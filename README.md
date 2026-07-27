# Hardware2Code
**从 YAML 硬件描述与业务 DSL 出发，自动生成 STM32 + FreeRTOS 低功耗固件工程。**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 为什么需要 Hardware2Code？

在嵌入式项目快速交付中，**引脚配置、外设驱动移植、RTOS 框架搭建、低功耗管理、测试工程**这些重复劳动占据了大量时间。
Hardware2Code 的目标是：

- 接收 **硬件描述（YAML）** 和 **结构化业务流程（DSL）**。
- 输出 **完整、可编译、带单元测试** 的工程，基于 GCC Makefile 构建。
- 自动注入 **FreeRTOS + Tickless 低功耗管理** 策略。
- 强制实施 **分层架构与 TDD（测试驱动开发）**，让交付更可靠。

## 工作流概览

```
硬件描述(YAML) + 业务需求(DSL)
    │
    ▼
Hardware2Code 生成引擎
    │
    ▼
STM32 + FreeRTOS 工程 (TDD分层, 低功耗管理)
```

## 特性

- **硬件驱动自动生成**：根据外设模型库，从硬件描述自动实例化 GPIO、I2C、SPI、ADC、PWM、RTC 等驱动。
- **业务逻辑 DSL**：支持层级状态机（复合子状态、并行区域、历史状态）、跨区域通信、defer/timeline 时间控制、ref 引用复用。
- **内置低功耗**：自动分析唤醒源，插入 Tickless Idle 钩子与电源管理代码。
- **TDD 就绪**：生成基于 Unity 的模块测试框架与硬件 mock，支持脱离硬件运行。
- **双槽位 Bootloader**：固件 CRC32 校验、TAMP 备份寄存器持久化、自动故障回退。

## 当前功能

- **YAML 硬件描述**：定义 MCU、引脚（GPIO/EXTI）、低功耗模式、应用任务
- **业务 DSL**：状态机引擎（states/regions/substates/ref）、动作系统（set/calc/defer/timeline/publish/send_to）
- **代码生成**：Python + Jinja2 生成完整的 C 工程（HAL、FreeRTOS、启动文件、链接脚本）
- **Bootloader**：双槽位 (A/B) + 硬件 CRC32 校验 + 启动失败自动回退
- **日志子系统**：USART2 中断驱动环形缓冲日志，6 级过滤，ISR 安全（基于 rxi/log.c 设计）
- **编译工具链**：GCC Makefile，支持 ST-Link 和 DAP-Link 烧录
- **单元测试**：Unity 框架 + Mock HAL，PC 端运行，支持覆盖率报告
- **HIL 测试**：目标板硬件在环测试框架，串口输出结果
- **VSCode 集成**：自动生成 launch/tasks/settings/c_cpp_properties 调试配置
- **GitHub CI**：自动编译 + 单元测试 + 覆盖率
- **低功耗管理**：Idle Hook 自动进入 `__WFI()`，支持 STOP/SLEEP/STANDBY 模式
- **实际验证**：已在 STM32G0B1RET6 开发板上通过按键中断 + LED 翻转 + Bootloader 跳转测试

## 支持的外设

| 外设 | 驱动模板 | 单元测试 | HIL 测试 |
|------|----------|----------|----------|
| GPIO + EXTI | gpio.c.j2 | test_gpio.c.j2 | -- |
| USART (日志) | drv_log.c.j2 | -- | -- |
| I2C (MPU6050) | drv_i2c_mpu6050.c.j2 | test_mpu6050.c.j2 | -- |
| SPI (W25Q32) | drv_spi_flash.c.j2 | test_spi_flash.c.j2 | -- |
| ADC | drv_adc.c.j2 | test_adc.c.j2 | -- |
| PWM | drv_pwm.c.j2 | test_pwm.c.j2 | -- |
| RTC | drv_rtc.c.j2 | test_rtc.c.j2 / test_rtc_timers.c.j2 | hil_test.c.j2 |

## 快速开始

1. 克隆仓库（包含子模块）：
   ```bash
   git clone --recurse-submodules https://github.com/jinliangliu/Hardware2Code.git
   cd Hardware2Code
   ```

2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 生成工程：
   ```bash
   python generator/generate.py -i examples/blinky_g0/hardware.yaml -o output/blinky_g0
   cd output/blinky_g0
   make
   ```

4. 编译并烧录：
   ```bash
   make flash           # ST-Link 烧录
   make flash-daplink   # DAP-Link 烧录
   ```

5. 运行单元测试：
   ```bash
   python generator/run_tests.py --test-dir output/blinky_g0/test
   ```

## 目录结构

```
├── examples/              # 示例项目 (14 个)
│   ├── blinky_g0/         # GPIO + EXTI
│   ├── adc_uart/          # ADC + USART
│   ├── mpu6050/           # I2C 传感器
│   ├── spi_flash/         # SPI Flash
│   ├── pwm/               # PWM 输出
│   ├── rtc_advanced/      # RTC + 状态机全特性
│   ├── substate_demo/     # 复合子状态
│   ├── parallel_states/   # 并行区域
│   ├── parallel_comm/     # 并行区域跨区域通信
│   ├── nested_ref/        # ref 引用 + namespace
│   ├── ref_demo/          # ref 基础用法
│   ├── timeline_demo/     # timeline 时间序列
│   ├── bootloader_demo/   # 双槽位 Bootloader
│   └── common_subflow.yaml
├── output/                 # 生成工程输出
├── static/stm32g0/         # HAL/CMSIS/FreeRTOS（子模块）
│   ├── CMSIS/
│   ├── HAL/
│   └── FreeRTOS-Kernel/
├── templates/              # Jinja2 模板
│   ├── src/                # main.c, gpio.c, sleep.c, stm32g0xx_it.c
│   ├── app/                # statemachine.c/h
│   ├── drivers/            # drv_rtc, drv_log, drv_adc, drv_pwm...
│   ├── bootloader/         # boot_main, boot_nvm, boot_crc, boot_jump, boot_app
│   ├── linker/             # 链接脚本 (标准 + SlotA/B + Bootloader)
│   ├── project/            # Makefile (App + Bootloader)
│   ├── config/             # FreeRTOSConfig, HAL conf
│   ├── test/               # 单元测试 + Mock HAL
│   └── vscode/             # VSCode 调试配置
├── generator/              # Python 代码生成器
│   ├── generate.py
│   ├── context_builder.py
│   ├── validator.py
│   ├── patch_crc.py
│   ├── run_tests.py
│   └── hil_runner.py
├── models/                 # 外设模型库 (YAML)
├── docs/                   # 文档
│   ├── dsl-reference.md
│   └── template-guide.md
├── .github/workflows/      # CI workflow
├── ROADMAP.md              # 项目路线图
├── README.md
└── LICENSE
```
