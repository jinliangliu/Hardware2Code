按下 PC13 按键，系统进入 DEEP 状态（实际上是嵌套的 nested_SUB_IDLE）。

每次 RTC 滴答，nested_local_counter 递增，子状态在 nested_SUB_IDLE 和 nested_SUB_ACTIVE 之间切换。

当 nested_local_counter > 2 时，执行 toggle_led；当 > 4 时，发布 HIGH_COUNT 事件。

父状态 DEEP 监听到 HIGH_COUNT，跳转回 MAIN_IDLE 并翻转 LED。

整个流程演示了嵌套状态、变量前缀、事件发布和引用机制。