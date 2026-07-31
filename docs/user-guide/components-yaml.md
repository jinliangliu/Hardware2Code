# components.yaml Reference

`components.yaml` 定义**可插拔应用组件**：每个组件封装一个或多个底层驱动
（通过 POSIX 接口），由框架按 `period_ms` 周期统一调度，与 MCU 型号解耦。

硬件描述见 [`hardware.yaml`](hardware-yaml.md)，组件间通信见
[`pubsub.yaml`](pubsub-yaml.md)，组件运行时参数见 [`params.yaml`](params-yaml.md)。

## Schema Reference

### Top-Level Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `components` | list | Yes | - | 组件实例列表 |
| `components[].name` | string | Yes | - | 组件实例名（唯一，snake_case） |
| `components[].type` | string | Yes | - | 组件类型：`shell_cli` / `led` / `btn` / 自定义 |
| `components[].driver` | string | Yes | - | 绑定的驱动实例名（来自 hardware.yaml） |
| `components[].period_ms` | int | No | `100` | step() 调度周期（ms），`-1` = 纯事件驱动 |
| `components[].config` | object | No | `{}` | 组件专属配置 |
| `components[].task` | string | No | `-` | 运行组件的 FreeRTOS 任务（默认组件调度任务） |
| `components[].priority` | int | No | `2` | 任务优先级（若独立运行） |
| `components[].stack_size` | int | No | `512` | 栈大小（字） |
| `components[].sleep_compat` | string | No | `""` | 休眠兼容模式：`RUN` / `SLEEP` / `STOP0` / `STOP1` / `STOP2` / `STANDBY` |

## 内置组件类型

| 类型 | 说明 | 典型配置 |
|------|------|---------|
| `shell_cli` | UART 交互终端 + 日志输出 | `prompt`、`history_size` |
| `led` | 多实例 LED 模式驱动器（自动发现 `LED*` 引脚） | `default_pattern`: `off`/`fast_blink`/`slow_blink`/`fault` |
| `btn` | 多实例按键手势检测（自动发现 `BUTTON*` + EXTI 引脚） | `long_press_ms`、`double_click_ms`、`debounce_ms` |

## 示例

```yaml
components:
  - name: shell
    type: shell_cli
    driver: usart2
    period_ms: 50
    sleep_compat: STOP1
    config:
      prompt: "hw2c> "
      history_size: 8
    priority: 3
    stack_size: 1024

  - name: led
    type: led
    driver: gpio
    period_ms: 50
    config:
      default_pattern: off

  - name: btn
    type: btn
    driver: gpio
    period_ms: 10
    config:
      long_press_ms: 3000
      double_click_ms: 500
      debounce_ms: 50
```

## 组件生命周期

每个组件实现三个标准接口，由 `component_registry` 统一管理：

```c
int  {name}_init(component_t *c, void *cfg);        // 初始化
void {name}_step(component_t *c);                   // 周期执行（period_ms）
void {name}_terminate(component_t *c);              // 清理
```

注册后固件自动：

1. `component_init_all()` 初始化全部组件；
2. 组件调度任务按各组件 `period_ms` 周期调用 `step()`；
3. 通过 `component_bus`（发布/订阅）与 `param_registry`（运行时参数）解耦通信；
4. `sleep_compat` 标记组件在低功耗模式下的行为兼容性。

新增组件只需编写模板并注册到 `components.yaml`，无需修改调度器代码。

## 生成产物

- `src/component_registry.c/h` — 组件注册表与生命周期调度
- `src/component_bus.c/h` — 组件间发布/订阅总线
- `src/param_registry.c/h` — 运行时参数表
- `src/btn_component.c/h`、`src/led_component.c/h` — 内置组件实现

参考：`examples/base/components.yaml`。
