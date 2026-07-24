# substate_demo — 嵌套复合状态与 return

演示复合状态（含子状态）和 `return` 动作。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: 唤醒定时器 100ms 周期

## 状态机

```
IDLE ──[按键]──► PROCESS (复合状态)
                    ├── STEP1 ──[RTC_TICK]──► STEP2
                    └── STEP2 ──[RTC_TICK, return]──► 触发 EVENT_RETURN
                 PROCESS ──[RETURN]──► IDLE
```

## 行为

1. 按 PC13 → 进入 PROCESS 的 STEP1 子状态，LED 翻转一次（STEP1 `on_entry`）
2. 2000ms 后 defer 触发，LED 翻转一次（`defer 2000 => toggle_led`）
3. 每次 RTC_TICK：STEP1 → STEP2 → `return` → 父状态 PROCESS 收到 RETURN → 回到 IDLE（LED 翻转）

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | IDLE 状态 |
| 按 PC13 | 亮 | 进入 STEP1，`on_entry: toggle_led` |
| ~2s 后 | 灭 | STEP1 的 `defer 2000 => toggle_led` 触发 |
| 下一个 RTC_TICK | 亮 | STEP1→STEP2→return→IDLE，`toggle_led` |
| 再次按键 | 重复上述流程 | |

## 测试特性

| 特性 | 说明 |
|------|------|
| 嵌套状态 | PROCESS 包含 STEP1/STEP2 子状态 |
| `return` | 子状态返回父状态，触发 EVENT_RETURN |
| `defer` | 延迟动作在子状态 on_entry 中 |
| `on_entry` | 进入状态的进入动作 |

## 生成

```bash
python generator/generate.py -i examples/substate_demo/hardware.yaml -o output/substate_demo
```
