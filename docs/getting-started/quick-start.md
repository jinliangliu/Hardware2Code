# Quick Start

本指南带你用 **六层 YAML** 在 5 分钟内生成第一个 hw2c 工程。

六个配置层各司其职：

| 文件 | 职责 |
|------|------|
| `hardware.yaml` | 硬件物理事实 — MCU / 引脚 / 外设 / 时钟 / 休眠 |
| `task.yaml` | 软件架构 — FreeRTOS 任务 / 状态机行为 / 定时事件 |
| `components.yaml` | 组件注册 — shell / led / btn 等可插拔组件实例 |
| `bind.yaml` | 硬-软绑定 — 中断 → 组件 / 外设 → 任务路由 |
| `params.yaml` | 运行时参数 — 类型化可调参数（default/min/max） |
| `pubsub.yaml` | 发布/订阅 — 跨组件解耦事件主题 |

## Step 1: 创建 YAML 文件

在目录 `my_project/` 中创建以下文件。

**`hardware.yaml`** — MCU 与引脚定义：

```yaml
mcu:
  part: STM32G0B1RET6
  clock_source: HSI          # HSI 或 HSE
  clock_freq_hz: 16000000    # 振荡器频率
  core_clock_mhz: 16         # SYSCLK = clock_freq / 1e6

pins:
  - id: PC0
    function: GPIO_Output
    label: "LED"
    active_level: low
  - id: PC13
    function: GPIO_Input
    label: "BUTTON"
    pull: up
    exti:
      enable: true
      trigger: both

peripherals:
  - name: usart2
    type: UART_Serial
    instance: USART2
    interface: uart
    extra:
      baudrate: 115200
```

**`task.yaml`** — 任务与状态机：

```yaml
project:
  name: my_project
  version: "0.1.0"
  heap_size: 16384

event_task:
  name: events_process_task
  entry: vEventTask
  priority: 3
  stack_size: 512
  queue_depth: 16

app_tasks:
  - name: shell_task
    priority: 1
    stack_size: 1024

behavior:
  initial_state: IDLE
  states:
    - name: IDLE
      transitions:
        - event: BUTTON_SHORT_PRESS
          target: IDLE
          actions:
            - 'log "button pressed"'
```

**`components.yaml`** — 组件注册（周期、配置、休眠兼容）：

```yaml
components:
  - name: shell
    type: shell_cli
    driver: usart2
    period_ms: 50
    config:
      prompt: "my_project> "
  - name: btn
    type: btn
    driver: gpio
    period_ms: 10
    config:
      long_press_ms: 1000
      double_click_ms: 500
      debounce_ms: 50
```

**`bind.yaml`** — 中断/外设与组件、任务的绑定：

```yaml
version: 1
hardware: hardware.yaml
task: task.yaml

interrupt:
  - pin: PC13
    component: btn
    event: EXTI13
```

**`params.yaml`** 与 **`pubsub.yaml`** 可选（无参数/主题时可用空配置），参考
[components.yaml](../user-guide/components-yaml.md)、[params.yaml](../user-guide/params-yaml.md)、
[pubsub.yaml](../user-guide/pubsub-yaml.md)。

## Step 2: 生成工程

```bash
python -m generator.generate -i my_project/hardware.yaml -o output/my_project --force \
  --task my_project/task.yaml \
  --components my_project/components.yaml \
  --bind my_project/bind.yaml \
  --params my_project/params.yaml \
  --pubsub my_project/pubsub.yaml
```

生成内容：

- `src/main.c` — FreeRTOS 任务创建与组件框架初始化
- `src/gpio.c` — GPIO / EXTI 初始化
- `src/event_mgr.c/h` — 事件队列与分发器
- `src/statemachine.c/h` — 状态机行为
- `src/component_*.c/h` — 组件注册表 / 组件总线 / 参数注册表
- `config/FreeRTOSConfig.h` — FreeRTOS 内核配置
- `CMakeLists.txt`、`toolchain.cmake` — CMake 构建
- `test/` — Unity 单元测试（Mock HAL）
- `.vscode/` — 调试配置

## Step 3: 编译

```bash
cd output/my_project
cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
```

## Step 4: 运行单元测试（PC）

```bash
cd test
python run_tests.py
```

测试在 PC 上基于 Mock HAL 原生运行，无需硬件。

## Step 5: 烧录

```bash
# ST-Link
openocd -f interface/stlink.cfg -f target/stm32g0x.cfg -c "program build/my_project.elf verify reset exit"

# DAP-Link
openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg -c "program build/my_project.elf verify reset exit"
```

## 下一步

- 查看 `examples/base/README.md` 完整示例（六层 YAML + 组件框架）
- [hardware.yaml 参考](../user-guide/hardware-yaml.md) — 完整 Schema
- [task.yaml 参考](../user-guide/task-yaml.md) — 行为 DSL
- [components.yaml 参考](../user-guide/components-yaml.md) — 组件注册
- [bind.yaml 参考](../user-guide/bind-yaml.md) — 绑定规则
- [Examples](../user-guide/examples.md) — 示例工程
