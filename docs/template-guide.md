# Hardware2Code 模板开发指南

## 概述
Hardware2Code 使用 **Jinja2** 模板引擎，根据硬件描述文件（`hardware.yaml`）生成完整的嵌入式 C 工程。模板位于 `templates/` 目录下，由 Python 生成器渲染后输出到目标目录。

## 目录结构
templates/
├── macros.j2 # 可复用的 Jinja2 宏（如 EXTI 映射）
├── src/
│ ├── main.c.j2
│ ├── gpio.c.j2
│ ├── sleep.c.j2
│ └── stm32g0xx_it.c.j2
├── config/
│ ├── FreeRTOSConfig.h.j2
│ └── stm32g0xx_hal_conf.h.j2
├── linker/
│ └── STM32G0B1RETx_FLASH.ld.j2
└── project/
└── Makefile.j2


## 模板渲染上下文
生成器会将 `hardware.yaml` 解析后的数据加上一些额外处理，组合成一个 **上下文字典** 传递给每个模板。所有模板共享同一上下文，但各自只使用需要的变量。

### 常用上下文变量
| 变量名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `mcu` | object | MCU 信息，包含 `part`, `core_clock_mhz`, `hse_freq` | `{"part": "STM32G0B1RET6", "core_clock_mhz": 64}` |
| `pins` | list[object] | 引脚列表，每个引脚包含 `id`, `function`, `label`, `pull`, `exti`, `notify_task` 等 | `[{"id": "PC13", "label": "BUTTON", "exti": {"enable": true, "trigger": "falling"}, "notify_task": "button_led_task"}]` |
| `app_tasks` | list[object] | 应用任务列表，每个任务有 `name`, `priority`, `stack_size` | `[{"name": "button_led_task", "priority": 2, "stack_size": 128}]` |
| `sleep` | object | 低功耗配置，含 `mode`（如 `"STOP1"`） | `{"mode": "STOP1"}` |
| `project_name` | string | 工程名称，默认 `hw2code` | `"blinky_g0"` |
| `heap_size` / `stack_size` | string | 链接脚本中的堆/栈大小（十六进制字符串） | `"0x200"` |

## 模板详细说明

### `macros.j2`
- **作用**：提供可重用的宏函数，避免在各个模板中重复编写逻辑。
- **当前宏**：
  - `exti_irq_name(pin_id)` → 返回 NVIC 中断号名称（如 `EXTI4_15_IRQn`）
  - `exti_handler_name(pin_id)` → 返回中断处理函数名（如 `EXTI4_15_IRQHandler`）
- **使用方式**：在其他模板顶部添加 `{% import 'macros.j2' as macros %}`，然后通过 `macros.exti_irq_name(...)` 调用。

### `main.c.j2`
- **生成文件**：`src/main.c`
- **职责**：
  - 根据 `pins` 中 `label == 'LED'` 的引脚自动生成 `LED_GPIO_Port` 和 `LED_GPIO_Pin` 宏。
  - 提供默认的 `SystemClock_Config()` 函数（HSI 16MHz）。
  - 创建 `app_tasks` 中定义的所有 FreeRTOS 任务。
  - 内置一个 `button_led_task` 示例任务，等待任务通知后翻转 LED。

### `gpio.c.j2`
- **生成文件**：`src/gpio.c`
- **职责**：遍历所有引脚，生成对应的 GPIO 初始化代码，并使能 EXTI 中断线（如果需要）。
- **依赖**：`macros.j2` 中的 `exti_irq_name` 宏。

### `sleep.c.j2`
- **生成文件**：`src/sleep.c`
- **职责**：提供 `vApplicationIdleHook()` 实现，当前直接使用 `__WFI()` 进入休眠。

### `stm32g0xx_it.c.j2`
- **生成文件**：`src/stm32g0xx_it.c`
- **职责**：
  - 为配置了 EXTI 的引脚生成对应的中断处理函数。
  - 如果引脚定义了 `notify_task`，则在中断中通过 `xTaskNotifyFromISR` 发送通知给指定任务。
  - 避免覆盖 FreeRTOS 所需的 `SysTick_Handler`、`PendSV_Handler` 等。
- **依赖**：`macros.j2` 中的 `exti_handler_name` 宏。

### `FreeRTOSConfig.h.j2`
- **生成文件**：`config/FreeRTOSConfig.h`
- **职责**：提供与 MCU 频率匹配的 FreeRTOS 内核配置，包含 Cortex-M0+ 必须的 `configENABLE_MPU 0`，并禁用 Tickless 模式。

### `stm32g0xx_hal_conf.h.j2`
- **生成文件**：`config/stm32g0xx_hal_conf.h`
- **职责**：基于官方 HAL 配置模板，开启所有外设模块，并将 `USE_RTOS` 设为 0，避免与 FreeRTOS 冲突。

### `STM32G0B1RETx_FLASH.ld.j2`
- **生成文件**：`linker/STM32G0B1RETx_FLASH.ld`
- **职责**：官方 STM32CubeIDE 链接脚本模板，可动态调整堆栈大小。

### `Makefile.j2`
- **生成文件**：`Makefile`
- **职责**：
  - 组织所有源文件（HAL、CMSIS、FreeRTOS-Kernel、用户代码）的编译。
  - 提供 `flash`（ST-Link）和 `flash-daplink`（OpenOCD）烧录目标。
  - 通过 `HARDWARE2CODE_STATIC` 变量指向静态库目录。

## 如何添加新的模板
1. 在 `templates/` 下相应子目录创建 `.j2` 文件。
2. 在文件顶部添加 Jinja2 注释，说明生成的输出文件、所需上下文变量及用途。
3. 在 `generator/generate.py` 的 `render_templates()` 函数中添加该模板的渲染逻辑（映射到输出路径）。
4. 如果新模板引用了新的上下文变量，需在 `context_builder.py` 中提供这些变量。

## 变量扩展与宏
- 所有复杂的计算或条件判断应尽量封装在 `macros.j2` 或生成器的 `context_builder` 中，保持模板简洁。
- 当模板中的逻辑变得复杂时，优先考虑将部分逻辑移到 Python 预处理阶段（例如构建 `handlers` 字典），而不是在模板中写过多 Jinja2 代码。

## 调试技巧
- 可以在生成器 `generate.py` 中打印 `context` 变量，查看实际传入模板的数据结构。
- 使用 `template.render(context)` 的异常信息定位 Jinja2 语法错误。
- 编译生成的代码时，注意查看错误信息，多数情况下是模板未正确输出变量导致的宏/函数名错误。


1. 业务逻辑 DSL
简介：通过 business_flow 节点定义状态机，自动生成 statemachine.c/h。

语法示例（引用 rtc_adv 的 YAML）：

yaml
business_flow:
  initial_state: "IDLE"
  states:
    - name: "IDLE"
      transitions:
        - event: "BUTTON_PRESS"
          target: "ACTIVE"
          actions:
            - "toggle_led"
    - name: "ACTIVE"
      transitions:
        - event: "RTC_TICK"
          target: "IDLE"
可用事件：EVENT_BUTTON_PRESS, EVENT_RTC_TICK, EVENT_MPU6050_ALERT 等（参见 event_mgr.h）。

内置动作：toggle_led（通过 led_task_notify 通知 LED 任务）。

2. 测试框架扩展
如何为新外设编写测试：参照 test_gpio.c.j2 的模式，使用 mock_hal 验证 HAL 调用。

状态机测试：test_statemachine.c 验证状态转换和动作执行。

RTC 定时器集成测试：test_rtc_timers.c 验证多定时器并发和周期触发。

