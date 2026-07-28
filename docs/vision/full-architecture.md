# 🏗️ Hardware2Code 完全体架构设计

Hardware2Code 的目标不仅是“生成代码”，而是构建一个**硬件感知的嵌入式工程全生命周期管理平台**。下图描绘了 V2.0 完全体的宏观分层架构。

---

## 1. 总体分层架构

```mermaid
flowchart TB
    subgraph User_Layer [👤 用户交互层]
        CLI[🖥️ CLI 命令行工具]
        IDE[🧩 IDE 插件]
        WEB[🌐 Web 可视化配置台]
    end

    subgraph Input_Layer [📂 输入抽象层]
        YAML[📄 硬件描述 YAML]
        BOM[🔌 网表/BOM 导入器]
        SCH[📐 原理图解析器]
    end

    subgraph Core_Engine [⚙️ 核心生成引擎]
        direction TB
        Orch[🎼 编排器 Orchestrator]
        
        subgraph Domain [📊 领域模型层]
            MCU[MCU 目标模型]
            Pin[引脚/外设复用模型]
            Periph[外设抽象模型]
        end

        subgraph Builders [🏭 构建器农场]
            PinB[引脚分配器]
            ClockB[时钟树计算器]
            PeriphB[外设初始化构建器]
        end

        subgraph Advanced [🧠 智能核心]
            Calc[数学/约束引擎]
            Merger[🤖 AST 智能合并器]
            Atomic[💾 原子写入器]
        end
    end

    subgraph Output_Layer [📤 多后端输出层]
        STM32[STM32 HAL]
        NXP[NXP MCUXpresso]
        ESP[ESP-IDF]
        Zephyr[Zephyr RTOS]
    end

    User_Layer --> Input_Layer --> Core_Engine --> Output_Layer
    Advanced -.->|增强| Core_Engine