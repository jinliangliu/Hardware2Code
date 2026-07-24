# parallel_states — 并行区域

演示 `regions`（并行区域）机制：多个独立区域串行处理同一事件。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）

## 状态机

```
regions:
  led_control:   OFF ──[按键]──► ON ──[按键]──► OFF
  counter:       COUNTING ──[RTC_TICK, 自循环]──► COUNTING (count++)
```

## 行为

两个区域**独立维护各自的状态变量**，互不干扰：
1. 按 PC13 → `led_control` 区域切换 ON/OFF，LED 翻转
2. 每次 RTC_TICK → `counter` 区域 `count` 自增（自循环）

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | OFF 状态 |
| 按 PC13 | 亮 | OFF→ON，toggle_led |
| 再按 PC13 | 灭 | ON→OFF，toggle_led |
| 重复按键 | 每次翻转 | 两个区域独立运行，counter 区持续自增 |

## 测试特性

| 特性 | 说明 |
|------|------|
| `regions` | 多个独立区域并行处理事件 |
| 区域变量 | counter 区域有独立的 `count` 变量 |
| 自循环转换 | target 指向自身实现持续计数 |

## 生成

```bash
python generator/generate.py -i examples/parallel_states/hardware.yaml -o output/parallel_states
```
