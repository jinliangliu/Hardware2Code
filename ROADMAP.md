# Hardware2Code Roadmap

## Phase 1: 稳定性与真实性修复

- [x] USART2 日志子系统 (drv_log.c/h, 6 级, ISR 安全)
- [x] 修复 TAMP DBP 同步等待 Crash
- [x] 修复 SP 地址范围检查 (144KB SRAM)
- [x] 修复硬件 CRC32 REV_IN/REV_OUT 配置
- [x] CRC 元数据 magic 搜索定位机制
- [x] 日志调用集成到 main.c.j2 初始化流程
- [x] 修复 SYSCFG 时钟使能 (EXTI)
- [x] README 更新（移除虚假声明，补充实际功能）
- [x] 创建 ROADMAP.md
- [x] 修复并启用 substate 单元测试
- [x] IWDG 独立驱动模板 (drv_iwdg.c.j2 + drv_iwdg.h.j2, HAL_IWDG)
- [x] 更新 template-guide.md（完整重写，覆盖全部 62 个模板）

## Phase 2: 测试完善

- [x] Bootloader CRC 单元测试 (4 tests: null/size/magic validation)
- [x] Bootloader NVM 单元测试 (12 tests: init/reset/counter/slot/boot_ok)
- [x] Bootloader Jump 单元测试 (8 tests on 32-bit, placeholder on 64-bit)
- [x] CMSIS 寄存器 mock 基础设施 (CRC/PWR/RCC/TAMP/SCB/NVIC/SysTick)
- [ ] GPIO 按键 HIL 测试
- [ ] ADC 采样 HIL 测试
- [ ] UART 收发 HIL 测试
- [ ] Bootloader 集成端到端测试 (编译 + 烧录 + 验证)
- [ ] DSL 变量类型扩展（struct / array）

## Phase 3: 功能扩展

- [ ] CHOICE 伪状态（条件分支节点）
- [ ] USB CDC 日志模板 (PA11/PA12, AF10)
- [ ] DMA 支持 (UART RX/TX)
- [ ] FDCAN 通信模板
- [ ] LPUART 低功耗串口模板
- [ ] 安全启动（固件签名验证）
- [ ] OTA 固件升级协议
