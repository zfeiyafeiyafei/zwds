# 紫微斗数智能分析平台数据库设计文档（V1.0）

## 1. 数据库设计目标

本数据库设计服务于：

> 一个支持多流派、多端、本地离线、云同步、规则计算、AI分析的紫微斗数智能分析平台。

核心目标：

1. **支持紫微斗数排盘计算**

2. **支持不同流派规则体系**

3. **支持星曜、宫位、格局等知识库**

4. **支持用户保存多个命盘**

5. **支持 JSON 命盘导入导出**

6. **支持 AI 分析与 Prompt 管理**

7. **支持 SQLite（本地）和 PostgreSQL（云端）统一模型**

---

# 2. 总体数据库架构

数据库分为四大领域：

```text
Ziwei Database

├── A. Rule Engine Database
│
│   流派
│   规则包
│   排盘规则
│   四化规则
│   大限规则
│   分析规则
│
├── B. Knowledge Database
│
│   星曜
│   十二宫
│   神煞
│   格局
│   解释知识
│
├── C. User Chart Database
│
│   用户
│   人物
│   命盘
│   十二宫实例
│   星曜落宫
│   大限流年小限
│
└── D. AI & Analysis Database
│
    分析结果
    Prompt模板
    AI报告
    同步记录
```

---

# 3. 核心设计原则

## 3.1 基础数据与规则数据分离

必须区分：

```
什么是什么？
        ↓
Knowledge Base

如何计算？
        ↓
Rule Engine

如何解释？
        ↓
Analysis Engine
```

例如：

### 星曜：

```
紫微是什么？
```

属于知识库。

### 紫微如何定位？

属于规则库。

### 紫微在命宫如何解释？

属于分析规则。

---

# 4. 流派与规则体系设计（核心）

## 4.1 为什么需要流派模型

紫微斗数存在：

- 三合派

- 飞星派

- 钦天派

- 河洛派

- 四化体系

不同体系可能影响：

- 排盘规则

- 四化规则

- 大限规则

- 格局判断

- 分析解释

因此必须支持：

> 同一个出生资料，可以按照不同规则体系生成不同命盘解释。

---

# 5. Rule Engine 数据库

---

# 5.1 school（流派表）

定义理论体系。

## 表：

```
school
```

字段：

| 字段          | 说明   |
| ----------- | ---- |
| id          | 主键   |
| name        | 流派名称 |
| code        | 编码   |
| description | 说明   |
| version     | 版本   |
| status      | 状态   |

示例：

```
1 三合派
2 飞星派
3 钦天派
```

---

# 5.2 rule_package（规则包）

不要直接绑定单个规则。

应该：

> 一个流派 + 一套规则版本 = 一个规则包

例如：

```
三合派传统版 V1.0
飞星派现代版 V1.0
```

表：

```
rule_package
```

字段：

| 字段          | 说明  |
| ----------- | --- |
| id          |     |
| school_id   |     |
| name        |     |
| version     |     |
| description |     |
| status      |     |

关系：

```
school

  |

rule_package
```

---

# 5.3 calendar_rule（历法规则）

负责：

- 农历转换

- 节气

- 四柱

- 子时跨日

字段：

```
calendar_rule

id

rule_package_id

rule_type

condition_json

result_json

priority
```

例如：

```
子时是否换日

晚子时按次日
```

你的示例 JSON 中明确包含：

- 钟表时间

- 真太阳时

- 农历时间

- 节气四柱

- 非节气四柱

这些均属于历法计算结果。

---

# 5.4 star_position_rule（安星规则）

负责：

- 紫微定位

- 天府定位

- 辅星定位

- 小星定位

字段：

```
star_position_rule

id

rule_package_id

star_id

rule_type

condition_json

result_json

priority
```

---

# 5.5 sihua_rule（四化规则）

负责：

- 生年四化

- 飞化

- 自化

字段：

```
sihua_rule

id

rule_package_id

heavenly_stem

star_id

hua_type

direction
```

支持：

```
化禄
化权
化科
化忌

离心
向心
```

示例 JSON 中存在：

- 生年四化

- 自化方向

- 自化类型。

---

# 5.6 period_rule（时间周期规则）

负责：

- 大限

- 流年

- 小限

字段：

```
period_rule

id

rule_package_id

period_type

condition_json

result_json
```

---

# 5.7 analysis_rule（分析规则）

负责：

- 格局判断

- 星曜组合

- 宫位分析

字段：

```
analysis_rule

id

rule_package_id

rule_type

condition_json

result_json

priority
```

---

# 6. Knowledge Base 数据库

---

# 6.1 star（星曜基础表）

保存所有星曜。

字段：

```
star

id

name

code

category

level

description
```

category：

```
主星

辅星

小星

煞星
```

你的 JSON 中明确区分：

- 主星

- 辅星

- 小星。

---

# 6.2 star_attribute（星曜属性）

保存：

- 五行

- 阴阳

- 象义

- 性格关键词

字段：

```
star_attribute

id

star_id

attribute_type

attribute_value
```

---

# 6.3 palace_definition（十二宫定义）

固定十二宫。

字段：

```
palace_definition

id

name

sequence

description
```

例如：

```
命宫
兄弟宫
夫妻宫
财帛宫
官禄宫
```

---

# 6.4 star_status_definition（星曜状态）

保存：

```
庙
旺
得
利
平
陷
```

字段：

```
id

name

description
```

注意：

状态不是星曜属性。

因为：

同一颗星，在不同宫位可能不同状态。

---

# 6.5 shensha_definition（神煞）

保存：

- 岁前星

- 将前星

- 十二长生

- 太岁煞禄

字段：

```
shensha_definition

id

type

name

description
```

示例 JSON 每宫包含：

- 岁前星

- 将前星

- 十二长生

- 太岁煞禄。

---

# 6.6 pattern_definition（格局库）

保存：

例如：

- 紫府朝垣

- 杀破狼

- 机月同梁

字段：

```
pattern_definition

id

name

category

description
```

---

# 7. User Chart 数据库

---

# 7.1 user

系统账号。

```
user

id

username

email

password_hash

created_time
```

---

# 7.2 person（排盘对象）

一个用户可以有多个对象：

例如：

- 自己

- 孩子

- 配偶

- 客户

字段：

```
person

id

user_id

name

gender

birthday

remark
```

---

# 7.3 chart（命盘主表）

核心表。

字段：

```
chart

id

person_id

rule_package_id

engine_version


solar_datetime

lunar_datetime

longitude

timezone


gender

body_master

life_master

body_palace

origin_palace


created_time
```

你的 JSON 中包含：

- 身主

- 命主

- 身宫

- 来因宫

这些应该作为结构化字段保存。

---

# 7.4 chart_palace（命盘十二宫）

保存某一个具体命盘的十二宫。

字段：

```
chart_palace

id

chart_id

palace_definition_id

heavenly_stem

earth_branch

position
```

例如：

```
福德宫

丙子
```

对应 JSON：

“宫名 + 宫位标识”。

---

# 7.5 chart_star（星曜落宫）

核心关联表。

字段：

```
chart_star

id

chart_id

chart_palace_id

star_id


category

status_id


birth_hua

self_hua_json
```

支持：

例如：

```
天同

旺

自化禄

离心
```

---

# 7.6 chart_shensha

保存命盘中的神煞。

字段：

```
chart_shensha

id

chart_id

chart_palace_id

type

name
```

---

# 7.7 chart_period

统一保存：

- 大限

- 流年

- 小限

字段：

```
chart_period

id

chart_id

period_type

age_start

age_end

year

chart_palace_id
```

例如：

JSON 中：

```
大限:
106~115虚岁

小限:
11,23,35

流年:
1,13,25
```

---

# 8. JSON 快照设计

数据库结构化保存之外，需要支持：

```
chart_snapshot
```

字段：

```
id

chart_id

json_content

engine_version

created_time
```

用途：

- 导出

- 分享

- AI输入

- 数据备份

---

# 9. AI 分析数据库

---

# 9.1 prompt_template

保存提示词。

字段：

```
prompt_template

id

name

category

template_content

variables
```

例如：

```
综合分析

婚姻分析

职业分析

儿童成长分析
```

---

# 9.2 analysis_result

保存分析结果。

字段：

```
analysis_result

id

chart_id

analysis_type

rule_package_id

content_json

created_time
```

---

# 9.3 ai_report

最终报告。

字段：

```
ai_report

id

chart_id

prompt_id

model_name

content

created_time
```

---

# 10. 同步设计

支持：

SQLite ↔ PostgreSQL

表：

```
sync_record

id

object_type

object_id

local_version

cloud_version

status

updated_time
```

---

# 11. 最终 ER 关系

```
                 school

                    |

              rule_package

                    |

 ------------------------------------------------

 |             |             |                 |

calendar    star_rule     sihua_rule     analysis_rule



                    star

                     |

              chart_star

                     |

chart ---- chart_palace ---- palace_definition

                     |

              chart_period

                     |

              analysis_result


person

  |

chart

  |

chart_snapshot
```

---

# 12. 最终设计原则总结

## 基础数据：

共享：

```
星曜
宫位
神煞
格局
```

---

## 规则数据：

隔离：

```
流派
规则包
排盘规则
四化规则
分析规则
```

---

## 用户数据：

实例化：

```
用户
人物
命盘
十二宫
星曜落宫
周期
```

---

## AI数据：

扩展：

```
Prompt
分析结果
报告
模型记录
```

---

最终形成：

> **一个支持多流派规则、多端运行、离线计算、云同步和 AI 解读的紫微斗数数据平台。**

这个数据库设计已经可以作为后续：

- SQL建表设计

- Python ORM设计

- JSON Schema设计

- API接口设计

的基础版本。下一步建议进入 **“数据库物理模型设计（MySQL/PostgreSQL/SQLite 建表 SQL + SQLAlchemy ORM模型）”**。
