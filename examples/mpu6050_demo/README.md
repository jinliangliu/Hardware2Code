# mpu6050_demo - I2C 多设备总线 + MPU6050 姿态管理示例

演示 hw2c 的 **I2C 总线抽象** 与 **姿态管理组件**：

- **一条物理 I2C 总线挂多个设备**：I2C1（PB6/PB7）上同时挂
  **MPU6050（0x68）** 与 **EEPROM（0x50）**，驱动层通过 7 位设备地址
  区分，互不干扰（`i2c scan` 可一次列出两个设备）
- **i2c_api 总线层**：POSIX 风格接口（`i2c_open/read_reg/write_reg/
  mem_read/mem_write/scan`），与 uart_api 同一抽象范式，组件不感知
  物理外设细节
- **imu 组件（mpu6050 类型）**：`imu_init()` 校验 WHO_AM_I 并配置量程，
  `imu_step()` 以 50 Hz 采样加速度/陀螺仪/温度并更新姿态
- **姿态管理**：互补滤波（加速度计静态参考 + 陀螺仪积分融合），
  roll/pitch/yaw 输出，yaw 无磁力计、存在漂移（已注明）
- **CLI**：`i2c scan` / `i2c rd` / `i2c wr`（总线调试）、`mpu`
  （实时 IMU 数据 + 融合姿态）

## 硬件

| 组件 | 引脚 | 功能 |
|------|------|------|
| I2C1 SCL/SDA | PB6/PB7 | 共享 I2C 总线（100 kHz） |
| MPU6050 | 0x68 | 加速度计 ±2g + 陀螺仪 ±250dps + 温度 |
| EEPROM | 0x50 | AT24C32 风格存储（同总线第二个设备） |
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
python test/run_tests.py        # 主机侧：test_i2c_api / test_mpu6050 / test_attitude / test_eeprom 等
cmake --build build --target flash-daplink
```

## CLI 用法

```text
hw2c> i2c scan
I2C scan: 2 device(s) on i2c1
  0x50
  0x68

hw2c> i2c rd 68 75        # 读 MPU6050 WHO_AM_I
0x68[0x75]: 68

hw2c> mpu                # 实时 IMU + 融合姿态
attitude  roll=   0.2 pitch=  -0.4 yaw=  12.3 deg
accel(g)  x=-0.01 y=+0.01 z=+1.00
gyro(dps) x=+0.10 y=-0.05 z=+0.20
temp      46.53 C
```

## 设计要点

### 一总线多设备（软硬件分离）

```
I2C1 物理总线 (PB6/PB7)
  ├─ MPU6050 @ 0x68  → mpu6050 组件（i2c_read_reg / i2c_write_reg）
  └─ EEPROM  @ 0x50  → eeprom 驱动（i2c_mem_read / i2c_mem_write, 16-bit 地址）

所有访问都经过 i2c_api：
  i2c_open("i2c1")  → 共享总线句柄（幂等）
  每次调用携带 7 位设备地址 → 驱动层天然支持多设备
```

### 姿态解算（互补滤波）

```
roll/pitch = α·(上一帧 + 陀螺仪积分) + (1-α)·加速度计静态参考
             α = 0.98（可配置），加速度幅值偏离 1g 时自动降低信任度
yaw         = 纯陀螺仪积分（无磁力计，随时间漂移）
```

组件每 20 ms 发布 `att_roll / att_pitch / att_yaw`（0.01°）与
`imu_temp`（0.1°C）到 component_bus，便于其他组件订阅消费。

## 已知限制

- 实际未接硬件：`i2c scan` 为不带板调试工具；接板后应先扫描确认
  两个地址都在，再查 `mpu` 输出
- yaw 无绝对参考（无磁力计），长时间会漂移；roll/pitch 有加速度计
  约束，无漂移
- Cortex-M0+ 无 FPU：姿态用软件浮点，50 Hz 更新完全够用
