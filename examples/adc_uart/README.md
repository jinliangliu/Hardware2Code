# adc_uart — ADC 采样 + UART 串口

演示 `Internal_ADC` 和 `UART_Serial` 双外设组合，无状态机。

## 硬件

- **PA0**: ADC 输入（ADC_IN1）
- **PA2**: USART2 TX（AF1）
- **PA3**: USART2 RX（AF1）
- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 行为

- ADC 外设自动初始化并周期性采样
- USART2 串口配置为 115200-8-N-1
- 按键控制 LED 翻转

## 测试特性

| 特性 | 说明 |
|------|------|
| `Internal_ADC` | ADC HAL 驱动 + DMA 配置 |
| `UART_Serial` | UART HAL 驱动自动生成 |
| 多外设共存 | 验证两个外设同时初始化不冲突 |

## 生成

```bash
python generator/generate.py -i examples/adc_uart/hardware.yaml -o output/adc_uart
```
