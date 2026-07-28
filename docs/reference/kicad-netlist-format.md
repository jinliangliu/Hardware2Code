# KiCad 网表格式规范
> 来源: [KiCad Documentation](https://docs.kicad.org/)
> 对应解析器: `parser/netlist_parser.py`

## 概述

KiCad 支持两种网表导出格式：
1. **XML 格式** (传统) — `<export version="D">`
2. **S-Expression 格式** (KiCad 6+) — `(kicad_netlist ...)`

hw2c 自动检测格式并解析。

---

## 1. XML 格式 (Legacy)

### 结构

```xml
<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <design>
    <source>hardware.sch</source>
    <date>29/08/2010 20:35:21</date>
    <tool>eeschema (7.0.0)</tool>
  </design>
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
      <footprint>LQFP-64</footprint>
      <libsource lib="mcu_st" part="STM32G0B1RET6"/>
      <tstamp>4C6E2141</tstamp>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PB6)">
      <node ref="U1" pin="PB6"/>
      <node ref="U2" pin="SCL"/>
    </net>
  </nets>
</export>
```

### 核心元素

| 元素 | 属性 | 说明 |
|------|------|------|
| `<export version="D">` | — | 根元素，版本固定为 "D" |
| `<design>` | — | 设计元信息（可选） |
| `<design>/<source>` | — | 原理图源文件路径 |
| `<design>/<date>` | — | 导出日期 |
| `<design>/<tool>` | — | 工具名称和版本 |
| `<components>/<comp>` | `ref` | 元器件引用名（位号） |
| `<comp>/<value>` | — | 元器件值 |
| `<comp>/<footprint>` | — | 封装名 |
| `<comp>/<libsource>` | `lib, part` | 库来源 |
| `<nets>/<net>` | `code, name` | 网络：编号，名称 |
| `<net>/<node>` | `ref, pin` | 引脚连接：元器件引用，引脚号 |

---

## 2. S-Expression 格式 (KiCad 6+)

### 语法基础

- Token 由 `(` `)` 分隔
- 关键字全小写
- 字符串用双引号 `"..."` 包裹，UTF-8 编码
- 网络名称通常定义为 `Net-(<ref>-<pin>)` 或用户自定义名

### 结构

```lisp
(kicad_netlist
  (version 20240108)
  (components
    (comp (ref "U1")
          (value "STM32G0B1RET6")
          (footprint "LQFP-64"))
    (comp (ref "U2")
          (value "MPU6050")
          (footprint "QFN-24"))
  )
  (nets
    (net (code 1) (name "I2C1_SCL")
      (node (ref "U1") (pin "PB6"))
      (node (ref "U2") (pin "SCL"))
    )
    (net (code 2) (name "I2C1_SDA")
      (node (ref "U1") (pin "PB7"))
      (node (ref "U2") (pin "SDA"))
    )
  )
)
```

### 顶层 Token

| Token | 说明 |
|-------|------|
| `(version ...)` | 格式版本，如 `20240108` |
| `(components ...)` | 元器件列表 |
| `(nets ...)` | 网络连接列表 |

### 元器件: `(comp ...)`

| 子 Token | 说明 |
|----------|------|
| `(ref "...")` | 位号 (Designator)，如 `"U1"`, `"R2"`, `"C3"` |
| `(value "...")` | 元器件值，如 `"STM32G0B1RET6"`, `"10K"` |
| `(footprint "...")` | 封装名，如 `"LQFP-64"`, `"SOIC-8"` |

### 网络: `(net ...)`

| 子 Token | 说明 |
|----------|------|
| `(code N)` | 网络编号 (整数) |
| `(name "...")` | 网络名称 |
| `(node ...)` | 引脚节点 |

### 节点: `(node ...)`

| 子 Token | 说明 |
|----------|------|
| `(ref "...")` | 元器件引用名 |
| `(pin "...")` | 引脚编号 (如 `"PB6"`, `"SCL"`, `"1"`) |

---

## 3. 格式检测

hw2c 按以下优先级检测格式：

```python
def _detect_format(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        return "enet"           # EasyEDA Pro JSON
    if stripped.startswith("<?"):
        return "xml"            # KiCad XML
    if stripped.startswith("(kicad_netlist"):
        return "sexpr"          # KiCad S-Expression
    return "sexpr"              # fallback
```

---

## 4. hw2c 解析策略

| .net 字段 | hw2c 映射 |
|-----------|-----------|
| `<comp ref>` / `(ref)` | 元器件引用名（作为字典 key） |
| `<value>` / `(value)` | 用于 MCU 检测 (`STM32*`) 和外设类型匹配 |
| `<footprint>` / `(footprint)` | 封装名 |
| `<net name>` / `(name)` | 网络名 |
| `<node ref>` / `(node ref)` | 元器件引用 |
| `<node pin>` / `(node pin)` | 引脚号，用于 `_pin_to_bus_info()` 查找 |

### XML vs S-Expr 关键差异

| 特性 | XML | S-Expression |
|------|-----|--------------|
| 根元素 | `<export version="D">` | `(kicad_netlist (version ...))` |
| 设计头 | `<design>` 独立元素 | 无显式设计头 |
| 网络名 | `<net name="...">` | `(net (name "..."))` |
| 字符串 | XML 文本节点 | 双引号原子 |
| 编码 | XML declaration | UTF-8 隐式 |
