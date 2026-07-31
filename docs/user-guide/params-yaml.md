# params.yaml Reference

`params.yaml` 定义**运行时参数**：类型化、有边界的值，可在运行期通过
CLI `param get/set` 动态读取/修改，无需重新编译。

每个参数归属一个组件（`component`），由 `param_registry` 统一登记。

## Schema Reference

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `params` | list | Yes | - | 参数定义列表 |
| `params[].name` | string | Yes | - | 参数名（唯一，snake_case） |
| `params[].component` | string | No | `"system"` | 归属组件名 |
| `params[].type` | string | No | `"uint32"` | 类型：`int32` / `uint32` / `float` / `bool` |
| `params[].default` | any | No | `0` | 默认值 |
| `params[].min` | number | No | - | 最小值（数值类型） |
| `params[].max` | number | No | - | 最大值（数值类型） |
| `params[].readonly` | bool | No | `false` | 只读参数（仅可 get） |
| `params[].description` | string | No | `""` | 参数说明 |

## 示例

```yaml
params:
  - name: led_brightness
    component: shell
    type: uint32
    default: 200
    min: 0
    max: 255
    description: "LED PWM duty cycle (0..255)"

  - name: log_level
    component: system
    type: uint32
    default: 3
    min: 0
    max: 4
    description: "Log level (0=OFF, 1=ERROR, 2=WARN, 3=INFO, 4=DEBUG)"

  - name: telemetry_enabled
    component: system
    type: bool
    default: true
    description: "Enable periodic telemetry snapshot logging"
```

## CLI 用法

生成固件启用 `param` 命令后：

```
hw2c> param get led_brightness
led_brightness = 200
hw2c> param set led_brightness 100
led_brightness set to 100
```

## 命名约定

- 参数名全局唯一；按钮等组件实例参数建议带实例前缀
  （如 `btn_BUTTON_long_press_ms`）。
- 类型仅支持 `int32` / `uint32` / `float` / `bool`。
- `min`/`max` 仅对数值类型生效；`bool` 默认值为 `true`/`false`。

## 生成产物

- `src/param_registry.c/h` — 参数登记、读写、边界校验
- CLI `param get/set` 命令自动注册

参考：`examples/base/params.yaml`。
