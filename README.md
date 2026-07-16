# Hardware2Code
**从硬件设计原理图与项目业务需求出发，自动生成 TDD 分层的 STM32 + FreeRTOS 低功耗固件工程。**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/yourname/Hardware2Code)](https://github.com/yourname/Hardware2Code/stargazers)

## 为什么需要 Hardware2Code？

在嵌入式项目快速交付中，**引脚配置、外设驱动移植、RTOS 框架搭建、低功耗管理、测试工程**这些重复劳动占据了大量时间。  
Hardware2Code 的目标是：

- 接收 **硬件描述（YAML / 网表 / BOM）** 和 **结构化业务流程**。
- 输出 **完整、可编译、带单元测试** 的工程，支持 GCC / IAR / Keil 三种工具链。
- 自动注入 **FreeRTOS + Tickless 低功耗管理** 策略。
- 强制实施 **分层架构与 TDD（测试驱动开发）**，让交付更可靠。

## 工作流概览
硬件设计图(YAML/Netlist) + 业务需求(DSL)
│
▼
Hardware2Code 生成引擎
│
▼
STM32 + FreeRTOS 工程 (TDD分层, 低功耗管理)


## 特性

- **硬件驱动自动生成**：根据外设模型库，从硬件描述自动实例化 I2C、SPI、GPIO 等驱动。
- **业务任务骨架生成**：基于任务/状态机描述，生成 FreeRTOS 任务、队列、软件定时器。
- **内置低功耗**：自动分析唤醒源，插入 Tickless Idle 钩子与电源管理代码。
- **TDD 就绪**：生成基于 Unity 的模块测试框架与硬件 mock，支持脱离硬件运行。
- **多 IDE 支持**：同时输出 GCC Makefile、IAR (.eww)、Keil (.uvprojx) 工程。
- **保护用户代码**：通过 `/* USER CODE BEGIN */` 标记，重新生成时可保留手工修改。

TBD...
