# blinky_g0 — 最小示例

最简单的入门示例，仅包含按键 + LED，无状态机、无外设。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 行为

按下 PC13 按键 → LED 翻转。

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | 初始化输出高电平 |
| 按 PC13 | 亮 | EXTI 触发 → led_task 收到通知 → toggle |
| 再按 PC13 | 灭 | 再次 toggle |
| 重复按键 | 每次翻转 | |

## 测试特性

| 特性 | 说明 |
|------|------|
| GPIO 输出 | LED 引脚配置 |
| GPIO 输入 + EXTI | 按键中断 + FreeRTOS 任务通知 |

## 生成

```bash
python generator/generate.py -i examples/blinky_g0/hardware.yaml -o output/blinky_g0
```
