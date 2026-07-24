# ref_demo — 状态引用（Subflow）

演示 `type: ref` 状态引用机制：将外部 YAML 的状态机作为子流程嵌入。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: 唤醒定时器

## 状态机

```
IDLE ──[按键]──► BLINK (ref: common_subflow.yaml, namespace: blinker)
                    ├── blinker_S1 ──[RTC_TICK]──► blinker_S2 (toggle_led)
                    └── blinker_S2 ──[RTC_TICK]──► blinker_S1 (toggle_led)
```

## 行为

1. 按 PC13 → 进入 BLINK 状态，加载 `common_subflow.yaml` 的状态机
2. 每次 RTC_TICK：在 S1/S2 之间切换，翻转 LED

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | IDLE |
| 按 PC13 | 开始闪烁 | 进入 BLINK，每 100ms 在 S1/S2 间切换 |
| 持续闪烁 | 来回翻转 | `blinker_S1 → blinker_S2` 和反向转换都有 `toggle_led` |

> **注意**：由于 RTC_TICK 周期为 100ms，LED 以 200ms 周期闪烁（每个完整 S1→S2→S1 需要 2 个 tick），肉眼可见快速闪烁。

## 测试特性

| 特性 | 说明 |
|------|------|
| `type: ref` | 引用外部 YAML 作为子状态机 |
| `namespace` | 变量/状态名自动添加前缀避免冲突 |
| 子流程复用 | `common_subflow.yaml` 可被多个 demo 引用 |

## 生成

```bash
python generator/generate.py -i examples/ref_demo/hardware.yaml -o output/ref_demo
```
