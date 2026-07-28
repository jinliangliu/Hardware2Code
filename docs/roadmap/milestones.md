# Roadmap

## 来时路

hw2c 从"根据 YAML 生成 GPIO 翻转代码"的原型起步，经历了四个阶段的演进，逐步构建起**硬件设计→嵌入式工程**的全链路能力：

### 阶段零：原型验证（2024 底 — 2025 初）

从零搭建了整套骨架 —— 这阶段产出的不是功能，是地基。

- [x] Python + Jinja2 代码生成引擎，YAML → C 工程的原型跑通
- [x] STM32G0B1 + FreeRTOS + arm-none-eabi-gcc 工具链集成
- [x] `static/` 子模块引入 HAL/CMSIS/FreeRTOS & Unity 测试框架
- [x] VSCode Cortex-Debug 调试配置自动生成
- [x] GitHub Actions CI（自动编译 + 单元测试 + 覆盖率）

### 阶段一：稳定性与真实性（2025 上半年）

原型能跑但不够可靠。这一阶段集中修复了影响真实硬件运行的关键缺陷。

- [x] 日志子系统：USART2 中断驱动环形缓冲，6 级过滤，ISR 安全
- [x] Bootloader 稳定性：修复 CRC32 配置、TAMP DBP 同步、SP 地址校验
- [x] 电源与时钟：SYSCFG 时钟使能、Tickless Idle RTC 时钟源修复
- [x] 10 个 demo 编译错误系统性修复，引入 Pydantic 类型模型重构校验层
- [x] HAL timebase 无条件可用 + `log_flush()` ISR 竞态修复
- [x] 模板完善：IWDG 驱动、62 个模板的文档化（template-guide）

### 阶段二：外设与协议扩展（2025 中）

从单点外设走向多协议通信栈，覆盖工业物联网典型场景。

- [x] 基础外设全覆盖：GPIO / EXTI / I2C(MPU6050) / SPI(W25Q32) / ADC / PWM / RTC
- [x] 通信协议栈：UART / RS485 / Modbus RTU / MQTT 3.1.1
- [x] 蜂窝网络：Cellular 4G Cat.1 模组驱动（AT 指令 + PDP 拨号）
- [x] 红外通信：NEC / SIR 协议收发
- [x] 存储扩展：I2C EEPROM 驱动
- [x] CLI 调试终端：UART 命令行交互，支持 gpio/rtc/led/modbus/cellular/mqtt/fota
- [x] 21 个示例项目，覆盖从点灯到 4G 上云的全场景

### 阶段三：状态机引擎与安全升级（2025 中后）

从"生成外设驱动"升级到"生成业务逻辑"，DSL 能力大幅扩展。

- [x] DSM 引擎：复合子状态 / 并行区域 / 历史状态
- [x] 高级动作：defer / timeline / when 条件 / ref 引用 + namespace
- [x] 跨区域通信：`send_to` + `publish_async` 并行区域间事件传递
- [x] 双槽位 Bootloader：硬件 CRC32 + TAMP 备份寄存器 + 自动回退
- [x] BSDIFF FOTA：差分固件升级，减小 OTA 传输体积，含校验与回滚
- [x] 完整测试体系：Bootloader CRC(4) + NVM(12) + Jump(8) 单元测试
- [x] CMSIS 寄存器级 Mock 基础设施（CRC/PWR/RCC/TAMP/SCB/NVIC/SysTick）

---

## Phase 4: Netlist/BOM 驱动（已完成 ✅）

将硬件设计文件直接作为输入源，打通 EDA → 嵌入式工程的第一跳。

- [x] **Netlist 解析增强**：支持 EasyEDA Pro .enet JSON（主要）、KiCad XML、KiCad S-Expression 三种网表格式自动检测
- [x] **BOM 解析增强**：100+ 种外设芯片启发式匹配，提取阻容/晶振/连接器/稳压器等无源元件约束
- [x] **引脚冲突自动检测与交叉校验**：Netlist vs YAML 四级检查（MCU 匹配→引脚冲突→引脚缺失/多余→外设类型匹配）
- [x] **原理图注解导入**：从网络命名约定提取总线分配（SPI/I2C/UART/CAN/SWD）、外设分组、电源域、信号角色
- [x] **统一管道**：`parser/pipeline.py` 一键整合 Netlist + BOM + Passive + Annotator + Validator，输出带注解的 enriched YAML
- [x] **116 个单元/集成测试全部通过**

## Phase 5: 可视化配置台

从手写 YAML 到可视化编排，降低使用门槛。

- [ ] Web-based visual YAML editor（基于 Netlist/BOM 解析结果的硬件能力约束）
- [ ] 任务编排画布：拖拽式状态机设计 + timeline 时间轴
- [ ] 外设参数面板：I2C 地址、SPI 模式、UART 波特率等约束化输入
- [ ] 实时 YAML 预览与 diff：可视化操作实时反映到 YAML，支持手动切换编辑

## Phase 6: 质量与合规

向 MISRA C 合规和工业级代码质量对齐。

- [ ] MISRA C:2012 规则扫描集成（生成代码自动通过 Mandatory 规则）
- [ ] MISRA C 违规自动修复引擎（模板层面修复，不依赖后处理）
- [ ] 代码复杂度控制（单函数 ≤ 100 行，圈复杂度 ≤ 10）
- [ ] 静态分析集成（Cppcheck / Clang Static Analyzer）
- [ ] Docker 编译环境镜像（固化工具链版本，消除"在我机器上能跑"问题）

## Phase 7: 多平台与生态

从单点 MCU 到多平台支持，从生成器到开发平台。

- [ ] 多 MCU 系列支持：STM32F4 / STM32H7（Cortex-M4/M7）
- [ ] 多 RTOS 后端：Zephyr RTOS 模板适配（可选）
- [ ] 增量代码生成（只重新生成变更部分，保留用户手写代码）
- [ ] 插件市场：社区贡献的驱动模板、外设模型、状态机 action
- [ ] VSCode 扩展：IDE 内 YAML 补全、校验、预览、一键生成
- [ ] GitHub Actions 模板：CI 中自动生成 + 编译 + 测试的 workflow 模板

---

## 待办（未归类）

以下条目来自早期路线图，待归入对应 Phase 或评估优先级后去重。

- [ ] GPIO / ADC / UART HIL 测试
- [ ] Bootloader 集成端到端测试（编译 + 烧录 + 验证）
- [ ] DSL 变量类型扩展（struct / array）
- [ ] CHOICE 伪状态（条件分支节点）
- [ ] USB CDC 日志模板（PA11/PA12, AF10）
- [ ] DMA 支持（UART RX/TX）
- [ ] FDCAN 通信模板
- [ ] LPUART 低功耗串口模板
- [ ] 安全启动（固件签名验证）
- [ ] FOTA 完整集成测试 + 补丁制作工具链
