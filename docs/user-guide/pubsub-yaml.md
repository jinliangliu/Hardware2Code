# pubsub.yaml Reference

`pubsub.yaml` 定义**发布/订阅主题**，实现跨组件解耦通信。主题名在生成代码中
变为 `TOPIC_<name>` 枚举值，运行时由 `component_bus` 分发。

组件可向主题 `publish()` 数据、`subscribe()` 接收数据，双方无需直接依赖。

## Schema Reference

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `topics` | list | Yes | - | 主题定义列表 |
| `topics[].name` | string | Yes | - | 主题名（唯一，snake_case） |
| `topics[].description` | string | No | `""` | 主题说明（数据语义、单位等） |

## 示例

```yaml
topics:
  - name: led_state
    description: "LED on/off state change (0=off, 1=on)"
  - name: button_press
    description: "Button press event (button_id as value)"
  - name: temperature
    description: "Temperature reading (scaled to int32, unit=0.1C)"
  - name: alarm
    description: "Alarm notification (alarm_id as value)"
```

## 生成产物

- `TOPIC_<name>` 枚举：`src/component_bus.h`
- 运行时发布/订阅接口：`component_bus_publish()` / `component_bus_subscribe()`
- 主题路由由 `src/component_bus.c` 实现（订阅表 + 分发）

## 与 bind.yaml / task.yaml 的关系

- `bind.yaml` 负责硬-软绑定（中断 → 组件/任务路由）；
- `pubsub.yaml` 负责**组件间**软-软解耦（主题总线）；
- 状态机 `behavior` 动作支持 `publish <topic>` 向总线发布事件。

参考：`examples/base/pubsub.yaml`。
