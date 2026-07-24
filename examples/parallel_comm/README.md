# parallel_comm — 跨区域通信

演示并行区域间的 `send_to` 跨区域通信机制。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 状态机

```
regions:
  button_region:  UP ──[按键, send_to led_region LED_ON]──► DOWN
                  DOWN ──[按键, send_to led_region LED_OFF]──► UP

  led_region:     OFF ──[LED_ON]──► ON (toggle_led)
                  ON ──[LED_OFF]──► OFF (toggle_led)
```

## 行为

按 PC13 → `button_region` 通过 `send_to` 向 `led_region` 发送 `LED_ON` 或 `LED_OFF` 事件 → `led_region` 切换状态并翻转 LED。

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | button_region=UP, led_region=OFF |
| 按 PC13 | 亮 | send_to LED_ON → led_region ON → toggle_led |
| 再按 PC13 | 灭 | send_to LED_OFF → led_region OFF → toggle_led |
| 重复按键 | 每次翻转 | UP↔DOWN 交替发送 LED_ON/LED_OFF |

## 测试特性

| 特性 | 说明 |
|------|------|
| `send_to` | 跨区域异步发送事件（3 段式语法：区域名 + 事件名） |
| 自定义事件 | `LED_ON` / `LED_OFF` 由 `send_to` 隐式创建 |

## 生成

```bash
python generator/generate.py -i examples/parallel_comm/hardware.yaml -o output/parallel_comm
```
