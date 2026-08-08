# mpu6050_demo - I2C IMU（MPU6050）+ 姿态管理示例

演示 hw2c 的 **I2C 总线抽象** 与 **姿态管理组件**：

- **IMU 走 I2C1**：PB6(SCL)/PB7(SDA)，MPU6050 @ 0x68（默认总线；
  SPI 变体受支持——换成 `SPI_Sensor_MPU6500` 模型 + CS 引脚即可，见下）
- **i2c_api 总线层**：POSIX 风格接口（`i2c_open/read_reg/write_reg/
  mem_read/mem_write/scan`），一总线多设备按 7 位地址区分
- **IMU 驱动参数化**：`drv_mpu6050` 一个模板同时支持 I2C（MPU6050）与
  SPI（MPU6500）传输——模型 `interface` 切换传输宏，寄存器表/量程/缩放共用
- **imu 组件 + 姿态**：WHO_AM_I 校验、50 Hz 采样、互补滤波
  （roll/pitch 加速度计约束，yaw 陀螺仪积分），发布 att_roll/pitch/yaw
- **fall_detect 摔倒监测**：直接消费 imu 组件数据（同周期采样），
  自由落体→撞击→静止三阶段检测，`FALL_DETECTED` 事件触发状态机报警
- **CLI**：`mpu` 显示实时 IMU 数据 + 融合姿态；无传感器时优雅报错不挂死

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| I2C1 SCL/SDA | PB6/PB7 | I2C 总线（100 kHz） |
| IMU | MPU6050 @ 0x68 | 加速度计 ±2g + 陀螺仪 ±250dps + 温度 |
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
python test/run_tests.py        # 主机侧：test_i2c_api / test_mpu6050 / test_attitude 等
cmake --build build --target flash-daplink
```

## CLI 用法

```text
hw2c> i2c scan                # 总线扫描（无传感器时 0 设备）
I2C scan: 0 device(s) on i2c1

hw2c> mpu                     # 实时 IMU + 融合姿态（无传感器时提示接线）
MPU6050 read failed (check wiring, addr 0x68)
```

接上传感器后：

```text
hw2c> mpu
attitude  roll=   0.2 pitch=  -0.4 yaw=  12.3 deg
accel(g)  x=-0.01 y=+0.01 z=+1.00
gyro(dps) x=+0.10 y=-0.05 z=+0.20
temp      46.53 C

hw2c> fall                    # 摔倒检测状态
Fall detector: state=STABLE events=0 last_impact=0.0g failures=0
```

摔倒参数可运行时调参（`param set fall_impact_g 3.0` 等）：

```text
hw2c> param get fall_impact_g
fall_impact_g = 2.500000
```

## 设计要点

### 一总线多设备（软硬件分离）

```
I2C1 物理总线 (PB6/PB7)
  └─ MPU6050 @ 0x68 → imu 组件（i2c_read_reg / i2c_write_reg）

所有访问都经过 i2c_api：
  i2c_open("i2c1")  → 共享总线句柄（幂等）
  每次调用携带 7 位设备地址 → 驱动层天然支持多设备
```

### 驱动模板参数化（I2C ↔ SPI 一键切换）

同一个 `drv_mpu6050.c.j2` 按模型的 `interface` 字段选择传输宏：

```c
/* I2C:  i2c_read_reg(bus, dev_addr, reg, ...)  MPU6050 @ 0x68
 * SPI:  spi_read_reg(bus, cs_name, reg, ...)   MPU6500 @ CS
 * 寄存器表（WHO_AM_I/量程/数据寄存器）与物理量缩放完全共用 */
```

切换到 SPI 只需在 `hardware.yaml` 里把 IMU 外设换成
`type: SPI_Sensor_MPU6500, bus: SPI1, cs_pin: "PC4"`（并声明 SPI1 引脚），
组件与姿态层零改动。

### 姿态解算（互补滤波）

```
roll/pitch = α·(上一帧 + 陀螺仪积分) + (1-α)·加速度计静态参考
             α = 0.98（可配置），加速度幅值偏离 1g 时自动降低信任度
yaw         = 纯陀螺仪积分（无磁力计，随时间漂移）
```

组件每 20 ms 发布 `att_roll / att_pitch / att_yaw`（0.01°）与
`imu_temp`（0.1°C）到 component_bus。

### 摔倒监测（fall_detect）

```
imu 组件(50 Hz 采样) ──同周期直接取数──► fall_detect 组件
                                          │ 三阶段状态机
                                          │   STABLE → FREE_FALL(‖a‖<0.4g, ≥200ms)
                                          │         → IMPACT(‖a‖>2.5g)
                                          │         → STILL(0.8..1.2g, ≥2s)
                                          ▼
                              FALL_DETECTED → 状态机报警(LED fault + 日志)
```

阈值来自 `params.yaml`（fall_free_fall_g / fall_free_fall_ms /
fall_impact_g / fall_still_ms），CLI 可运行时调整。

## 已知限制

- 实际未接硬件：`i2c scan` / `mpu` 为不带板调试工具；接板后应先扫描确认
  0x68 在总线上，再看姿态输出
- 摔倒阈值需上板标定（身体/佩戴位置不同差异大）；算法为规则式，
  后续可叠加机器学习模型（特征仍来自 imu 组件）
- yaw 无绝对参考（无磁力计），长时间会漂移；roll/pitch 有加速度计约束
- Cortex-M0+ 无 FPU：姿态用软件浮点，50 Hz 更新完全够用
