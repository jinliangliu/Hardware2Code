# mpu6050 — I2C 传感器 MPU6050

演示 `I2C_Sensor_MPU6050` 外设驱动生成。

## 硬件

- **PB6**: I2C1 SCL（AF1）
- **PB7**: I2C1 SDA（AF1）
- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 行为

- I2C1 自动初始化，MPU6050 传感器驱动生成
- 传感器数据周期性读取（加速度 ±2g，陀螺仪 ±250°/s）
- 按键触发 LED 翻转

## 测试特性

| 特性 | 说明 |
|------|------|
| `I2C_Sensor_MPU6050` | I2C 传感器 HAL 驱动自动生成 |
| `bus` 字段 | 指定 I2C 总线（I2C1） |
| `extra` 配置 | 加速度量程、陀螺仪量程、采样率 |
| 外设模型 | 通过 `models/I2C_Sensor_MPU6050.yaml` 管理 HAL 依赖 |

## 生成

```bash
python generator/generate.py -i examples/mpu6050/hardware.yaml -o output/mpu6050
```
