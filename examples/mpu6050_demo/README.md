# mpu6050_demo - SPI IMU（MPU6500 兼容）+ 姿态管理示例

演示 hw2c 的 **SPI 总线抽象** 与 **姿态管理组件**：

- **IMU 走 SPI1**：PA5(SCK)/PA6(MISO)/PA7(MOSI)，CS=PC4（软件 GPIO 控制），
  对应 MPU6500/MPU9250 类芯片（寄存器映射与 MPU6050 兼容，WHO_AM_I=0x70）
- **spi_api 总线层**：POSIX 风格接口（`spi_open/transfer/transmit/receive/
  read_reg/write_reg`），CS 通过 gpio_api 软件控制，一总线多设备按 CS 区分，
  与 i2c_api 同一抽象范式
- **IMU 驱动参数化**：`drv_mpu6050` 一个模板同时支持 I2C（MPU6050）与
  SPI（MPU6500）传输——模型 `interface` 切换传输宏，寄存器表/量程/缩放共用
- **imu 组件 + 姿态**：WHO_AM_I 校验、50 Hz 采样、互补滤波
  （roll/pitch 加速度计约束，yaw 陀螺仪积分），发布 att_roll/pitch/yaw
- **CLI**：`mpu` 显示实时 IMU 数据 + 融合姿态；无传感器时优雅报错不挂死

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| SPI1 SCK/MISO/MOSI | PA5/PA6/PA7 | SPI 总线（主模式） |
| IMU CS | PC4 | 软件片选（低有效） |
| IMU | MPU6500 兼容 | 加速度计 ±2g + 陀螺仪 ±250dps + 温度 |
| LED | PC0 | 低电平点亮 |
| BUTTON | PC13 | EXTI 双沿 → 手势检测 |
| USART2 | PA2/PA3 | CLI Shell + 日志（115200） |

MCU: STM32G0B1RET6 @ 16 MHz (HSI)

## 生成固件（六层完整配置）

```bash
python -m generator.generate -i examples/mpu6050_demo/hardware.yaml -o output/mpu6050_demo --force \
  --task examples/mpu6050_demo/task.yaml \
  --components examples/mpu6050_demo/components.yaml \
  --bind examples/mpu6050_demo/bind.yaml \
  --params examples/mpu6050_demo/params.yaml \
  --pubsub examples/mpu6050_demo/pubsub.yaml
```

## 编译 / 测试 / 烧录

```bash
cd output/mpu6050_demo
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
python test/run_tests.py        # 主机侧：test_spi_api / test_mpu6050 / test_attitude 等
cmake --build build --target flash-daplink
```

## CLI 用法

```text
hw2c> mpu                # 实时 IMU + 融合姿态（无传感器时提示接线）
MPU6500 read failed (check wiring, CS mpu_cs)
```

接上传感器后：

```text
hw2c> mpu
attitude  roll=   0.2 pitch=  -0.4 yaw=  12.3 deg
accel(g)  x=-0.01 y=+0.01 z=+1.00
gyro(dps) x=+0.10 y=-0.05 z=+0.20
temp      46.53 C
```

## 设计要点

### 一总线多设备（软硬件分离）

```
SPI1 物理总线 (PA5/PA6/PA7)
  └─ MPU6500 @ CS=PC4 → imu 组件（spi_read_reg / spi_write_reg）

所有访问都经过 spi_api：
  spi_open("spi1")  → 共享总线句柄（幂等）
  每次调用携带 CS 引脚 → 驱动层天然支持多设备（多 CS）
```

### 驱动模板参数化（I2C ↔ SPI 一键切换）

同一个 `drv_mpu6050.c.j2` 按模型的 `interface` 字段选择传输宏：

```c
/* I2C:  i2c_read_reg(bus, dev_addr, reg, ...)  MPU6050 @ 0x68
 * SPI:  spi_read_reg(bus, cs_name, reg, ...)   MPU6500 @ CS=PC4
 * 寄存器表（WHO_AM_I/量程/数据寄存器）与物理量缩放完全共用 */
```

组件与姿态层（`mpu6050_component` / `attitude`）不感知总线类型，零改动。

### 姿态解算（互补滤波）

```
roll/pitch = α·(上一帧 + 陀螺仪积分) + (1-α)·加速度计静态参考
             α = 0.98（可配置），加速度幅值偏离 1g 时自动降低信任度
yaw         = 纯陀螺仪积分（无磁力计，随时间漂移）
```

组件每 20 ms 发布 `att_roll / att_pitch / att_yaw`（0.01°）与
`imu_temp`（0.1°C）到 component_bus。

## 已知限制

- 实际未接硬件：`mpu` 命令为不带板调试工具；接板后应先确认 WHO_AM_I
  （0x70）能读到，再看姿态输出
- yaw 无绝对参考（无磁力计），长时间会漂移；roll/pitch 有加速度计约束
- Cortex-M0+ 无 FPU：姿态用软件浮点，50 Hz 更新完全够用
