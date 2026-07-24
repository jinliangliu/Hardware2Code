# pwm — PWM 输出外设

演示 `Internal_PWM` 外设驱动生成。

## 硬件

- **PA8**: PWM 输出（TIM1_CH1）
- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 行为

- PWM 任务自动配置 TIM1 输出 PWM 信号
- 按键控制 LED 翻转

## 测试特性

| 特性 | 说明 |
|------|------|
| `Internal_PWM` | PWM 外设 HAL 驱动自动生成 |
| 外设模型 | 通过 `models/Internal_PWM.yaml` 自动拉取 HAL 源文件 |

## 生成

```bash
python generator/generate.py -i examples/pwm/hardware.yaml -o output/pwm
```
