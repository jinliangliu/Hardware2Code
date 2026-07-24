# rtc_advanced — 守卫条件与用户定时器

演示 `guard`（守卫条件）路由、`start_timer`/`stop_timer` 用户定时器、`defer` 延迟动作。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: 唤醒定时器 + LSE 时钟

## 状态机

```
IDLE ──[按键, press_count<3]──► ACTIVE ──[exit_timer到期|RTC_TICK]──► IDLE
  │                                │
  ├──[按键, press_count>=3]──► RESET ──[RTC_TICK]──► IDLE
  │
  └──[5s超时(after)]──► TIMEOUT ──[RTC_TICK]──► IDLE
```

## 行为

1. **按 1~3 次** → 进入 ACTIVE：启动 3 秒 `exit_timer`，3 秒后自动回 IDLE
2. **按 4 次及以上** → 进入 RESET：`press_count` 清零，下一个 RTC_TICK 回 IDLE
3. **5 秒无操作** → 进入 TIMEOUT：下一个 RTC_TICK 回 IDLE
4. 每次进出 IDLE 都会翻转 LED（`on_entry`/`on_exit`）

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 亮 | IDLE `on_entry: toggle_led` |
| 按第 1 次 | 灭 | IDLE `on_exit: toggle_led` → ACTIVE |
| ~3s 后 | 亮 | `exit_timer` 到期 → IDLE `on_entry: toggle_led` |
| 快速按 4 次 | 灭→亮 | 进入 RESET（press_count≥4），counter 清零，下一 tick 回 IDLE |
| 等 5s 不按 | 灭→亮 | `after: 5000` 超时 → TIMEOUT → IDLE |
| IDLE 下按键 | 每次翻转 | `on_exit` + 目标态 `on_entry` 各 toggle 一次 |

> **注意**：每次按键后需等当前转换完成再按，否则 `press_count` 累计可能跳过 ACTIVE 直接进入 RESET。

## 测试特性

| 特性 | 说明 |
|------|------|
| `guard` | 同一事件根据条件路由到不同目标 |
| `start_timer` / `stop_timer` | 手动管理命名定时器 |
| `defer` | 转换过程中延迟翻转 LED |
| `set <var> inc` / `set <var> 0` | 变量操作 |
| `after` | 状态超时自动退出 |
| `on_entry` / `on_exit` | 进出动作 + 定时器自动清理 |

## 生成

```bash
python generator/generate.py -i examples/rtc_advanced/hardware.yaml -o output/rtc_advanced
```
