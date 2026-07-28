# Quick Start

This guide walks you through generating your first hw2c project in 5 minutes.

## Step 1: Create a Hardware Description

Create a `my_project.yaml` file:

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
    notify_task: "led_task"

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

## Step 2: Generate the Project

```bash
python generator/generate.py -i my_project.yaml -o output/my_project
```

This generates:
- `src/main.c` — FreeRTOS task creation and main loop
- `src/gpio.c` — GPIO and EXTI initialization
- `src/event_mgr.c/h` — Event queue and dispatcher
- `src/statemachine.c/h` — Business flow state machine
- `src/stm32g0xx_it.c` — Interrupt handlers
- `config/FreeRTOSConfig.h` — FreeRTOS kernel configuration
- `Makefile` — GCC build system
- `test/` — Unity-based unit tests with Mock HAL
- `.vscode/` — VS Code debug configuration

## Step 3: Build

```bash
cd output/my_project
make
```

## Step 4: Run Unit Tests (PC)

```bash
cd test
python run_tests.py
```

All tests run natively on your PC against Mock HAL — no hardware required.

## Step 5: Flash to Hardware

```bash
# ST-Link
make flash

# DAP-Link
make flash-daplink
```

## Next Steps

- Explore more examples in `examples/` directory
- Read the [Hardware YAML Reference](../user-guide/hardware-yaml.md) for complete schema
- Check [Examples](../user-guide/examples.md) for 21 pre-built example projects
- Learn [Template Development](../developer-guide/template-development.md) to create custom drivers
