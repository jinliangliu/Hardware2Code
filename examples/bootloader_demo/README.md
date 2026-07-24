# bootloader_demo — 双槽位 Bootloader + 异常恢复

演示双 Bank Bootloader 固件完整性校验与故障自动切换。

## 硬件

- **PC0**: LED（低电平点亮）— Bootloader 和 App 共用
- **PC13**: 按键（上拉，下降沿触发 EXTI）
- **RTC**: LSI 时钟，100ms RTC_TICK

## Flash 布局

```
Bank1 (256KB)                   Bank2 (256KB)
┌────────────────┐ 0x08000000   ┌────────────────┐ 0x08040000
│ Bootloader 8KB │              │ App Slot B     │
├────────────────┤ 0x08002000   │ (OTA 更新槽位)  │
│ App Slot A     │              │ 256KB          │
│ 当前运行固件    │              │                │
│ 248KB          │              │                │
└────────────────┘ 0x08040000   └────────────────┘ 0x08080000
```

## Bootloader 启动流程

```
上电 → 读 TAMP 标志 → 检查上次启动状态
  ├─ boot_ok 已写入 → 计数归零 → CRC 校验 → 跳转 App
  ├─ boot_ok 未写入 → 计数 +1 → CRC 校验 → 跳转 App
  └─ 计数 > 3       → 切换槽位 → 软复位
```

## App 行为

1. **上电** → LED 灭（IDLE 状态）
2. **按 PC13** → 进入 PLAYING → LED 亮（`on_entry: toggle_led`）
3. **5 秒无操作** → `after: 5000` 超时 → 回到 IDLE → LED 灭（`toggle_led`）

## 板上观察

### 正常启动

| 阶段 | LED | 说明 |
|------|-----|------|
| 上电 | 灭 | Bootloader 通过 CRC 校验，跳转 App → IDLE |
| 按 PC13 | 亮 | 进入 PLAYING，`toggle_led` |
| 5s 后 | 灭 | 超时返回 IDLE，`toggle_led` |

### 异常恢复测试

| 操作 | 预期现象 |
|------|---------|
| 烧录仅 bootsloader（App Slot A 为空） | LED SOS 闪烁（3短3长3短），CRC 校验失败 |
| 烧录 bootloader + 正常 App | 正常亮灭（见上表） |
| App Slot A 写入损坏固件 | 计数累积 3 次后自动回退 Slot B |
| 两个 Slot 均损坏 | LED 永久 SOS 闪烁 = Recovery 模式 |

## 编译与烧录

```bash
# 1. 生成工程
python generator/generate.py -i examples/bootloader_demo/hardware.yaml -o output/bootloader_demo

# 2. 编译 Bootloader + App，合并为单镜像
cd output/bootloader_demo
make bootloader    # 编译 Bootloader → bootloader/build/bootloader.bin
make app           # 编译 App → build/bootloader_demo.bin
make combined      # 合并 → build/combined.bin

# 3. 烧录合并镜像到主板
make flash-daplink

# 4. 仅更新 App（OTA 场景）
make flash-daplink-app
```

## 测试特性

| 特性 | 说明 |
|------|------|
| 双槽位 | Bank1=当前固件, Bank2=OTA 备用 |
| CRC32 硬件校验 | 每次启动前校验固件完整性 |
| 启动计数 | TAMP 备份寄存器跨复位持久化 |
| 自动回退 | 连续 3 次启动失败 → 切换到备用槽位 |
| Recovery 模式 | 双槽位均损坏 → LED SOS 信号 |

## 生成

```bash
python generator/generate.py -i examples/bootloader_demo/hardware.yaml -o output/bootloader_demo
```
