# Quick Start

This guide walks you through generating your first hw2c project in 5 minutes, using the
three-layer YAML format (hardware / task / bind).

## Step 1: Create the YAML Files

Create three files in a new directory `my_project/`:

**`hardware.yaml`** — MCU and pin definitions:

```yaml
mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64

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
      trigger: falling
```

**`task.yaml`** — Task and state machine definitions:

```yaml
project:
  name: my_project
  version: "0.1.0"
  heap_size: 16384

event_task:
  name: event_task
  entry: vEventTask
  priority: 3
  stack_size: 1024
  queue_depth: 32

app_tasks:
  - name: led_task
    priority: 2
    stack_size: 128

behavior:
  initial_state: "OFF"
  states:
    - name: "OFF"
      transitions:
        - event: "BUTTON_PRESS"
          target: "ON"
          actions:
            - "toggle_led"
    - name: "ON"
      transitions:
        - event: "BUTTON_PRESS"
          target: "OFF"
          actions:
            - "toggle_led"
```

**`bind.yaml`** — Wiring: connects pins to tasks and events:

```yaml
version: 1
hardware: hardware.yaml
task: task.yaml
interrupt:
  - pin: PC13
    task: led_task
    event: EXTI13
```

## Step 2: Generate the Project

```bash
hw2c gen -i my_project/hardware.yaml -o output/my_project --task my_project/task.yaml --bind my_project/bind.yaml
```

This generates:
- `src/main.c` — FreeRTOS task creation and main loop
- `src/gpio.c` — GPIO and EXTI initialization
- `src/event_mgr.c/h` — Event queue and dispatcher
- `src/statemachine.c/h` — Business flow state machine
- `src/stm32g0xx_it.c` — Interrupt handlers
- `config/FreeRTOSConfig.h` — FreeRTOS kernel configuration
- `CMakeLists.txt` — CMake build system
- `toolchain.cmake` — ARM GCC cross-compilation toolchain
- `test/` — Unity-based unit tests with Mock HAL
- `.vscode/` — VS Code debug configuration

## Step 3: Build

```bash
cd output/my_project
cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
```

## Step 4: Run Unit Tests (PC)

```bash
cd test
python run_tests.py
```

All tests run natively on your PC against Mock HAL — no hardware required.

## Step 5: Flash to Hardware

```bash
# ST-Link (via OpenOCD)
openocd -f interface/stlink.cfg -f target/stm32g0x.cfg -c "program build/my_project.elf verify reset exit"

# DAP-Link
openocd -f interface/cmsis-dap.cfg -f target/stm32g0x.cfg -c "program build/my_project.elf verify reset exit"
```

## Next Steps

- Explore more examples in `examples/` directory (20 pre-built projects)
- Read the [Hardware YAML Reference](../user-guide/hardware-yaml.md) for complete schema
- Read the [Task YAML Reference](../user-guide/task-yaml.md) for behavior DSL
- Read the [Bind YAML Reference](../user-guide/bind-yaml.md) for wiring rules
- Check [Examples](../user-guide/examples.md) for all example projects
- Learn [Template Development](../developer-guide/template-development.md) to create custom drivers
