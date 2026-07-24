# Hardware2Code DSL Reference

## Overview

Hardware2Code uses a YAML-based DSL (Domain-Specific Language) to describe:
1. **Hardware Configuration**: MCU, pins, peripherals, tasks, sleep mode
2. **Business Flow**: State machines, transitions, actions, variables

---

## 1. Hardware Configuration

### 1.1 MCU Configuration

```yaml
mcu:
  part: STM32G0B1RET6        # Required: MCU part number
  core_clock_mhz: 64         # Optional: Core clock frequency (default: 64)
  hse_freq: 8000000          # Optional: HSE crystal frequency (default: 8000000)
```

**Valid MCU parts**: STM32G0B1RET6 (currently only STM32G0 series supported)

### 1.2 Pin Configuration

```yaml
pins:
  - id: PC0                    # Required: Pin identifier (format: P[A-F][0-9][0-9]?)
    function: GPIO_Output      # Required: Pin function
    label: "LED"               # Optional: Human-readable label
    active_level: low          # Optional: Active level for output pins (low/high, default: high)
    pull: up                   # Optional: Pull resistor for input pins (up/down)
    af: 0                      # Optional: Alternate function number (default: 0)
    exti:                      # Optional: EXTI interrupt configuration
      enable: true
      trigger: falling         # rising/falling/both
    notify_task: "led_task"    # Optional: Task to notify on EXTI interrupt
```

**Valid functions**:
- `GPIO_Output`: General purpose output
- `GPIO_Input`: General purpose input
- `I2C_SCL`: I2C clock line
- `I2C_SDA`: I2C data line
- `SPI_SCK`: SPI clock
- `SPI_MISO`: SPI master-in slave-out
- `SPI_MOSI`: SPI master-out slave-in
- `SPI_NSS`: SPI chip select
- `UART_TX`: UART transmit
- `UART_RX`: UART receive
- `USART_TX`: USART transmit
- `USART_RX`: USART receive
- `LPUART_TX`: Low-power UART transmit
- `LPUART_RX`: Low-power UART receive
- `ADC_IN`: ADC input

### 1.3 Sleep Mode Configuration

```yaml
sleep:
  mode: STOP1                  # STOP0/STOP1/STOP2/STANDBY/SLEEP
```

### 1.4 Application Tasks

```yaml
app_tasks:
  - name: led_task             # Required: Task name
    priority: 2                # Optional: FreeRTOS priority (0-31, default: 1)
    stack_size: 128            # Optional: Stack size in words (default: 128)
```

**Special task names**:
- `led_task`: LED control task (requires a pin labeled "LED")
- `rtc_demo_task`: RTC demo task (requires Internal_RTC peripheral)

### 1.5 Peripherals

```yaml
peripherals:
  - name: "rtc"                # Required: Peripheral name
    type: "Internal_RTC"       # Required: Peripheral type
    interface: "internal"      # Required: Interface type
    clock_source: "LSE"        # Optional: Clock source (for RTC)
    features:                  # Optional: Feature list
      - calendar
    bus: "I2C1"                # Required for I2C/SPI peripherals
    extra:                     # Optional: Extra configuration
      baudrate: 115200         # For UART
      update_interval_ms: 1000 # For sensors
```

**Supported peripheral types**:

| Type | Description | Required Fields |
|------|-------------|----------------|
| `Internal_RTC` | Internal real-time clock | interface, clock_source |
| `Internal_PWM` | Internal PWM timer | - |
| `Internal_ADC` | Internal analog-to-digital converter | - |
| `UART_Serial` | UART serial communication | extra.baudrate |
| `I2C_Sensor_MPU6050` | MPU6050 accelerometer via I2C | bus |
| `SPI_Flash_W25Q32` | W25Q32 SPI flash | bus |

---

## 2. Business Flow DSL

### 2.1 Basic State Machine

```yaml
business_flow:
  initial_state: "IDLE"        # Required: Initial state name
  variables:                   # Optional: Global variables
    - name: "counter"          # Required: Variable name
      type: "uint32_t"         # Required: C data type
      initial: 0               # Optional: Initial value (default: 0)
  states:
    - name: "IDLE"             # Required: State name
      on_entry:                # Optional: Actions on entry
        - "toggle_led"
      on_exit:                 # Optional: Actions on exit
        - "toggle_led"
      after: 5000              # Optional: Timeout in ms
      history: false           # Optional: History mode (default: false)
      transitions:
        - event: "BUTTON_PRESS"    # Required: Triggering event
          target: "ACTIVE"         # Required: Target state
          guard: "counter < 3"     # Optional: Guard condition
          actions:                 # Optional: Actions on transition
            - "set counter inc"
            - "defer 3000 => toggle_led"
```

### 2.2 Compound States (Substates)

```yaml
business_flow:
  initial_state: "PROCESS"
  states:
    - name: "PROCESS"
      initial_state: "STEP1"    # Required for compound states
      states:                   # Substates
        - name: "STEP1"
          on_entry:
            - "defer 3000 => toggle_led"
          transitions:
            - event: "RTC_TICK"
              target: "STEP2"
        - name: "STEP2"
          transitions:
            - event: "RTC_TICK"
              actions:
                - "return"      # Return to parent state
      transitions:              # Parent-level transitions
        - event: "RETURN"
          target: "IDLE"
```

### 2.3 Parallel Regions

```yaml
business_flow:
  regions:                     # Parallel regions instead of states
    - name: "led_control"      # Required: Region name
      initial_state: "OFF"     # Required: Initial state
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

    - name: "counter"
      initial_state: "COUNTING"
      variables:
        - name: "count"
          type: "uint32_t"
          initial: 0
      states:
        - name: "COUNTING"
          transitions:
            - event: "RTC_TICK"
              target: "COUNTING"    # Self-loop
              actions:
                - "set count inc"
```

### 2.4 State References (Subflow)

```yaml
business_flow:
  initial_state: "IDLE"
  states:
    - name: "IDLE"
      transitions:
        - event: "BUTTON_PRESS"
          target: "BLINK"
    - name: "BLINK"
      type: "ref"              # Mark as reference
      ref: "common_subflow.yaml"  # Required: Path to subflow YAML
      namespace: "blinker"     # Required: Namespace prefix for variables/states
      transitions:              # Additional transitions at parent level
        - event: "STOP"
          target: "IDLE"
```

**Subflow file format** (`common_subflow.yaml`):
```yaml
business_flow:
  initial_state: "S1"
  states:
    - name: "S1"
      transitions:
        - event: "RTC_TICK"
          target: "S2"
          actions:
            - "toggle_led"
    - name: "S2"
      transitions:
        - event: "RTC_TICK"
          target: "S1"
          actions:
            - "toggle_led"
```

---

## 3. Actions Reference

### 3.1 Built-in Actions

| Action | Description | Example |
|--------|-------------|---------|
| `toggle_led` | Toggle the LED state | `- "toggle_led"` |
| `return` | Return from substate to parent | `- "return"` |

### 3.2 Variable Actions

| Action | Description | Example |
|--------|-------------|---------|
| `set <var> inc` | Increment variable | `- "set counter inc"` |
| `set <var> dec` | Decrement variable | `- "set counter dec"` |
| `set <var> <value>` | Set variable to value | `- "set counter 0"` |
| `calc <expression>` | Arbitrary C expression | `- "calc counter = counter + 1"` |

### 3.3 Timer Actions

| Action | Description | Example |
|--------|-------------|---------|
| `defer <ms> => <action>` | Execute action after delay | `- "defer 3000 => toggle_led"` |
| `timeline: <ms1>=>action1, <ms2>=>action2` | Multiple deferred actions | `- "timeline: 1000=>toggle_led, 2000=>toggle_led"` |
| `start_timer <name> <ms>` | Start named timer | `- "start_timer my_timer 5000"` |
| `stop_timer <name>` | Stop named timer | `- "stop_timer my_timer"` |

### 3.4 Event Actions

| Action | Description | Example |
|--------|-------------|---------|
| `publish <event>` | Synchronously publish event | `- "publish HIGH_COUNT"` |
| `publish_async <event>` | Asynchronously publish event | `- "publish_async HIGH_COUNT"` |
| `send_to <event>` | Send event to event queue | `- "send_to BUTTON_PRESS"` |

### 3.5 Conditional Actions

| Action | Description | Example |
|--------|-------------|---------|
| `when <condition> => <action>` | Execute action conditionally | `- "when counter > 5 => toggle_led"` |

---

## 4. Events Reference

### 4.1 Built-in Events

| Event | Trigger |
|-------|---------|
| `EVENT_BUTTON_PRESS` | EXTI interrupt from button pin |
| `EVENT_RTC_TICK` | RTC wake-up timer tick |
| `EVENT_RETURN` | Generated by `return` action |

### 4.2 Custom Events

Custom events are defined through `publish` or `publish_async` actions:

```yaml
actions:
  - "publish HIGH_COUNT"       # Creates EVENT_HIGH_COUNT
  - "publish_async TIMEOUT"    # Creates EVENT_TIMEOUT
```

---

## 5. Variable Types

**Recommended types**:
- `uint8_t`, `uint16_t`, `uint32_t` - Unsigned integers
- `int8_t`, `int16_t`, `int32_t` - Signed integers
- `float` - Floating point
- `bool` - Boolean (true/false)

---

## 6. Example: Complete Hardware YAML

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

sleep:
  mode: STOP1

app_tasks:
  - name: led_task
    priority: 2
    stack_size: 128
  - name: rtc_demo_task
    priority: 3
    stack_size: 512

peripherals:
  - name: "rtc"
    type: "Internal_RTC"
    interface: "internal"
    clock_source: "LSE"
    features:
      - calendar

business_flow:
  initial_state: "IDLE"
  variables:
    - name: "press_count"
      type: "uint32_t"
      initial: 0
  states:
    - name: "IDLE"
      after: 5000
      on_entry:
        - "toggle_led"
      transitions:
        - event: "BUTTON_PRESS"
          target: "ACTIVE"
          guard: "press_count < 3"
          actions:
            - "defer 3000 => toggle_led"
            - "set press_count inc"
        - event: "BUTTON_PRESS"
          target: "RESET"
          guard: "press_count >= 3"
          actions:
            - "set press_count 0"
    - name: "ACTIVE"
      on_entry:
        - "start_timer exit_timer 10000"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
          actions:
            - "stop_timer exit_timer"
        - event: "TIMER_EXPIRED_exit_timer"
          target: "IDLE"
          actions:
            - "stop_timer exit_timer"
    - name: "RESET"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
    - name: "TIMEOUT"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
```

---

## 7. Validation Rules

The generator validates the following:

### Critical Errors (Cannot continue)
- Missing `mcu.part`
- YAML parsing errors

### Errors (Recommended to fix)
- Missing required fields (pin id, function, state name, event, target)
- Invalid formats (pin ID, MCU part number)
- Invalid values (function names, EXTI trigger, sleep mode)
- Duplicate pin IDs
- Missing LED pin when `led_task` is defined
- Missing ref file for reference states

### Warnings (May cause unexpected behavior)
- Invalid pull values
- Unknown variable types
- Missing namespace for reference states
- Missing model files for peripherals

### Info
- Guard conditions used as-is without validation
