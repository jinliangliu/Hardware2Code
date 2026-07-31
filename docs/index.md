# 🚀 hw2c

**从 YAML 硬件描述与业务 DSL 出发，自动生成 STM32 + FreeRTOS 低功耗固件工程。**

[![GitHub](https://img.shields.io/badge/GitHub-jinliangliu/hw2c-blue)](https://github.com/jinliangliu/hw2c)
[![License](https://img.shields.io/badge/License-MIT-green)](https://github.com/jinliangliu/hw2c/blob/main/LICENSE)

---

## 为什么需要 hw2c？

在嵌入式项目快速交付中，**引脚配置、外设驱动移植、RTOS 框架搭建、低功耗管理、测试工程** 这些重复劳动占据了大量时间[reference:8]。

`hw2c` 的目标是：

- ✅ 接收 **硬件描述（YAML）** 和 **结构化业务流程（DSL）**
- ✅ 输出 **完整、可编译、带单元测试** 的工程
- ✅ 自动注入 **FreeRTOS + Tickless 低功耗管理** 策略
- ✅ 强制实施 **分层架构与 TDD**

---

## 核心特性

| 特性 | 说明 |
| :--- | :--- |
| **硬件驱动自动生成** | GPIO、I2C、SPI、ADC、PWM、RTC[reference:9] |
| **业务逻辑 DSL** | 层级状态机、并行区域、历史状态、defer/timeline[reference:10] |
| **内置低功耗** | Tickless Idle、STOP/SLEEP/STANDBY[reference:11] |
| **TDD 就绪** | Unity 测试框架 + Mock HAL[reference:12] |
| **双槽位 Bootloader** | CRC32 校验、TAMP 备份、自动回退[reference:13] |

---

## 快速开始

```bash
# 1. 克隆仓库
git clone --recurse-submodules https://github.com/jinliangliu/hw2c.git
cd hw2c

# 2. 安装依赖
pip install -r requirements.txt

# 3. 生成工程
hw2c gen -i examples/base/hardware.yaml -o output/base --force \
  --task examples/base/task.yaml \
  --components examples/base/components.yaml \
  --bind examples/base/bind.yaml \
  --params examples/base/params.yaml \
  --pubsub examples/base/pubsub.yaml

# 4. 编译
cd output/base
cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
cmake --build build
