# task.yaml Reference

## Overview

`task.yaml` defines the **software architecture** of the project:
task partitioning, state-machine behavior, variable declarations, and custom types.

Hardware description is in [`hardware.yaml`](hardware-yaml.md).
The wiring between hardware and software is in [`bind.yaml`](bind-yaml.md).

---

## Schema Reference

### Top-Level Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `project` | object | No | `{}` | Project metadata |
| `project.name` | string | No | `"untitled"` | Project name |
| `project.version` | string | No | `"0.1.0"` | Project version |
| `app_tasks` | list | No | `[]` | FreeRTOS task definitions |
| `app_tasks[].name` | string | Yes | - | Task name |
| `app_tasks[].priority` | int | No | `1` | Task priority (0–31) |
| `app_tasks[].stack_size` | int | No | `128` | Stack size in words |
| `behavior` | object | No | `{}` | State-machine DSL |
| `behavior.initial_state` | string | Varies | - | Initial state name |
| `behavior.states` | list | Varies | `[]` | State definitions |
| `behavior.regions` | list | Varies | `[]` | Parallel region definitions |
| `behavior.variables` | list | No | `[]` | Global variable declarations |
| `behavior.events` | list | No | `[]` | Custom event declarations |
| `behavior.types` | list | No | `[]` | Custom type definitions (struct/enum/union/bitfield) |
| `behavior.types[].name` | string | Yes | - | Type name (e.g. `sensor_data_t`) |
| `behavior.types[].struct` | list | No | - | Struct fields (max 2 nesting levels) |
| `behavior.types[].struct[].name` | string | Yes | - | Field name |
| `behavior.types[].struct[].type` | string | No | - | C type; omit for nested struct (has `fields`) |
| `behavior.types[].struct[].array` | int | No | - | Array size if field is an array |
| `behavior.types[].struct[].fields` | list | No | - | Nested struct fields (level 2) |
| `behavior.types[].enum` | list | No | - | Enum values |
| `behavior.types[].enum[].name` | string | Yes | - | Enum value name |
| `behavior.types[].enum[].value` | int | No | auto | Enum value (auto-increments from 0) |
| `behavior.types[].union` | list | No | - | Union member fields |
| `behavior.types[].union[].name` | string | Yes | - | Member name |
| `behavior.types[].union[].type` | string | Yes | - | Member C type |
| `behavior.types[].union[].array` | int | No | - | Array size if member is an array |
| `behavior.types[].bitfield` | list | No | - | Bitfield definitions |
| `behavior.types[].bitfield[].name` | string | Yes | - | Bitfield member name |
| `behavior.types[].bitfield[].width` | int | Yes | - | Bit width (1–32) |
| `behavior.variables[].name` | string | Yes | - | Variable name |
| `behavior.variables[].type` | string | Yes | - | C type or custom type name |
| `behavior.variables[].array` | int | No | - | Array size (scalar → array conversion) |
| `behavior.variables[].initial` | any | No | - | Initial value |

> **Note**: `run_mode`, `triggers`, and `signals` have been removed from `app_tasks`.
> These are now defined in [`bind.yaml`](bind-yaml.md).
> FreeRTOS tasks are always `for(;;)` loops; single-shot behavior is implicitly defined by trigger conditions.

---

## 1. Project Metadata

```yaml
project:
  name: "smart_meter"         # Optional: Project name
  version: "0.1.0"            # Optional: Semantic version
```

## 2. Application Tasks

```yaml
app_tasks:
  - name: led_task             # Required: Task name
    priority: 2                # Optional: FreeRTOS priority (0-31, default: 1)
    stack_size: 128            # Optional: Stack size in words (default: 128)
  - name: sensor_task
    priority: 3
    stack_size: 512
  - name: mqtt_task
    priority: 4
    stack_size: 1024
```

**Special task names**:
- `led_task`: LED control task (requires a pin labeled "LED" in hardware.yaml)
- `rtc_demo_task`: RTC demo task (requires Internal_RTC peripheral)

Trigger and signal configuration has been moved to [`bind.yaml`](bind-yaml.md).

---

## 3. Business Flow DSL

### 3.1 Basic State Machine

```yaml
behavior:
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

### 3.2 Compound States (Substates)

```yaml
behavior:
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

### 3.3 Parallel Regions

```yaml
behavior:
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

### 3.4 State References (Subflow)

```yaml
behavior:
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
behavior:
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

## 4. Actions Reference

### 4.1 Built-in Actions

| Action | Description | Example |
|--------|-------------|---------|
| `toggle_led` | Toggle the LED state | `- "toggle_led"` |
| `return` | Return from substate to parent (fires `EVENT_RETURN`) | `- "return"` |

### 4.2 Variable Actions

| Action | Description | Example |
|--------|-------------|---------|
| `set <var> inc` | Increment variable | `- "set counter inc"` |
| `set <var> dec` | Decrement variable | `- "set counter dec"` |
| `set <var> <value>` | Set variable to value | `- "set counter 0"` |
| `calc <expression>` | Arbitrary C expression | `- "calc counter = counter + 1"` |

### 4.3 Timer Actions

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

### 4.4 Event Actions

| Action | Description | Example |
|--------|-------------|---------|
| `publish <event>` | Synchronously publish event | `- "publish HIGH_COUNT"` |
| `publish_async <event>` | Asynchronously publish event | `- "publish_async HIGH_COUNT"` |
| `send_to <region> <event>` | Cross-region async publish (3 parts: region name + event) | `- "send_to led_region LED_ON"` |

### 4.5 Conditional Actions

| Action | Description | Example |
|--------|-------------|---------|
| `when <condition> => <action>` | Execute action conditionally | `- "when counter > 5 => toggle_led"` |

### 4.6 Action Syntax Reference

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

## 5. Events Reference

### 5.1 Built-in Events

| Event | Trigger |
|-------|---------|
| `EVENT_NONE` | Sentinel (value 0) |
| `EVENT_BUTTON_PRESS` | EXTI interrupt from button pin |
| `EVENT_RTC_TICK` | RTC wake-up timer tick (100ms period) |
| `EVENT_RTC_ALARM` | RTC alarm interrupt |
| `EVENT_RETURN` | Generated by `return` action (substate → parent) |

### 5.2 RTC Auto-Generated Events

When `Internal_RTC` is present, these are auto-created by the RTC driver:

| Event | Period |
|-------|--------|
| `EVENT_MINUTE_TICK` | Every 60 seconds |
| `EVENT_HOUR_TICK` | Every 3600 seconds |

### 5.3 Timer Auto-Generated Events

These are automatically created based on DSL usage:

| Source | Event Name | Notes |
|--------|-----------|-------|
| `after: <ms>` on state | `EVENT_TIMER_EXPIRED_<state>_timeout` | One-shot |
| `start_timer <name> <ms>` | `EVENT_TIMER_EXPIRED_<name>` | One-shot |
| `defer <ms> => action` | `EVENT_TIMER_EXPIRED_defer_N` | `defer_0`, `defer_1`, ... |
| `timeline: <ms1>=>action, ...` | `EVENT_TIMER_EXPIRED_defer_0`, ... | Same as defer pattern |

### 5.4 Custom Events

Custom events are defined through `publish` or `publish_async` actions:

```yaml
actions:
  - "publish HIGH_COUNT"       # Creates EVENT_HIGH_COUNT
  - "publish_async TIMEOUT"    # Creates EVENT_TIMEOUT
```

---

## 6. Types & Variables

### 6.1 Custom Type Definitions (`behavior.types`)

Define reusable complex C types — structs, enums, unions, and bitfields.
Generated with `#pragma pack(push, 1)` for consistent memory layout on Cortex-M0+.

**Type kinds:**

| Kind | Key | C output |
|------|-----|----------|
| Struct | `struct` | `typedef struct { ... } name;` |
| Enum | `enum` | `typedef enum { ... } name;` |
| Union | `union` | `typedef union { ... } name;` |
| Bitfield | `bitfield` | `typedef struct { uint8_t f : w; ... } name;` |

**Struct (with optional nesting up to 2 levels):**

```yaml
behavior:
  types:
    - name: "sensor_data_t"
      struct:
        - { name: "temperature", type: "int16_t" }
        - { name: "humidity",  type: "uint8_t" }
        - { name: "accel"                    # Nested struct (omit type)
            fields:
              - { name: "x", type: "int16_t" }
              - { name: "y", type: "int16_t" }
              - { name: "z", type: "int16_t" }
          }
        - { name: "samples", type: "uint16_t", array: 8 }
```

Generates:

```c
#pragma pack(push, 1)
typedef struct {
    int16_t  temperature;
    uint8_t  humidity;
    struct {
        int16_t x;
        int16_t y;
        int16_t z;
    } accel;
    uint16_t samples[8];
} sensor_data_t;
#pragma pack(pop)
```

**Enum:**

```yaml
    - name: "device_state_t"
      enum:
        - { name: "OFF",    value: 0 }
        - { name: "IDLE",   value: 1 }
        - { name: "ACTIVE", value: 2 }
```

Generates:

```c
typedef enum {
    OFF    = 0,
    IDLE   = 1,
    ACTIVE = 2,
} device_state_t;
```

**Union:**

```yaml
    - name: "word_union_t"
      union:
        - { name: "raw",  type: "uint32_t" }
        - { name: "bytes", type: "uint8_t", array: 4 }
```

Generates:

```c
typedef union {
    uint32_t raw;
    uint8_t  bytes[4];
} word_union_t;
```

**Bitfield:**

```yaml
    - name: "config_flags_t"
      bitfield:
        - { name: "enable", width: 1 }
        - { name: "mode",   width: 3 }
        - { name: "speed",  width: 2 }
```

Generates:

```c
typedef struct {
    uint8_t enable : 1;
    uint8_t mode   : 3;
    uint8_t speed  : 2;
} config_flags_t;
```

### 6.2 Variable Declarations (`behavior.variables`)

**Scalar types:**

```yaml
  variables:
    - { name: "counter", type: "uint32_t", initial: 0 }
    - { name: "ready",   type: "bool",     initial: false }
```

**Custom type variables:**

```yaml
    - name: "sensor"
      type: "sensor_data_t"

    - name: "state"
      type: "device_state_t"
      initial: "IDLE"

    - name: "flags"
      type: "config_flags_t"
```

**Array variables** (scalar or custom type):

```yaml
    - name: "rx_buffer"
      type: "uint8_t"
      array: 256

    - name: "sensor_history"
      type: "sensor_data_t"
      array: 10
```

Generates:

```c
static uint32_t     counter = 0;
static bool         ready   = false;
static sensor_data_t sensor;
static device_state_t state = IDLE;
static config_flags_t flags;
static uint8_t       rx_buffer[256];
static sensor_data_t sensor_history[10];
```

### 6.3 Accessing Members in Actions

Extended dot and bracket syntax in guards / calc / set:

| Syntax | Meaning |
|--------|---------|
| `sensor.temperature` | Struct member access |
| `sensor.accel.x` | Nested struct member (2 levels) |
| `rx_buffer[0]` | Array element access |
| `sensor_history[2].temperature` | Array of struct member |
| `word.bytes[0]` | Union member + array index |

```yaml
  on_entry:
    - "set sensor.temperature = 0"
    - "calc sensor.temperature = adc_read * 3300 / 4096"
  transitions:
    - event: "TICK"
      guard: "sensor.temperature > 30 && state == ACTIVE"
      target: "ALERT"
```

### 6.4 Built-in Scalar Types (always valid)

- `uint8_t`, `uint16_t`, `uint32_t`
- `int8_t`, `int16_t`, `int32_t`
- `float`
- `bool`

---

## 7. Example: Complete task.yaml

```yaml
project:
  name: "smart_meter"
  version: "0.1.0"

app_tasks:
  - name: led_task
    priority: 2
    stack_size: 128
  - name: sensor_task
    priority: 3
    stack_size: 512
  - name: mqtt_task
    priority: 4
    stack_size: 1024

behavior:
  initial_state: "IDLE"
  types:
    - name: "sensor_data_t"
      struct:
        - { name: "temperature", type: "int16_t" }
        - { name: "humidity", type: "uint8_t" }
  variables:
    - name: "press_count"
      type: "uint32_t"
      initial: 0
    - name: "readings"
      type: "sensor_data_t"
      array: 32
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
            - "set press_count inc"
        - event: "BUTTON_PRESS"
          target: "RESET"
          guard: "press_count >= 3"
          actions:
            - "set press_count 0"
    - name: "ACTIVE"
      on_entry:
        - "publish_async DATA_READY"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
    - name: "RESET"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
```

---

## 8. Validation Rules

### Errors
- Missing required fields (task name, state name, event, target)
- Compound state (has `states`) missing `initial_state`
- `initial_state` missing in region definitions
- Ref type state missing `ref` path or ref file not found
- `behavior` defined with neither `states` nor `regions`
- Unknown actions in `on_entry`/`on_exit`/transition `actions`

### Warnings
- Unknown variable types (recommended: `uint8_t`..`uint32_t`, `int8_t`..`int32_t`, `float`, `bool`, or custom type name)
- Missing namespace for reference states (may cause name conflicts)
- Events referenced in `bind.yaml` but not declared in `behavior`

### Info
- Guard conditions: embedded as-is into C code without validation — errors surface at compile time
- Published events: `publish`/`publish_async` events are collected into `EVENT_<name>` enum entries automatically
