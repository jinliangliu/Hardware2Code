# timeline_demo — 时间线动作与状态超时

演示 `defer`、`timeline`、`after` 三种定时器 DSL 特性。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: 100ms 周期 RTC_TICK（由 `rtc_demo_task` 产生）

## 行为

| 时间点 | 动作 | 触发方式 |
|---|---|---|
| 0s（按键） | LED 翻转 | `on_entry: toggle_led` |
| 1s | LED 翻转 | `defer_0_cb`（timeline 第 1 步） |
| 2s | LED 翻转 | `defer_1_cb`（timeline 第 2 步） |
| 3s | LED 翻转 | `defer_2_cb`（timeline 第 3 步） |
| 5s | 返回 IDLE | `after: 5000` 超时 |

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | IDLE 状态 |
| 按 PC13 | 亮 | `on_entry: toggle_led` 立即翻转 |
| 约 1s 后 | 灭 | `timeline: 1000=>toggle_led` |
| 约 2s 后 | 亮 | `timeline: 2000=>toggle_led` |
| 约 3s 后 | 灭 | `timeline: 3000=>toggle_led` |
| 约 5s 后 | — | `after: 5000` 超时，返回 IDLE |
| 再次按键 | 重复 | |

## 测试特性

| 特性 | 说明 |
|------|------|
| `timeline` | 按时间序列批量延迟动作 |
| `defer` | `timeline` 展开为 `defer_N` 定时器 |
| `after` | 状态超时自动转换 |
| `on_entry` | 进入状态时立即执行动作 |

## 生成

```bash
python generator/generate.py -i examples/timeline_demo/hardware.yaml -o output/timeline_demo
```
