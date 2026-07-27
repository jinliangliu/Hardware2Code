# Hardware2Code DSL Reference

## Overview

Hardware2Code uses a YAML-based DSL (Domain-Specific Language) to describe:
1. **Hardware Configuration**: MCU, pins, peripherals, tasks, sleep mode
2. **Business Flow**: State machines, transitions, actions, variables

---

## Schema Reference

Complete `hardware.yaml` top-level schema. Every key, its type, whether it is required, default value, and description.

### Top-Level Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `mcu` | object | Yes | - | MCU configuration |
| `mcu.part` | string | Yes | - | MCU part number (e.g. `STM32G0B1RET6`) |
| `mcu.core_clock_mhz` | int | No | 64 | Core clock frequency in MHz |
| `mcu.hse_freq` | int | No | 8000000 | HSE crystal frequency in Hz |
| `pins` | list | No | `[]` | Pin configuration list |
| `pins[].id` | string | Yes | - | Pin identifier (`PA0` – `PF15`) |
| `pins[].function` | string | Yes | - | Pin function (see [Pin Function Enumeration](#12-pin-configuration)) |
| `pins[].label` | string | No | `""` | Human-readable label |
| `pins[].pull` | string | No | `none` | Pull resistor: `up` / `down` |
| `pins[].af` | int | No | `0` | Alternate function number |
| `pins[].notify_task` | string | No | `""` | FreeRTOS task to notify on EXTI |
| `pins[].exti` | object | No | `{}` | EXTI interrupt configuration |
| `pins[].exti.enable` | bool | No | `false` | Enable EXTI interrupt |
| `pins[].exti.trigger` | string | No | `-` | Edge trigger: `rising` / `falling` / `both` |
| `peripherals` | list | No | `[]` | Peripheral configurations |
| `peripherals[].name` | string | Yes | - | Peripheral instance name |
| `peripherals[].type` | string | Yes | - | Peripheral type (see [Peripheral Types](#15-peripherals)) |
| `peripherals[].bus` | string | Varies | - | Bus instance (`I2C1`, `SPI1`, …) |
| `peripherals[].bearer` | string | Varies | - | Communication bearer name (protocols) |
| `peripherals[].broker` | string | Varies | - | MQTT broker URL |
| `peripherals[].extra` | object | Varies | `{}` | Type-specific extra parameters (see below) |
| `app_tasks` | list | No | `[]` | FreeRTOS task definitions |
| `app_tasks[].name` | string | Yes | - | Task name |
| `app_tasks[].priority` | int | No | `1` | Task priority (0–31) |
| `app_tasks[].stack_size` | int | No | `128` | Stack size in words |
| `sleep` | object | No | `{}` | Low-power configuration |
| `sleep.mode` | string | No | `STOP0` | Sleep mode: `STOP0` / `STOP1` / `STOP2` / `STANDBY` / `SLEEP` |
| `bootloader` | object | No | `{}` | Bootloader configuration |
| `bootloader.enabled` | bool | No | `false` | Enable dual-slot bootloader |
| `bootloader.size_kb` | int | No | `8` | Bootloader Flash size in KB (4–32) |
| `bootloader.app_a_offset` | int | No | `0x2000` | App Slot A start offset |
| `bootloader.app_b_offset` | int | No | `0x40000` | App Slot B start offset |
| `bootloader.wdg_timeout_ms` | int | No | `5000` | Watchdog timeout in ms |
| `bootloader.max_retries` | int | No | `3` | Max consecutive boot failures (1–10) |
| `business_flow` | object | No | `{}` | State-machine DSL |
| `business_flow.initial_state` | string | Varies | - | Initial state name |
| `business_flow.states` | list | Varies | `[]` | State definitions |
| `business_flow.regions` | list | Varies | `[]` | Parallel region definitions |
| `business_flow.variables` | list | No | `[]` | Global variable declarations |
| `business_flow.events` | list | No | `[]` | Custom event declarations |
| `hil` | object | No | `{}` | HIL test configuration |
| `hil.baudrate` | int | No | `115200` | HIL UART baudrate |
| `hil.uart` | string | No | `UART2` | HIL UART instance |
| `heap_size` | string | No | `0x200` | Heap size (hex literal) |
| `stack_size` | string | No | `0x400` | Stack size (hex literal) |

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

**Valid functions** — all supported `pins[].function` values:

| Function | Description |
|----------|-------------|
| `GPIO_Output` | General-purpose output (push-pull) |
| `GPIO_Input` | General-purpose input (floating) |
| `I2C_SCL` | I2C clock line (any I2C bus) |
| `I2C_SDA` | I2C data line (any I2C bus) |
| `I2C1_SCL` | I2C1 clock line |
| `I2C1_SDA` | I2C1 data line |
| `I2C2_SCL` | I2C2 clock line |
| `I2C2_SDA` | I2C2 data line |
| `SPI_SCK` | SPI clock (any SPI bus) |
| `SPI_MISO` | SPI master-in slave-out (any SPI bus) |
| `SPI_MOSI` | SPI master-out slave-in (any SPI bus) |
| `SPI_NSS` | SPI chip select (any SPI bus) |
| `SPI1_SCK` | SPI1 clock |
| `SPI1_MISO` | SPI1 MISO |
| `SPI1_MOSI` | SPI1 MOSI |
| `SPI1_NSS` | SPI1 NSS |
| `SPI2_SCK` | SPI2 clock |
| `SPI2_MISO` | SPI2 MISO |
| `SPI2_MOSI` | SPI2 MOSI |
| `SPI2_NSS` | SPI2 NSS |
| `UART_TX` | UART transmit (any UART) |
| `UART_RX` | UART receive (any UART) |
| `USART_TX` | USART transmit (any USART) |
| `USART_RX` | USART receive (any USART) |
| `USART1_TX` | USART1 transmit |
| `USART1_RX` | USART1 receive |
| `USART2_TX` | USART2 transmit |
| `USART2_RX` | USART2 receive |
| `LPUART_TX` | Low-power UART transmit |
| `LPUART_RX` | Low-power UART receive |
| `RS485_DE` | RS485 direction-control (DE/RE) |
| `ADC_IN` | Analog-to-digital input (general) |
| `ADC_IN1` – `ADC_IN16` | ADC input channels 1–16 |
| `IR_OUT` | Infrared transmitter output |
| `IR_IN` | Infrared receiver input |
| `CELL_PWR` | Cellular modem power key |
| `CELL_RST` | Cellular modem reset |

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

| Type | Required Bus | `extra` Parameters | Description |
|------|-------------|--------------------|-------------|
| `Internal_RTC` | - | - | Internal real-time clock (LSE) |
| `Internal_PWM` | - | `timer`, `channel`, `freq`, `duty` | Internal PWM output |
| `Internal_ADC` | - | `channel`, `resolution` | Internal analog-to-digital converter |
| `Internal_CLI` | - | `uart` (carrier name) | UART-based debug command shell |
| `Internal_IR` | - | `carrier_freq` | Infrared NEC/SIR communication |
| `Internal_IWDG` | - | `wdg_timeout_ms` | Independent watchdog timer |
| `UART_Serial` | - | `baudrate` | UART serial communication |
| `I2C_Sensor_MPU6050` | I2C bus | `update_interval_ms` | MPU6050 accelerometer via I2C |
| `SPI_Flash_W25Q32` | SPI bus | `chip_select_pin` | W25Q32 SPI NOR Flash |
| `SPI_Flash_Generic` | SPI bus | `chip_select_pin`, `total_size` | Generic SPI NOR Flash |
| `I2C_EEPROM` | I2C bus | `i2c_addr`, `page_size`, `total_size` | I2C EEPROM storage |
| `RS485` | - | `uart`, `de_pin`, `baudrate` | RS485 half-duplex transceiver |
| `Cellular_4G` | - | `uart`, `apn`, `baudrate` | 4G Cat.1 cellular module |
| `Protocol_Modbus` | - | `bearer`, `role` (master/slave), `slave_id` | Modbus RTU protocol |
| `Protocol_MQTT` | - | `bearer`, `broker`, `client_id`, `topic` | MQTT 3.1.1 client |

### 1.6 Communication Peripherals

```yaml
peripherals:
  # RS485 example
  - name: "rs485_1"
    type: "RS485"
    uart: "uart2"          # Reference to UART_Serial peripheral name
    de_pin: "PA1"          # RS485 direction control pin (RE/DE)
    extra:
      baudrate: 9600

  # Cellular 4G Cat.1 example
  - name: "cellular"
    type: "Cellular_4G"
    uart: "uart2"
    power_pin: "PC4"       # Optional: power control
    reset_pin: "PC5"       # Optional: reset control
    extra:
      apn: "ctnet"         # APN for PDP activation

  # IR NEC example
  - name: "ir"
    type: "Internal_IR"
    mode: "nec"            # nec | sir (default: nec)
    tx_pin: "PB0"
    rx_pin: "PB1"

  # Modbus RTU slave example
  - name: "modbus"
    type: "Protocol_Modbus"
    bearer: "rs485_1"      # Reference to RS485 or UART peripheral
    role: "slave"
    slave_id: 1

  # MQTT client example
  - name: "mqtt"
    type: "Protocol_MQTT"
    bearer: "cellular"     # Reference to Cellular_4G peripheral
    broker: "iot.telecom.com"
    port: 1883
    client_id: "device001"
    extra:
      username: "optional_user"
      password: "optional_pass"
      keep_alive_s: 60

  # CLI debug shell example
  - name: "cli"
    type: "Internal_CLI"
    uart: "uart_debug"     # Reference to UART_Serial peripheral
    extra:
      prompt: "h2c> "      # Optional: shell prompt, default "> "
      stack_size: 512       # Optional: CLI task stack, default 512
      priority: 4           # Optional: CLI task priority, default 4
      max_cmd_len: 64       # Optional: max command length, default 64
```

### 1.7 Bootloader Configuration

```yaml
bootloader:
  enabled: true               # Required: Enable dual-slot bootloader
  size_kb: 8                  # Optional: Bootloader Flash size (default: 8)
  max_retries: 3              # Optional: Max consecutive boot failures before slot swap (default: 3)
  app_a_offset: 0x2000        # Optional: App Slot A start offset (default: 0x2000)
  app_b_offset: 0x40000       # Optional: App Slot B start offset (default: 0x40000)
  crc_method: crc32_hw        # Optional: CRC method (default: crc32_hw)
  boot_flag_src: tamp_bkp     # Optional: Boot flag storage (default: tamp_bkp)
  wdg_timeout_ms: 5000        # Optional: Watchdog timeout (default: 5000)
```

When enabled, the bootloader occupies the first `size_kb` KB of Flash and manages two App slots:

- **App Slot A**: `app_a_offset` → `app_b_offset` (Bank 1 remainder)
- **App Slot B**: `app_b_offset` → flash end (Bank 2)

The bootloader flow:
1. Read TAMP backup registers for boot state
2. If previous boot was OK → clear counter → CRC check → jump to App
3. If previous boot failed → increment counter → CRC check → jump to App
4. If counter exceeds `max_retries` → swap to other slot → soft reset
5. If CRC fails → swap slot → soft reset (indicates corrupted firmware)
6. If both slots fail → LED SOS pattern (recovery mode)

Supported CRC methods:
- `crc32_hw`: STM32G0 hardware CRC unit (fast, low code size)

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
| `return` | Return from substate to parent (fires `EVENT_RETURN`) | `- "return"` |

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
| `start_timer <name> <ms>` | Start named one-shot timer | `- "start_timer my_timer 5000"` |
| `stop_timer <name>` | Stop and delete named timer | `- "stop_timer my_timer"` |

**Notes**:
- `defer` and `timeline` are syntactic sugar: they auto-generate timer names (`defer_0`, `defer_1`, ...) and convert to `start_timer defer_N <ms>` internally.
- Each `start_timer` automatically creates a callback that fires `EVENT_TIMER_EXPIRED_<name>` when the timer expires.
- `after: <ms>` on a state also auto-creates a timer named `<state>_timeout`, firing `EVENT_TIMER_EXPIRED_<state>_timeout` on expiry.
- All defer timers are automatically stopped and deleted on state exit.

### 3.4 Event Actions

| Action | Description | Example |
|--------|-------------|---------|
| `publish <event>` | Synchronously publish event | `- "publish HIGH_COUNT"` |
| `publish_async <event>` | Asynchronously publish event | `- "publish_async HIGH_COUNT"` |
| `send_to <region> <event>` | Cross-region async publish (3 parts: region name + event) | `- "send_to led_region LED_ON"` |

### 3.5 Conditional Actions

| Action | Description | Example |
|--------|-------------|---------|
| `when <condition> => <action>` | Execute action conditionally | `- "when counter > 5 => toggle_led"` |

### 3.6 Action Syntax Reference

All actions support two equivalent formats: **string syntax** (compact, human-readable) and **dict syntax** (machine-friendly, YAML-native).

#### String-Format Actions

| Action String | Description | Example |
|--------------|-------------|---------|
| `toggle_led` | Toggle LED output | `toggle_led` |
| `return` | Return from substate to parent | `return` |
| `set VAR VALUE` | Set variable to value (`inc`/`dec` supported) | `set count 0`, `set count inc` |
| `calc VAR = EXPR` | Evaluate C expression, assign to variable | `calc result = count * 2 + 1` |
| `publish EVENT` | Synchronously publish event | `publish SENSOR_READY` |
| `publish_async EVENT` | Asynchronously publish event | `publish_async ALERT` |
| `start_timer NAME MS` | Start named one-shot timer | `start_timer exit_timer 3000` |
| `stop_timer NAME` | Stop and delete named timer | `stop_timer exit_timer` |
| `when COND => ACTION` | Conditional action execution | `when count > 5 => publish OVERFLOW` |
| `defer MS => ACTION` | Deferred action after delay | `defer 1000 => toggle_led` |
| `timeline: MS=>ACT, ...` | Timeline of deferred actions | `timeline: 100=>toggle_led, 500=>publish DONE` |
| `send_to REGION EVENT` | Cross-region event (3 tokens) | `send_to region_a RESET` |

#### Dict-Format Actions (Equivalent)

| Dict Format | Equivalent String |
|------------|-------------------|
| `{toggle_led: null}` | `toggle_led` |
| `{return: null}` | `return` |
| `{set: {var: count, value: 5}}` | `set count 5` |
| `{set: {var: count, value: inc}}` | `set count inc` |
| `{calc: {var: r, expr: c * 2}}` | `calc r = c * 2` |
| `{publish: {event: READY}}` | `publish READY` |
| `{publish_async: {event: ALERT}}` | `publish_async ALERT` |
| `{start_timer: {name: t, ms: 1000}}` | `start_timer t 1000` |
| `{stop_timer: {name: t}}` | `stop_timer t` |
| `{defer: {after: 1000, do: toggle_led}}` | `defer 1000 => toggle_led` |
| `{timeline: [{ms: 100, do: toggle_led}, {ms: 500, do: publish DONE}]}` | `timeline: 100=>toggle_led, 500=>publish DONE` |
| `{when: {condition: "count > 5", do: toggle_led}}` | `when count > 5 => toggle_led` |
| `{send_to: {region: region_a, event: RESET}}` | `send_to region_a RESET` |

---

## 4. Events Reference

### 4.1 Built-in Events

| Event | Trigger |
|-------|---------|
| `EVENT_NONE` | Sentinel (value 0) |
| `EVENT_BUTTON_PRESS` | EXTI interrupt from button pin |
| `EVENT_RTC_TICK` | RTC wake-up timer tick (100ms period) |
| `EVENT_RTC_ALARM` | RTC alarm interrupt |
| `EVENT_RETURN` | Generated by `return` action (substate → parent) |

### 4.2 RTC Auto-Generated Events

When `Internal_RTC` is present, these are auto-created by the RTC driver:

| Event | Period |
|-------|--------|
| `EVENT_MINUTE_TICK` | Every 60 seconds |
| `EVENT_HOUR_TICK` | Every 3600 seconds |

### 4.3 Timer Auto-Generated Events

These are automatically created based on DSL usage:

| Source | Event Name | Notes |
|--------|-----------|-------|
| `after: <ms>` on state | `EVENT_TIMER_EXPIRED_<state>_timeout` | One-shot |
| `start_timer <name> <ms>` | `EVENT_TIMER_EXPIRED_<name>` | One-shot |
| `defer <ms> => action` | `EVENT_TIMER_EXPIRED_defer_N` | `defer_0`, `defer_1`, ... |
| `timeline: <ms1>=>action, ...` | `EVENT_TIMER_EXPIRED_defer_0`, ... | Same as defer pattern |

**Example**: For a state `PLAYING` with `after: 5000`, use event `TIMER_EXPIRED_PLAYING_timeout` in transitions to react to the timeout.

### 4.4 Custom Events

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
- Invalid formats (pin ID regex `^P[A-F][0-9]{1,2}$`, MCU part number)
- Invalid pin functions (must be one of 15 supported functions)
- Invalid EXTI trigger values (must be `rising`/`falling`/`both`)
- Duplicate pin IDs
- Missing LED pin when `led_task` is defined in `app_tasks`
- Missing `bus` field for I2C (`I2C_Sensor_MPU6050`) and SPI (`SPI_Flash_W25Q32`) peripherals
- Compound state (has `states`) missing `initial_state`
- `initial_state` missing in region definitions
- Ref type state missing `ref` path or ref file not found
- `business_flow` defined with neither `states` nor `regions`
- Unknown actions in `on_entry`/`on_exit`/transition `actions`

### Warnings (May cause unexpected behavior)
- No pins defined
- Invalid pull values (only `up`/`down` valid)
- Unknown variable types (recommended: `uint8_t`..`uint32_t`, `int8_t`..`int32_t`, `float`, `bool`)
- Missing namespace for reference states (may cause name conflicts)
- Missing model files for peripheral types
- Invalid `sleep.mode` (valid: `STOP0`/`STOP1`/`STOP2`/`STANDBY`/`SLEEP`)

### Info
- Guard conditions: embedded as-is into C code without validation — errors surface at compile time
- Published events: `publish`/`publish_async` events are collected into `EVENT_<name>` enum entries automatically

---

## 8. CLI Debug Shell Commands

When `Internal_CLI` is enabled, the following commands are available at the UART prompt:

| Command | Description | Availability |
|---------|-------------|-------------|
| `help` | List all available commands | Always |
| `version` | Show firmware version and build time | Always |
| `uptime` | Show system uptime | Always |
| `free` | Show free heap memory | Always |
| `tasks` | List FreeRTOS tasks | Always |
| `reset` | Software reset MCU | Always |
| `gpio read <pin>` | Read GPIO pin level | When pins configured |
| `gpio write <pin> <0\|1>` | Set GPIO output | When pins configured |
| `led on\|off\|toggle` | Control LED | When LED pin exists |
| `rtc time` | Show RTC time | When RTC enabled |
| `rtc set <HH:MM:SS>` | Set RTC time | When RTC enabled |
| `modbus read <addr> <count>` | Read holding registers | When Modbus enabled |
| `modbus write <addr> <value>` | Write single register | When Modbus enabled |
| `cellular status\|imei\|csq` | Cellular modem info | When Cellular enabled |
| `mqtt status` | MQTT connection status | When MQTT enabled |
| `mqtt publish <topic> <payload>` | Publish MQTT message | When MQTT enabled |
| `fota version` | Show firmware version | When FOTA enabled |
| `fota start` | Enter FOTA receive mode | When FOTA enabled |
