# 嘉立创EDA专业版网表格式规范 (.enet)
> 来源: [easyeda/easyeda-pro-netlist-format](https://github.com/easyeda/easyeda-pro-netlist-format)
> 对应解析器: `parser/netlist_parser_enet.py`

## 概述
`.enet` 文件是嘉立创EDA专业版（EasyEDA Pro）原理图导出的网表文件格式，采用 JSON 结构，包含元器件信息、引脚网络连接、设计规则、差分对、网络类和等长组等完整的电路网表数据。

## 文件结构
```json
{
    "version": "2.0.0",
    "components": { ... },
    "designRule": { ... },
    "differentialPair": { ... },
    "netClass": { ... },
    "equalLengthNetGroup": { ... }
}
```

## 顶层字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 网表格式版本号，当前为 `"2.0.0"` |
| `components` | object | 元器件集合，键为元器件唯一ID |
| `designRule` | object | 设计规则，包含走线物理规则和网络规则 |
| `differentialPair` | object | 差分对定义 |
| `netClass` | object | 网络类定义 |
| `equalLengthNetGroup` | object | 等长网络组定义 |

---

## components（元器件）
`components` 是一个对象，键为元器件的唯一标识符（如 `"gge1"`、`"gge305"`），值为元器件对象。

### 元器件对象结构
```json
{
    "props": { ... },
    "pinInfoMap": { ... }
}
```

### props（元器件属性）
元器件属性为键值对形式，所有值均为字符串类型。以下为核心属性字段：

| 属性名 | 说明 | 示例 |
|--------|------|------|
| `Unique ID` | 元器件唯一标识符 | `"gge1"` |
| `Designator` | 位号 | `"R1"`、`"U2"`、`"C1"` |
| `Value` | 元器件值 | `"10K"`、`"10uF"` |
| `DeviceName` | 器件名称 | `"Res_0603"` |
| `FootprintName` | 封装名称 | `"R0603"` |
| `Add into BOM` | 是否加入BOM | `"yes"` / `"no"` |
| `Convert to PCB` | 是否转换到PCB | `"yes"` / `"no"` |
| `Description` | 元器件描述 | |

#### 供应商相关属性
| 属性名 | 说明 | 示例 |
|--------|------|------|
| `Supplier` | 供应商名称 | `"LCSC"` |
| `Supplier Part` | 供应商料号 | `"C307423"` |
| `Manufacturer` | 制造商名称 | `"SAMSUNG"` |
| `Manufacturer Part` | 制造商料号 | `"CL05A475MQ5NRNC"` |
| `JLCPCB Part Class` | 嘉立创SMT贴片分类 | `"Extended Part"` |

#### 器件参数属性（可选，因器件类型而异）
- 电阻：`Tolerance`、`Temperature Coefficient`
- 电容：`Voltage Rated`、`Tolerance`
- 电感：`Saturation Current (Isat)`、`DC Resistance (DCR)`
- 晶振：`Frequency Tolerance`、`Load Capacitance`

---

### pinInfoMap（引脚信息）
`pinInfoMap` 是一个对象，键为引脚标识符，值为引脚信息对象。

#### 引脚信息对象结构
```json
{
    "name": "PB6",
    "number": "PB6",
    "net": "I2C1_SCL",
    "props": {
        "Pin Number": "PB6"
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 引脚名称 |
| `number` | string | 引脚编号（与键相同） |
| `net` | string | 该引脚连接的网络名称，空字符串表示未连接 |
| `props` | object | 引脚属性，通常包含 `"Pin Number"` |

#### 网络命名规则
- **用户命名网络**：如 `"VCC"`、`"GND"`、`"+12V"`、`"SPI1_SCK"`
- **自动生成网络**：以 `$` 开头，格式为 `$<页面编号>N<序号>`，如 `"$1N2"`、`"$10N639"`
- **空字符串** `""` 表示引脚未连接（NC）

---

## designRule（设计规则）

### trackPhysics（走线物理规则）
```json
{
    "copperThickness1oz": {
        "name": "copperThickness1oz",
        "isDefault": true,
        "unit": "mm",
        "strokeValue": {
            "common": {
                "min": 0.127,
                "max": 2.54,
                "default": 0.254
            }
        }
    }
}
```

### netRule（网络规则）
为每个网络指定适用的设计规则。
```json
{
    "VCC": {
        "net": "VCC",
        "ruleMap": { "TrackPhysics": "" }
    }
}
```

---

## hw2c 解析策略

| .enet 字段 | hw2c 映射 |
|------------|-----------|
| `props.Designator` | 元器件引用名（ref） |
| `props.Value` | 元器件值，用于 MCU 检测和外设类型匹配 |
| `props.FootprintName` | 封装名 |
| `props.DeviceName` | 器件名，辅助类型识别 |
| `pinInfoMap[pin].net` | 网络名，用于重建连接关系 |
| `pinInfoMap[pin].number` | 引脚号，用于引脚分配 |
| `pinInfoMap[pin].name` | 引脚名，用于信号识别 |

### 网络重建
1. 遍历所有元器件的 `pinInfoMap`
2. 按 `net` 字段分组，相同 net 名的引脚属于同一网络
3. 过滤规则：跳过空字符串（NC）、跳过仅含 1 个器件的网络、跳过无 MCU 连接且无外设的网络

### MCU 检测
在 `props.Value` 中匹配 `STM32` / `GD32` / `AT32` 前缀。
