# nested_ref — 嵌套引用 + 事件发布

演示嵌套状态 + ref 引用 + `when` 条件动作 + `publish` 事件发布。

## 硬件

- **PC0**: LED（低电平点亮）
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: 100ms 周期 RTC_TICK（由 `rtc_demo_task` 产生）

## 状态机

```
MAIN_IDLE ──[按键]──► DEEP (ref: nested_ref/subflow.yaml, namespace: nested)
                        ├── nested_SUB_IDLE ──[RTC_TICK, counter++]──► nested_SUB_ACTIVE
                        └── nested_SUB_ACTIVE ──[RTC_TICK, 条件判断]──► nested_SUB_IDLE
                      DEEP ──[HIGH_COUNT, toggle_led]──► MAIN_IDLE
```

## 计数器逻辑

`nested_local_counter` 在 **SUB_IDLE → SUB_ACTIVE** 的转换动作中递增（每 2 个 RTC_TICK 递增 1）。条件判断发生在 **SUB_ACTIVE → SUB_IDLE** 的转换中：

| counter 值 | 耗时（约） | 触发动作 |
|-----------|----------|---------|
| 0 → 1 | 100ms | 仅递增，不满足任何条件 |
| 1 → 2 | 300ms | 不满足条件 |
| 2 → 3 | 500ms | counter=3: `> 2` 满足 → **toggle_led（LED 亮）** |
| 3 → 4 | 700ms | counter=4: `> 2` 满足 → **toggle_led（LED 灭）** |
| 4 → 5 | 900ms | counter=5: `> 2` 满足（toggle_led 亮）+ `> 4` 满足 → **publish HIGH_COUNT** |

`publish`（**同步**）vs `publish_async`（异步）：
- `publish` ⇒ 直接调用 `statemachine_process()`，在当前事件处理中**立即**触发父状态转换
- `publish_async` ⇒ `xQueueSend` 放入队列末尾，若前面有积压的 RTC_TICK 会被插队

本 demo 使用 `publish` 确保 HIGH_COUNT 在 counter=5 时立即处理，不被后续 RTC_TICK 推迟。

## 板上观察

| 阶段 | LED 状态 | 说明 |
|------|---------|------|
| 上电 | 灭 | MAIN_IDLE，无动作 |
| 按 PC13 | 灭 →（等待）| 进入 DEEP，counter 从 0 开始计数 |
| ~500ms 后 | 亮 | counter=3，`> 2` 条件触发 toggle_led |
| ~700ms 后 | 灭 | counter=4，`> 2` 条件触发 toggle_led |
| ~900ms 后 | 亮 → 立即灭 | counter=5：toggle_led 亮，同时 publish HIGH_COUNT → 退出 DEEP，toggle_led 灭 |
| 再次按键 | 重复上述流程 | counter 重新从 0 开始 |

## 测试特性

| 特性 | 说明 |
|------|------|
| 嵌套状态 | 子状态具有自己的转换和动作 |
| `when` | 条件执行动作（counter > 2 时 toggle_led） |
| `publish` | 同步发布自定义事件，不经过事件队列 |
| `type: ref` | 引用外部子流程文件 |
| `namespace` | 变量前缀避免命名冲突 |

## 生成

```bash
python generator/generate.py -i examples/nested_ref/hardware.yaml -o output/nested_ref
```
