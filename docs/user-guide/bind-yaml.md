# bind.yaml Reference

## Overview

`bind.yaml` is the **wiring layer** that connects hardware capabilities
([`hardware.yaml`](hardware-yaml.md)) to software architecture
([`task.yaml`](task-yaml.md)).

It maps interrupts to tasks, assigns peripherals to task owners, and defines
task-to-task communication routes. This is the only file that references
identifiers from both hardware and software domains.

---

## Schema Reference

### Top-Level Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `version` | int | No | `1` | Schema version |
| `hardware` | string | No | `hardware.yaml` | Path to hardware description file |
| `task` | string | No | `task.yaml` | Path to task definition file |
| `interrupt` | list | No | `[]` | Pin interrupt → task bindings |
| `interrupt[].pin` | string | Yes | - | Pin ID from `hardware.yaml` (e.g. `PC13`) |
| `interrupt[].task` | string | Yes | - | Task name from `task.yaml` (e.g. `led_task`) |
| `interrupt[].event` | string | No | `EVENT_<pin>_IRQ` | Event name published to task's state machine |
| `peripheral_assign` | list | No | `[]` | Peripheral → task ownership |
| `peripheral_assign[].peripheral` | string | Yes | - | Peripheral name from `hardware.yaml` (e.g. `max3232`) |
| `peripheral_assign[].task` | string | Yes | - | Owning task name from `task.yaml` |
| `peripheral_assign[].role` | string | No | `""` | Semantic role (e.g. `cli_uart`, `storage`, `tick_timer`) |
| `routing` | list | No | `[]` | Task-to-task communication routes |
| `routing[].from` | string | Yes | - | Source task name |
| `routing[].to` | string | Yes | - | Destination task name |
| `routing[].signal` | string | Yes | - | Signal / event name |
| `routing[].condition` | string | No | `""` | Optional guard condition |

---

## 1. Interrupt Binding

Maps GPIO EXTI interrupts to task wake-up notifications.
Only pins with `exti.enable: true` in hardware.yaml should appear here.

```yaml
interrupt:
  - pin: "PC13"                 # Pin ID from hardware.yaml
    task: "led_task"            # Task name from task.yaml
    event: "BUTTON_PRESS"       # Event to publish into task's state machine
  - pin: "PA0"
    task: "sensor_task"
    event: "ADC_DONE"
```

Generated C code:
```c
// In HAL_GPIO_EXTI_Callback():
if (GPIO_Pin == GPIO_PIN_13) {
    publish_event(EVENT_BUTTON_PRESS);
    xTaskNotifyFromISR(led_task_handle, 0, eNoAction, NULL);
}
```

### Event naming convention

If `event` is omitted, it defaults to `EVENT_<pin_id>_IRQ` (e.g. `EVENT_PC13_IRQ`).

The event name must match an event used in transitions within `task.yaml`'s
`behavior`. The generator emits a warning if an interrupt event is not
consumed by any state machine transition.

---

## 2. Peripheral Assignment

Assigns each peripheral to a specific FreeRTOS task that owns its lifecycle.

```yaml
peripheral_assign:
  - peripheral: "max3232"       # Peripheral name from hardware.yaml
    task: "shell_task"          # Owning task from task.yaml
    role: "cli_uart"            # Semantic role hint

  - peripheral: "spi_flash"
    task: "fota_task"
    role: "storage"

  - peripheral: "rtc"
    task: "sensor_task"
    role: "tick_timer"
```

### Role conventions

| Role | Typical Use |
|------|-------------|
| `cli_uart` | UART used for debug shell |
| `storage` | Flash / EEPROM storage backend |
| `tick_timer` | RTC or Timer providing periodic ticks |
| `modbus_uart` | UART used for Modbus RTU |
| `lte_at` | UART used for 4G AT commands |
| `sensor_i2c` | I2C bus for sensors |

### Ownership rules

- Each peripheral **must** be assigned to exactly one task
- A task can own multiple peripherals (e.g. `sensor_task` owns both RTC and an I2C sensor)
- Peripherals without an assignment will not generate driver code

---

## 3. Task-to-Task Routing

Defines communication channels between tasks using FreeRTOS primitives
(queues, semaphores, task notifications).

```yaml
routing:
  - from: "sensor_task"         # Source task
    to: "mqtt_task"             # Destination task
    signal: "data_ready"        # Signal name
    condition: "readings.temp > 50"   # Optional guard

  - from: "sensor_task"
    to: "led_task"
    signal: "alert"

  - from: "sensor_task"
    signal: "heartbeat"         # Broadcast (no target specified)
```

### Signal semantics

| Pattern | Generated Primitive |
|---------|---------------------|
| `to` specified, one consumer | `xTaskNotify` (fast, binary semaphore) |
| `to` specified, `condition` present | `xTaskNotify` + if-guard in source |
| No `to` (broadcast) | `xQueueSend` (queue with fanout) |

### Condition expressions

Conditions use the variable access syntax from task.yaml:
- `readings.temp > 50` — struct member
- `counter >= 3` — scalar variable
- `sensor_history[0].temperature > 100` — array of struct

---

## 4. Example: Complete bind.yaml

```yaml
version: 1

interrupt:
  - { pin: "PC13", task: "led_task",   event: "BUTTON_PRESS" }
  - { pin: "PA0",  task: "sensor_task", event: "ADC_DONE" }

peripheral_assign:
  - { peripheral: "max3232",  task: "shell_task",  role: "cli_uart" }
  - { peripheral: "spi_flash", task: "fota_task",  role: "storage" }
  - { peripheral: "rtc",      task: "sensor_task", role: "tick_timer" }

routing:
  - { from: "sensor_task", to: "mqtt_task", signal: "data_ready" }
  - { from: "sensor_task", to: "led_task", signal: "alert", condition: "readings.temp > 50" }
  - { from: "sensor_task", signal: "heartbeat" }
```

---

## 5. Validation Rules

### Critical Errors
- `pin` value in `interrupt` does not exist in hardware.yaml
- `task` value in any section does not exist in task.yaml
- `peripheral` value in `peripheral_assign` does not exist in hardware.yaml
- Circular routing (`from` == `to`)

### Warnings
- Interrupt event name not consumed by any state machine transition
- Peripheral assigned to non-existent task
- Routing signal name ambiguity (same signal from multiple sources to same target)
