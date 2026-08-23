# 紫微斗数跨平台软件系统架构设计文档

## 1. 架构目标

本项目目标是建设一个长期可扩展的紫微斗数软件平台，而不是单一客户端应用。

系统需要同时支持：

- Linux Desktop

- Windows Desktop

- macOS Desktop

- Android App

- iPhone App

- Web 应用

核心设计原则：

1. **紫微斗数算法作为独立核心资产**

2. **业务模型和数据结构统一**

3. **客户端根据平台选择最佳技术**

4. **支持本地离线运行**

5. **支持未来云同步和商业化扩展**

6. **为 AI 智能解盘预留接口**

---

# 2. 总体架构

整体采用：

> Python Domain Core + FastAPI 服务层 + 多端客户端架构

```
                         用户端


        ┌───────────────────────────────┐
        │                               │
        │             Web               │
        │                               │
        │       Vue3 + TypeScript       │
        │                               │
        └───────────────┬───────────────┘
                        │
                        │ HTTPS API
                        │

                 ┌──────▼──────┐
                 │  FastAPI    │
                 │ Application │
                 └──────┬──────┘
                        │

                 ┌──────▼────────┐
                 │ Ziwei Service │
                 │ Python        │
                 └──────┬────────┘
                        │

                 PostgreSQL


================================================


 Linux Desktop        Windows Desktop        macOS Desktop

        \                  |                    /

                    Tauri + Vue3


                        │

                 Local FastAPI

                        │

                 Python Core

                        │

                    SQLite



================================================


 Android App                 iPhone App

          Flutter

             │

        Local SQLite

             │

       REST API Sync

             │

       Python Backend
```

---

# 3. 核心设计：Ziwei Engine

## 3.1 核心定位

紫微斗数计算引擎是整个产品最重要的资产。

它不属于：

- 桌面端

- Web端

- 移动端

而是独立领域模块。

结构：

```
ziwei-engine

├── calendar
│   ├── lunar calendar
│   ├── solar calendar
│   └── ganzhi calculation
│
├── chart
│   ├── natal chart
│   ├── palace calculation
│   └── chart layout
│
├── stars
│   ├── main stars
│   ├── auxiliary stars
│   └── transformations
│
├── rules
│   ├── sihua
│   ├── daxian
│   └── liunian
│
├── analysis
│   └── interpretation engine
│
└── models
```

---

## 3.2 Core设计原则

核心模块：

- 不依赖 UI

- 不依赖数据库

- 不依赖 API

例如：

```python
chart = ZiweiChart(
    birth_date="1985-05-12",
    hour="子时",
    gender="male"
)

result = chart.calculate()
```

输出标准结构：

```json
{
  "ming_gong": {
    "stars": [
      "紫微",
      "天府"
    ]
  }
}
```

---

# 4. 后端架构

## 4.1 技术选择

后端：

- Python

- FastAPI

- SQLAlchemy

原因：

- 紫微算法天然适合 Python

- AI生态成熟

- 方便未来接入 LLM

- 数据处理能力强

---

## 4.2 服务结构

```
FastAPI

├── user service
│
├── chart service
│
├── report service
│
├── sync service
│
└── AI interpretation service
```

---

# 5. 客户端架构

# 5.1 Web应用

技术：

```
Vue3
+
TypeScript
+
SVG / Canvas
```

用途：

- 免费排盘入口

- SEO流量入口

- 用户中心

- 在线报告

- 会员体系

---

# 5.2 Desktop应用

技术：

```
Vue3
+
Tauri
```

支持：

- Linux

- Windows

- macOS

优势：

- 同一套前端代码

- 体积小

- 跨平台能力强

运行模式：

```
Tauri

  |

Local FastAPI

  |

Python Ziwei Engine

  |

SQLite
```

---

# 5.3 Mobile应用

技术：

```
Flutter
```

支持：

- Android

- iOS

用途：

- 快速排盘

- 收藏命盘

- AI解释

- 分享

本地：

```
Flutter

  |

SQLite

  |

Sync API

  |

Cloud Database
```

---

# 6. 数据库设计

## 6.1 数据库策略

支持：

本地：

```
SQLite
```

云端：

```
PostgreSQL
```

两者保持：

- 相同数据模型

- 相同业务结构

---

# 6.2 数据模型

核心表：

```
user

account

chart

chart_snapshot

palace

star_position

interpretation

engine_version

sync_record
```

---

## 6.3 算法版本管理

必须记录：

```
chart

id

engine_version

created_time
```

原因：

未来可能调整：

- 排盘规则

- 四化规则

- 流派算法

历史命盘必须可以复现。

---

# 7. 本地离线设计

## Linux/Desktop

```
Application

↓

SQLite

↓

Ziwei Engine
```

支持：

- 离线排盘

- 本地历史记录

- 文件备份

---

## Mobile

```
Flutter

↓

SQLite

↓

Sync Service
```

支持：

- 无网络使用

- 本地收藏

- 云同步

---

# 8. 数据同步设计

未来支持：

```
Local SQLite

       ↓

 Sync Engine

       ↓

PostgreSQL Cloud
```

同步记录：

```
sync_record

id

object_type

object_id

local_version

cloud_version

sync_time

status
```

---

# 9. AI扩展架构

AI不参与计算。

正确流程：

```
用户出生信息

        ↓

Ziwei Engine

        ↓

结构化命盘数据

        ↓

AI Interpretation

        ↓

自然语言报告
```

AI负责：

- 性格分析

- 事业分析

- 财运分析

- 流年解释

核心算法仍由规则引擎负责。

---

# 10. 最终技术栈

| 模块    | 技术                  |
| ----- | ------------------- |
| 核心算法  | Python              |
| 业务模型  | Python Domain Model |
| API   | FastAPI             |
| ORM   | SQLAlchemy          |
| 本地数据库 | SQLite              |
| 云数据库  | PostgreSQL          |
| Web   | Vue3 + TypeScript   |
| 桌面    | Tauri + Vue3        |
| 移动    | Flutter             |
| 图形展示  | SVG / Canvas        |
| AI服务  | Python + LLM        |

---

# 11. 开发路线

## Phase 1：核心引擎

目标：

完成：

- 历法转换

- 干支

- 十二宫

- 安星

- 四化

- 大限

- 流年

技术：

```
Python
SQLite
```

---

## Phase 2：Desktop专业版

增加：

```
Vue3
+
Tauri
```

实现：

- Linux

- Windows

- macOS

---

## Phase 3：Web平台

增加：

```
FastAPI
+
PostgreSQL
+
Vue3
```

实现：

- 在线排盘

- 用户体系

- 云端报告

---

## Phase 4：Mobile

增加：

```
Flutter
+
SQLite
+
同步机制
```

实现：

- Android

- iPhone

---

# 12. 最终架构理念

本项目不是开发一个单独的软件，而是建设：

> 一个以 Python 紫微计算引擎为核心，支持桌面、Web、移动端、多数据库模式和 AI 扩展的跨平台紫微斗数计算平台。

核心资产：

```
Ziwei Engine
+
统一数据模型
+
规则体系
```

客户端只是不同入口。
