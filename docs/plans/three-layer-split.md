# Three-Layer Split Plan: hardware.yaml / task.yaml / bind.yaml

## 1. Overview

Split the current monolithic `hardware.yaml` into three focused files:

| File | Responsibility | Produced by |
|------|---------------|-------------|
| `hardware.yaml` | Physical hardware facts (pins, peripherals, clock, sleep) | Netlist parser + manual review |
| `task.yaml` | Software architecture (tasks, state machine, variables, types) | User authoring |
| `bind.yaml` | Wiring layer (interrupt→task, peripheral→task, task→task routing) | User drag-and-drop mapping |

## 2. Data Model Split

### 2.1 `hardware.yaml` — Hardware Capabilities

```yaml
mcu:
  part: STM32G0B1RET6
  core: Cortex-M0+
  core_clock_mhz: 64
  ram_kb: 144
  flash_kb: 512
  dual_bank: true

pins:
  - { id: "PC0",  function: "GPIO_Output", label: "LED", active_level: "low" }
  - { id: "PC13", function: "GPIO_Input",  label: "BUTTON",
      pull: "up", exti: { enable: true, trigger: "falling" } }
  - { id: "PA2",  function: "USART1_TX" }
  - { id: "PA3",  function: "USART1_RX" }

peripherals:
  - { name: "max3232",   type: "UART_Serial",      bus: "USART1" }
  - { name: "spi_flash", type: "SPI_Flash_W25Q32", bus: "SPI1" }
  - { name: "rtc",       type: "Internal_RTC",     interface: "internal" }

sleep:
  mode: STOP1

clock:
  hsi_hz: 16000000
  lsi_hz: 32000
  hse:  { present: true, frequency_hz: 8000000 }
  lse:  { present: true, frequency_hz: 32768 }
  pll:  { source: "HSE", m: 1, n: 8, r: 2 }
  sysclk: { source: "PLL", frequency_hz: 64000000 }
  apb: { prescaler: 1 }
  freertos_tick: { source: "SysTick", frequency_hz: 1000 }
```

**Key changes**:
- `mcu.core` **new field** — CPU core model (e.g. `Cortex-M0+`)
- `pins[].notify_task` is **removed** — moves to `bind.yaml`

### 2.2 `task.yaml` — Software Definition

```yaml
project:
  name: "smart_meter"
  version: "0.1.0"

app_tasks:
  - { name: "led_task",    priority: 2, stack_size: 128 }
  - { name: "sensor_task", priority: 3, stack_size: 512 }
  - { name: "mqtt_task",   priority: 4, stack_size: 1024 }

business_flow:
  types:
    - name: "sensor_data_t"
      struct:
        - { name: "temp", type: "int16_t" }
        - { name: "humidity", type: "uint8_t" }
  variables:
    - { name: "readings", type: "sensor_data_t", array: 32 }
    - { name: "press_count", type: "uint32_t", initial: 0 }
  initial_state: "IDLE"
  states:
    - name: "IDLE"
      transitions:
        - { event: "BUTTON_PRESS", target: "ACTIVE" }
        - { event: "ADC_DONE",    target: "READ" }
```

**Key changes**:
- `app_tasks` no longer has `run_mode`, `triggers`, `signals` — those are `bind.yaml` concepts
- `business_flow` moves entirely here from hardware.yaml
- `project` metadata is new

### 2.3 `bind.yaml` — Hardware ⇔ Software Wiring

```yaml
version: 1

hardware: "hardware.yaml"   # reference (resolved by CLI or in-memory)
task:     "task.yaml"

# --- Interrupt → Task ---
interrupt:
  - { pin: "PC13", task: "led_task",    event: "BUTTON_PRESS" }
  - { pin: "PA0",  task: "sensor_task", event: "ADC_DONE" }

# --- Peripheral → Task ---
peripheral_assign:
  - { peripheral: "max3232",   task: "shell_task",   role: "cli_uart" }
  - { peripheral: "spi_flash", task: "fota_task",    role: "storage" }
  - { peripheral: "rtc",       task: "sensor_task",  role: "tick_timer" }

# --- Task → Task routing ---
routing:
  - { from: "sensor_task", to: "mqtt_task", signal: "data_ready" }
  - { from: "sensor_task", to: "led_task",  signal: "alert",
      condition: "readings.temp > 50" }
```

## 3. Implementation Phases

### Phase 1: DSL Documentation (no code changes)

**Files:** `docs/user-guide/`

| Action | File |
|--------|------|
| Split hardware-yaml.md → remove `business_flow`, `app_tasks` | `docs/user-guide/hardware-yaml.md` |
| New `mcu.core` field in hardware-yaml.md schema table | `docs/user-guide/hardware-yaml.md` |
| Create task-yaml.md with `project`, `app_tasks`, `business_flow` | `docs/user-guide/task-yaml.md` (new) |
| Create bind-yaml.md with `interrupt`, `peripheral_assign`, `routing` | `docs/user-guide/bind-yaml.md` (new) |
| Update mkdocs navigation | `mkdocs.yml` |

### Phase 2: Parser — Output Two YAML strings

**Files:** `parser/`

| Action | File |
|--------|------|
| `PipelineResult.yaml` → deprecated, add `hardware_yaml` + `task_yaml` fields | `parser/pipeline.py` |
| Remove `business_flow` / `app_tasks` generation from netlist parsers | `parser/netlist_parser.py`, `parser/netlist_parser_enet.py` |
| Add `"core": "Cortex-M0+"` to default MCU dict | `parser/bom_parser.py` |
| Generate default empty `task.yaml` from parser (with detected tasks from pins) | `parser/pipeline.py` |
| CLI `parse` subcommand: output hardware.yaml; `--task` flag also writes task.yaml | `parser/cli.py` |

### Phase 3: Generator — Accept Three Files

**Files:** `generator/`

| Action | File |
|--------|------|
| Add new `BindModel`, `RoutingModel`, `InterruptBindingModel`, `PeripheralAssignModel` Pydantic schemas | `generator/schemas/bind.py` (new) |
| Split `BusinessFlowModel` → `TaskModel` (top-level) + `BusinessFlowModel` (inside task.yaml) | `generator/schemas/task.py` (new) |
| Strip `business_flow` and `app_tasks` from `HardwareModel` | `generator/schemas/hardware.py` |
| Add `core: str = ""` field to `McuModel` | `generator/schemas/hardware.py` |
| Add `core: str` to `McuConfig` TypedDict | `generator/types.py` |
| New `mapper.py` that merges hardware + task + bind into a unified internal dict | `generator/mapper.py` (new) |
| Update `build_context()` to accept the mapped dict (API unchanged internally) | `generator/context/builder.py` |
| Update `generate_project()` to accept `--task` and `--bind` args | `generator/generate.py` |
| Update CLI `gen` subcommand | `parser/cli.py` |
| Backward compatibility: if no task/bind files given, extract from hardware.yaml internally | `generator/mapper.py` |

### Phase 4: Web Backend — Multi-YAML Response & Generation

#### 4.1 `backend/schemas.py` — Split Response Model

| Action | Detail |
|--------|--------|
| `AppTaskInfo` | Remove `run_mode`, `triggers`, `signals` fields (moved to bind.yaml) |
| `McuInfo` | Add `core: str = ""` field |
| New `ProjectInfo` | `{ name: str, version: str }` |
| New `BindInterruptInfo` | `{ pin: str, task: str, event: str }` |
| New `BindPeripheralAssignInfo` | `{ peripheral: str, task: str, role: str }` |
| New `BindRoutingInfo` | `{ from: str, to: str, signal: str, condition: Optional[str] }` |
| New `BindInfo` | `{ hardware: str, task: str, interrupt: List[], peripheral_assign: List[], routing: List[] }` |
| `ParseResponse` | Add `project: Optional[ProjectInfo]`, `bind: Optional[BindInfo]`, `task_yaml: str`, `bind_yaml: str` |
| `ParseResponse.yaml` | Rename to `hardware_yaml: str` (backward compat: old `yaml` field kept as alias) |

Response changes:
```
Before:  { yaml: "monolith hardware.yaml", app_tasks: [...] }
After:   { hardware_yaml: "...", task_yaml: "...", bind_yaml: "...", bind: {...}, project: {...} }
```

#### 4.2 `backend/routes/parse.py` — Split YAML Output

| Action | Detail |
|--------|--------|
| Parse new `PipelineResult.hardware_yaml` + `task_yaml` | After Phase 2, pipeline returns split strings |
| Generate default `BindInfo` | If no `bind_yaml` yet, create empty bind with `hardware = "hardware.yaml"` / `task = "task.yaml"` |
| `AppTaskInfo` construction | Use `task_yaml` dict's `app_tasks`, not old monolithic yaml |
| Fallback for old pipeline | If `result.task_yaml` is empty, call `_split_legacy(result.yaml)` |

#### 4.3 `backend/routes/generate.py` — Accept Three YAML Files

| Action | Detail |
|--------|--------|
| `GenerateRequest` model | Replace single `yaml` field with `hardware_yaml`, `task_yaml` (required), `bind_yaml` (optional) |
| Temp file layout | Write `hardware.yaml` + `task.yaml` + `bind.yaml` (if present) to `tmpdir` |
| CLI invocation | `gen -i hardware.yaml --task task.yaml --bind bind.yaml -o output_dir --force` |
| Fallback for single yaml | If old frontend sends `yaml` field only, treat as legacy monolithic and write as `hardware.yaml` |

### Phase 5: Web Frontend — Multi-Tab Workflow

#### 5.1 `src/api.ts` — Updated Types & API

| Action | Detail |
|--------|--------|
| `ParseResponse` | Add `task_yaml: string`, `bind_yaml?: string`, `project?: ProjectInfo`, `bind?: BindInfo`; `mcu` add `core: string` |
| New `ProjectInfo` | `{ name: string, version: string }` |
| New `BindInfo` | `{ hardware: string, task: string, interrupt: [], peripheral_assign: [], routing: [] }` |
| New `BindInterruptInfo` | `{ pin: string, task: string, event: string }` |
| New `BindPeripheralAssignInfo` | `{ peripheral: string, task: string, role: string }` |
| New `BindRoutingInfo` | `{ from: string, to: string, signal: string, condition?: string }` |
| `AppTaskInfo` | Remove `run_mode`, `triggers`, `signals` |
| `generateFirmware()` | Signature change: `(hardwareYaml: string, taskYaml: string, bindYaml?: string, projectName?: string) => Promise<Blob>` |

#### 5.2 `src/composables/` — Split State Management

| Action | File | Detail |
|--------|------|--------|
| Strip `app_tasks` and `business_flow` | `useHardwareModel.ts` | `HardwareModel` only has `mcu`, `pins`, `peripherals`, `sleep`, `clock` |
| Add `core: string` to `McuModel` | `useHardwareModel.ts` | Default `"Cortex-M0+"`, YAML parse read `m.core` |
| New composable | `useTaskModel.ts` | `TaskModel { project: ProjectInfo, app_tasks: AppTaskModel[], business_flow: BusinessFlowModel }`; YAML sync for `task_yaml` ref |
| New composable | `useBindModel.ts` | `BindModel { interrupt: [], peripheral_assign: [], routing: [] }`; YAML sync for `bind_yaml` ref |
| `loadFromApi` | `useHardwareModel.ts` | After parse, also call `loadFromApi` on task and bind models |

#### 5.3 `src/App.vue` — Tab Layout Restructure

**Tab layout (4 tabs):**

| Tab | Label | Content | Data source |
|-----|-------|---------|-------------|
| 1 | Hardware | PinChip + ClockTree + Pin config editor | `hardwareModel` |
| 2 | Tasks | TaskGraph (pure tasks) + Business Flow editor | `taskModel` |
| 3 | Bind | BindGraph (drag pin→task, task→task) | `bindModel` + refs to hardware/task |
| 4 | YAML | Triple-pane YAML preview (hardware / task / bind) | `hardwareYamlRef` / `taskYamlRef` / `bindYamlRef` |

Changes to current layout:
- Left column stays largely same (FileUpload, MCU Card, Topology, PeripheralList, PeripheralConfig, BusHints)
- Generate button moves to YAML tab
- `app_tasks` ref removed from `useHardwareModel`; accessed via `useTaskModel` instead

#### 5.4 `src/components/TaskGraph.vue` — Simplify to Pure Task Definitions

| Action | Detail |
|--------|--------|
| Remove trigger/signal handles from task nodes | Task nodes only show name + priority + stack_size |
| Remove trigger source nodes (GPIO / Timer / RTC) | Those belong in BindGraph |
| Task-to-task connections for `business_flow` states | Keep state-machine transitions as separate graph (or in Business Flow editor panel) |
| Double-click to rename | Keep in-place rename |
| Run mode toggle | Remove (always loop in FreeRTOS) |

#### 5.5 `src/components/BindGraph.vue` — New Visual Binding Editor

Visual drag-and-drop graph with three zones:

```
┌─────────────────────────────────────────────────────┐
│  LEFT (Source Pane)        │  RIGHT (Task Pane)     │
│                             │                        │
│  ┌─ Hardware Sources ──┐   │  ┌─ Tasks ───────────┐ │
│  │ 🟦 PC13 (BUTTON)    │   │  │ 📦 led_task    2  │ │
│  │ 🟦 PA0  (ADC_IN)    │──▶│  │ 📦 sensor_task 3  │ │
│  │ 🟩 SPI1 (spi_flash) │   │  │ 📦 mqtt_task   4  │ │
│  │ 🟩 USART1(max3232)  │   │  │ 📦 shell_task  1  │ │
│  │ 🟨 RTC (tick)       │   │  └──────────────────┘ │
│  └──────────────────────┘   │                        │
│                             │  Task→Task routes:     │
│                             │  sensor ──data_ready──▶ mqtt   │
└─────────────────────────────────────────────────────┘
```

| Feature | Implementation |
|---------|---------------|
| Hardware source nodes | Auto-generated from `hardwareModel.pins` (EXTI-enabled) + `hardwareModel.peripherals` + internal sources (RTC, SysTick) |
| Task nodes | From `taskModel.app_tasks` |
| Drag source → task | Creates `interrupt` or `peripheral_assign` entry in bindModel |
| Drag task → task | Creates `routing` entry in bindModel; popup to set signal name and optional condition |
| Connection labels | Show event name / role / signal name on edges |
| Click edge to edit | Edit signal name, condition expression, role |
| Delete edge | Click + Delete key, or context menu, removes bindModel entry |
| Validation indicators | Red outline if `event` name doesn't match `business_flow` events in task.yaml |

#### 5.6 Legacy YAML Import Handler

| Action | Detail |
|--------|--------|
| Detection | In `handleParse()`, check if `results.yaml` has `business_flow` or `app_tasks` top-level |
| Auto-split | If legacy detected, call a client-side `splitLegacy(yaml: string)` that extracts hardware/task/bind separately and feeds into three models |
| Warning banner | Show "Legacy monolithic YAML detected — auto-split into Hardware / Tasks / Bind tabs. Review Bind tab for interrupt and routing mapping." |
| Split logic | `app_tasks` → taskModel; `business_flow` → taskModel; `pins[].notify_task` → bindModel.interrupt; `app_tasks[].triggers` → bindModel.interrupt; `app_tasks[].signals` → bindModel.routing |

## 4. Backward Compatibility Strategy

### 4.1 Detection
If hardware.yaml contains `business_flow` or `app_tasks` at the top level → old format.

### 4.2 Auto-split (in mapper.py)
```python
def split_legacy(hw: dict) -> tuple[dict, dict, dict]:
    """Extract task.yaml and bind.yaml from old-format hardware.yaml."""
    task = {
        "project": {"name": hw.get("project_name", "untitled")},
        "app_tasks": _strip_task_triggers(hw.get("app_tasks", [])),
        "business_flow": hw.get("business_flow", {}),
    }
    hw_new = {k: v for k, v in hw.items() if k not in ("app_tasks", "business_flow")}
    bind = _extract_bind_from_legacy(hw)
    return hw_new, task, bind
```

### 4.3 Cleanup timeline
- v1.0: old format produces deprecation WARNING, continues to work
- v1.1: old format produces ERROR but still continues
- v1.2: old format removed

## 5. File Impact Summary

| Repo | New Files | Modified Files |
|------|-----------|---------------|
| **hw2c** | `docs/user-guide/task-yaml.md`, `docs/user-guide/bind-yaml.md`, `generator/schemas/task.py`, `generator/schemas/bind.py`, `generator/mapper.py`, `docs/plans/three-layer-split.md` | `docs/user-guide/hardware-yaml.md`, `mkdocs.yml`, `parser/pipeline.py`, `parser/cli.py`, `parser/netlist_parser.py`, `parser/netlist_parser_enet.py`, `generator/schemas/hardware.py`, `generator/generate.py`, `generator/context/builder.py`, `generator/validator.py` |
| **hw2c-web** | `frontend/src/components/BindGraph.vue`, `frontend/src/composables/useTaskModel.ts`, `frontend/src/composables/useBindModel.ts` | `backend/schemas.py` (split ParseResponse + new BindInfo/ProjectInfo models), `backend/routes/parse.py` (return split yaml strings), `backend/routes/generate.py` (accept three yamls), `frontend/src/api.ts` (new types + generate signature), `frontend/src/App.vue` (4-tab restructure + legacy import), `frontend/src/composables/useHardwareModel.ts` (strip app_tasks/business_flow), `frontend/src/components/TaskGraph.vue` (simplify to pure tasks) |

**Total: 6 new files + 17 modified files across 2 repos (23 files)**

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `bind.yaml` event names mismatch with `task.yaml` | Validator checks all `bind.yaml.interrupt[].event` and `routing[].signal` against `business_flow` events; frontend provides auto-complete dropdown |
| Generator template context API too coupled to single-dict shape | `mapper.py` produces the identical dict shape that `build_context()` expects; only the input side changes |
| Frontend regressions during Tab restructure | Phase 5 last, after all backend layers stable; keep old Tab as fallback during development |
| User confusion with three files | hw2c-web provides guided step-by-step workflow (upload → hardware → tasks → bind → generate)；CLI help text explains the 3-file model |
