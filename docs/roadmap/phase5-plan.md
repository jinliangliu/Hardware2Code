# Phase 5 Plan: 可视化交互层

> 状态：制定中 | 仓库：hw2c-web（独立） | 依赖：hw2c >= 0.4.0

## 目标

将 hw2c 从"程序员手写 YAML"升级为"硬件工程师拖拽配置"。用户上传网表/BOM 后，在硬件能力约束内可视化完成：外设参数配置、任务分配、状态机编排，最终一键生成嵌入式工程。

## 现状

| 组件 | 状态 |
|------|------|
| `hw2c parse` (CLI) | 100% |
| `hw2c gen` (CLI) | 100% |
| hw2c-web 后端 `/api/parse` | 100% |
| hw2c-web 后端 `/api/generate` | 未实现 |
| hw2c-web 前端 上传 + 预览 | 骨架完成 |
| hw2c-web 前端 YAML 编辑器 | 未实现 |
| hw2c-web 前端 外设配置面板 | 未实现 |
| hw2c-web 前端 状态机画布 | 未实现 |

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3, Port 5173)                    │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ 硬件资源面板  │  │  配置编辑器   │  │   实时 YAML + 预览       │ │
│  │ (左侧, 300px)│  │  (中央, flex) │  │   (右侧, 400px)          │ │
│  │              │  │               │  │                          │ │
│  │ 引脚树        │  │ 外设参数表单   │  │  CodeMirror YAML 编辑器  │ │
│  │ 外设列表      │  │ 状态机画布     │  │  语法高亮 / 自动补全     │ │
│  │ 无源元件表    │  │ Timeline 时间轴│  │  Diff 高亮              │ │
│  │ 总线分配      │  │ 任务分配面板   │  │  "生成工程" 按钮         │ │
│  │ 冲突警告      │  │               │  │  下载 .zip               │ │
│  └─────────────┘  └──────────────┘  └──────────────────────────┘ │
│                                                                   │
└──────────────────────┬────────────────────────────────────────────┘
                       │  YAML (单一真相源)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端 (FastAPI, Port 8000)                   │
│                                                                   │
│  POST /api/parse       上传 netlist + BOM → ParsedHardware        │
│  POST /api/generate    提交 hardware.yaml → 编译 zip 下载         │
│  GET  /api/mcu/{part}  获取 MCU 引脚/外设数据库                    │
│  POST /api/validate    实时校验 YAML 片段                          │
│                                                                   │
└──────────────────────┬────────────────────────────────────────────┘
                       │  Python API
                       ▼
               hw2c (parser + generator)
```

## 子阶段拆分

### 5.1 YAML 编辑器 + 双向绑定（优先）

**目标**：前端以 YAML 为单一真相源，UI 操作与 YAML 实时双向同步。

**技术选型**：CodeMirror 6（轻量、Vue 3 友好、YAML 语法高亮开箱即用）

**文件清单**：

```
hw2c-web/frontend/src/
├── composables/
│   └── useHardwareModel.ts    # YAML ↔ 响应式状态双向同步
├── components/
│   └── YamlEditor.vue         # CodeMirror 封装（语法高亮、错误提示）
```

**useHardwareModel.ts 核心逻辑**：

```
1. 从 API 获取 ParsedHardware，提取初始 YAML
2. 建立 reactive 对象 { mcu, pins, peripherals, app_tasks, behavior }
3. 监听 reactive 变更 → js-yaml dump → 更新 CodeMirror
4. 监听 CodeMirror 变更 → js-yaml load → 更新 reactive
5. 提供 writeMcu(part), writePin(id, field, val), addPeripheral(), removeTask() 等 mutations
```

**验收**：修改 YAML 文本 → UI 面板自动刷新；修改 UI 面板参数 → YAML 文本自动更新。

---

### 5.2 外设配置面板

**目标**：对每种外设类型提供约束化的参数表单。

**文件清单**：

```
hw2c-web/frontend/src/
├── components/
│   ├── PeripheralConfig.vue       # 外设总面板（PeripheralList 升级版）
│   ├── configs/
│   │   ├── I2CConfig.vue          # I2C 地址、速率、从机应答
│   │   ├── SPIConfig.vue          # SPI 模式(0-3)、速率、NSS 策略
│   │   ├── UARTConfig.vue         # 波特率、数据位、校验位、停止位
│   │   ├── GPIOConfig.vue         # 方向、上拉/下拉、有效电平、EXTI
│   │   ├── ADCConfig.vue          # 通道、采样时间、分辨率
│   │   ├── PWMConfig.vue          # 通道、频率、占空比
│   │   ├── RTCConfig.vue          # 时钟源、闹钟、日历
│   │   └── SleepConfig.vue        # 低功耗模式(STOP/STANDBY)
```

**每种配置项来源**：
- **约束范围**来自 MCU 数据库（如 UART 最大波特率 = 6Mbps for STM32G0）
- **当前值**来自硬件能力映射（网表已连接的引脚）
- **可选值**以 Select/Dropdown 呈现，非法值红色警示

**验收**：点击任意外设 → 右侧展开参数表单 → 修改参数 → YAML 实时更新。

---

### 5.3 引脚分配可视化

**目标**：将 `pins` 数组从表格升级为可交互的资源看板。

**文件清单**：

```
hw2c-web/frontend/src/
├── components/
│   ├── PinAllocator.vue          # 引脚分配主面板（替代 PinTable）
│   ├── BusColorMap.ts            # 总线颜色映射
│   └── PinChip.vue               # 单个引脚芯片图（LQFP 封装预览）
```

**交互**：
- 表格左侧显示所有引脚及当前分配
- 颜色编码按总线类型（I2C=蓝, SPI=绿, UART=橙, 空闲=灰）
- 点击引脚弹出可选的 function/AF 下拉
- 已占用的 function 灰显（冲突检测）
- 预留引脚标注（SWD: PA13/PA14 固定灰色）

**验收**：修改引脚分配 → 拓扑图实时更新 → YAML 实时更新。

---

### 5.4 状态机可视化编辑器（高难度）

**目标**：Canvas 拖拽式状态机设计，生成 `behavior` YAML。

**技术选型**：Vue Flow (@vue-flow/core) — MIT 开源，Vue 3 原生支持，节点/边拖拽

**文件清单**：

```
hw2c-web/frontend/src/
├── components/
│   ├── StateMachineEditor.vue    # Vue Flow 封装
│   ├── nodes/
│   │   ├── StateNode.vue         # 状态节点（普通/初始/终态）
│   │   └── ChoiceNode.vue        # 条件分支节点（CHOICE）
│   ├── edges/
│   │   └── TransitionEdge.vue    # 转移边（事件/条件/动作）
│   └── panels/
│       ├── StatePropsPanel.vue   # 选中状态 → 右侧属性面板
│       └── EdgePropsPanel.vue    # 选中转移边 → 事件/动作编辑
```

**YAML 映射**：

```yaml
behavior:
  initial_state: "IDLE"
  states:
    - name: "IDLE"               # StateNode
      on_entry: []               # StatePropsPanel 输入
      transitions:
        - event: "BTN_PRESS"     # TransitionEdge 上的 label
          target: "ACTIVE"       # 边的目标节点
          actions: ["toggle_led"]  # EdgePropsPanel 输入
```

**验收**：拖拽创建节点和边 → 画布自动布局 → 右侧属性面板编辑 → YAML 实时生成 `behavior` 节。

---

### 5.5 任务分配面板

**目标**：可视化 FreeRTOS 任务配置。

**文件清单**：

```
hw2c-web/frontend/src/
├── components/
│   ├── TaskAllocator.vue        # 任务列表 + 新建/编辑
│   └── TaskItem.vue             # 单任务：名称、优先级、栈大小
```

**映射**：
- 每个 `peripherals` 自动生成一个对应 task（可在任务面板中编辑/删除）
- `app_tasks` 数组直接双向绑定到 TaskAllocator
- 栈大小 slider（128-4096），优先级 slider（1-5）

**验收**：添加/删除/编辑任务 → YAML `app_tasks` 实时更新。

---

### 5.6 生成 + 下载

**目标**：一键生成工程并下载 .zip。

**后端新增**：

```python
# hw2c-web/backend/routes/generate.py
POST /api/generate
Body: { "yaml": "<hardware.yaml 内容>" }
Response: application/zip download
```

**流程**：
1. 前端提交当前 YAML
2. 后端写入临时 `hardware.yaml`
3. 调用 `hw2c gen -i tmp/hardware.yaml -o tmp/output`
4. 在 `tmp/output/` 目录执行 `make` 编译
5. 将整个 output 目录打包为 .zip
6. 返回下载链接，清理临时文件

**验收**：点击"生成工程" → 下载 `project.zip` → 解压后 `make flash` 直接烧录运行。

---

### 5.7 交付物打磨

| 项 | 说明 |
|---|---|
| Error boundary | API 调用失败/解析异常 → 友好提示，不白屏 |
| Loading state | 上传解析 > 2s 显示进度动画 |
| Empty state | 初始欢迎页 + 格式说明 |
| 键盘快捷键 | `Ctrl+S` 下载 YAML，`Ctrl+G` 生成工程 |
| 响应式适配 | 小屏折叠为单列，移动端可看（不要求可操作） |

---

## 实施顺序

```
Step 1: 5.1 YAML 编辑器 + 双向绑定        ← 所有后续步骤的基础
Step 2: 5.2 外设配置面板                    ← 核心交互价值
Step 3: 5.6 生成 + 下载                     ← 闭环体验，立即可用
Step 4: 5.3 引脚分配可视化                  ← 进阶交互
Step 5: 5.5 任务分配面板                    ← 轻量，快速完成
Step 6: 5.4 状态机可视化编辑器              ← 最高难度，最后攻克
Step 7: 5.7 交付物打磨                      ← 收尾
```

---

## 不做的事情（明确边界）

| 不做的 | 原因 |
|--------|------|
| 手绘原理图导入 | EasyEDA Pro 已有 .enet 导出 |
| 在线编译（远程服务器） | 安全风险高，本地 make 更可控 |
| 多用户协作 | 本地单机工具，不需要 |
| 浏览器内 C 代码编辑器 | 专业的事交给 VS Code |
| 拖拽 PCB 布局 | 超出 hw2c 范围 |
