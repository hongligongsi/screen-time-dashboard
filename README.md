# Screen Time Dashboard

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

屏幕使用时间追踪仪表盘 — 实时监控 Windows 系统资源与应用使用习惯的本地数据看板。采集进程驻留后台，Web 面板提供直观的可视化界面，所有数据存储在本地 SQLite 数据库，无需联网，不依赖任何外部 CDN。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [架构与数据流](#架构与数据流)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [License](#license)

---

## 功能特性

### 系统监控
| 指标 | 说明 |
|------|------|
| CPU 使用率 | 实时百分比，带 24 小时历史趋势迷你图 |
| CPU 核心数 | 物理 + 逻辑核心数 |
| 内存使用率 | 百分比 + 已用 / 总容量 GB |
| GPU 占用 | NVIDIA 独立显卡实时负载 |
| 浏览器标签 | 当前活跃标签页数量与详情 |

### 应用分析
| 功能 | 说明 |
|------|------|
| 活跃时长 | 精确到秒的前台窗口停留时间，按小时/日/周聚合 |
| 应用排行 | 按使用时长的 Top N 明细表，含启动次数 |
| 窗口切换 | 追踪应用焦点切换频率，反映多任务强度 |
| 通知统计 | 记录各应用推送的 Windows 通知数量 |
| 六大分类 | 办公 / 开发 / 浏览器 / 社交 / 娱乐 / 工具，自动归类 |

### 数据可视化
- **7 日热力图** — 按小时 × 天展示每周使用强度分布
- **环形占比图** — ECharts 渲染各应用使用时间占比
- **趋势折线图** — 按小时/日展示使用量变化趋势
- **效率评分** — 综合工作效率、专注度、任务平衡性的加权评分（优秀 / 良好 / 一般 / 待改善）
- **环比变化** — 各指标周环比上升/下降百分比

### 用户体验
- 深色/亮色主题一键切换，跟随系统偏好
- 中/英文双语界面
- CSV 自定义日期范围导出
- 数据面板 30 秒自动刷新
- PWA 支持，可安装为桌面应用

---

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 数据采集 | Python 3.9+ `psutil` `GPUtil` `win32gui` | 每分钟采集窗口标题 + 系统指标 |
| 后端框架 | Flask 3.x | REST API + WebSocket 实时推送 |
| 前端界面 | 原生 HTML5 / CSS3 / Vanilla JS | 零框架、零 CDN 依赖 |
| 图表引擎 | ECharts 5.x（本地静态文件） | 热力图 / 环形图 / 趋势线 |
| 数据存储 | SQLite 3 | 10 张表，存储在 `%APPDATA%\ScreenTime\` |
| 进程管理 | Windows 任务计划 + `panel.bat` | 开机自启 + 一键启动面板 |

---

## 架构与数据流

```
┌──────────────┐   每分钟采集    ┌──────────────┐   REST API    ┌──────────────┐
│  tracker.py  │ ──────────────→ │   SQLite DB  │ ←─────────── │  server.py   │
│  后台采集进程  │   INSERT OR     │  本地数据库   │  查询/写入    │  Flask 服务   │
│              │   REPLACE      │              │              │  端口 19999   │
└──────────────┘                └──────────────┘              └──────┬───────┘
                                                                     │
                                                            HTTP/WebSocket
                                                                     │
                                                              ┌──────┴───────┐
                                                              │  index.html  │
                                                              │  仪表盘前端   │
                                                              │  + ECharts   │
                                                              └──────────────┘
```

- **tracker.py**：后台守护进程，每分钟获取前台窗口标题、进程名，采集 CPU/内存/GPU 数据，写入 SQLite
- **server.py**：Flask Web 服务器，提供 REST API 查询接口，托管前端静态文件
- **index.html**：单页仪表盘，通过 `fetch()` 轮询 API，ECharts 渲染图表，支持 WebSocket 实时推送

### 数据库设计（10 张表）

| 表名 | 用途 | 写入频率 |
|------|------|---------|
| `daily_app_usage` | 按应用按小时聚合使用时长 | 每分钟 |
| `daily_usage` | 每日总活跃时长 | 每分钟 |
| `system_metrics` | CPU/内存/GPU 快照 | 每分钟 |
| `hourly_activity` | 按小时活跃秒数 | 每分钟 |
| `browser_tabs` | 浏览器标签页快照 | 按需 |
| `browser_tab_history` | 标签页历史记录 | 按需 |
| `app_notifications` | 应用通知记录 | 事件驱动 |
| `daily_summary` | 每日汇总（含分类统计） | 每次启动 |
| `app_categories` | 应用分类映射 | 手动维护 |
| `insights` | AI 生成的洞察建议 | 按需 |

---

## 快速开始

### 环境要求

- **操作系统**：Windows 10 1809+ / Windows 11
- **Python**：3.9 及以上（推荐 3.11+）
- **显卡**：非必需，NVIDIA GPU 需额外安装驱动以启用 GPU 监控
- **浏览器**：Chrome 90+ / Edge 90+ / Firefox 88+

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/hongligongsi/screen-time-dashboard.git
cd screen-time-dashboard

# 2. 安装 Python 依赖
pip install flask psutil GPUtil pywin32

# 3. 启动（推荐使用一键脚本）
panel.bat
```

### 启动方式

| 方式 | 命令 | 说明 |
|------|------|------|
| 一键启动 | 双击 `panel.bat` | 启动后端 + 打开浏览器 |
| 完整启动 | 双击 `start.bat` | 启动采集 + 后端 + 浏览器 |
| 仅后端 | `python server.py` | 访问 `http://localhost:19999` |
| 仅采集 | `pythonw tracker.py` | 后台静默运行，无窗口 |
| 开机自启 | `install_task.bat` | 注册 Windows 任务计划 |

---

## 项目结构

```
screen-time-dashboard/
├── tracker.py           # 后台数据采集进程
│   ├── 窗口焦点追踪（win32gui）
│   ├── 系统指标采集（psutil/GPUtil）
│   └── SQLite 数据持久化
├── server.py            # Flask Web 服务
│   ├── 22 个 REST API 端点
│   ├── WebSocket 实时推送
│   └── 静态文件托管
├── index.html           # 单页仪表盘前端
│   ├── 系统监控面板
│   ├── 应用分析面板
│   ├── 热力图 & 趋势图
│   └── ECharts 集成
├── echarts.min.js       # ECharts 本地静态文件
├── sw.js                # Service Worker（PWA 离线缓存）
├── manifest.json        # PWA 应用清单
├── panel.bat            # 一键启动面板
├── start.bat            # 启动采集 + 面板
├── install_task.bat     # 注册开机自启任务
├── future_features.md   # 未来规划
├── .gitignore
└── README.md
```

---

## API 文档

### 核心接口

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/today` | 今日使用总览（总时长、应用排行、分类占比） |
| `GET` | `/api/system` | 实时系统指标（CPU%、内存 GB/%、GPU%） |
| `GET` | `/api/heatmap` | 最近 7 天热力图数据（小时 × 天矩阵） |
| `GET` | `/api/score` | 效率综合评分 |
| `GET` | `/api/browser-tabs` | 当前浏览器活跃标签 |
| `GET` | `/api/browser-tab-history` | 标签页历史记录 |
| `GET` | `/api/insights` | 使用洞察与建议 |
| `GET` | `/api/anomalies` | 异常活动检测 |
| `GET` | `/api/streaks` | 连续活跃天数 |
| `GET` | `/api/metrics` | 今日各指标明细 |
| `GET` | `/api/custom-range?start=&end=` | 自定义日期范围查询 |
| `GET` | `/api/export?start=&end=` | CSV 数据导出 |
| `GET` | `/api/app-usage` | 应用使用时长明细 |
| `GET` | `/api/hourly-activity` | 按小时活跃度数据 |

### 响应示例

```json
// GET /api/system
{
  "cpu_percent": 12.5,
  "cpu_cores": 16,
  "memory_percent": 56.3,
  "memory_used_gb": 17.9,
  "memory_total_gb": 31.8,
  "gpu_percent": 4.2
}

// GET /api/today
{
  "total_active_seconds": 18420,
  "total_active_hours": 5.12,
  "app_usage": [
    {"app_name": "Code", "seconds": 5400, "category": "开发"},
    {"app_name": "Chrome", "seconds": 3600, "category": "浏览器"}
  ],
  "hourly": [0, 0, 0, 120, 1800, 3600, ...]
}
```

---

## 配置说明

所有配置通过修改 `server.py` 和 `tracker.py` 顶部的常量完成：

| 配置项 | 位置 | 默认值 | 说明 |
|--------|------|--------|------|
| 采集间隔 | `tracker.py` `INTERVAL` | 60 秒 | 系统指标采样频率 |
| 服务端口 | `server.py` `PORT` | 19999 | Flask 监听端口 |
| 数据库路径 | `tracker.py` `DB_PATH` | `%APPDATA%\ScreenTime\` | SQLite 文件位置 |
| 数据保留 | `tracker.py` | 90 天 | 超过保留期的数据自动清理 |
| 活跃阈值 | `tracker.py` `ACTIVE_THRESHOLD` | 600 秒 | 计入"活跃天"的最小使用时长 |

---

## 常见问题

**Q：启动后仪表盘显示"图表加载失败"？**
> 检查 `echarts.min.js` 是否在项目目录下，确保浏览器未缓存旧版本（Ctrl+F5 强制刷新）。

**Q：GPU 显示为 0% 或 N/A？**
> 本机无 NVIDIA 独显，或 `nvidia-smi` 未安装。可忽略，不影响其他功能。

**Q：应用使用时长不准确？**
> tracker.py 通过前台窗口标题识别应用，同一进程名聚合。若某应用窗口标题不含进程名，可能归类不准确。

**Q：如何清除所有历史数据？**
> 删除 `%APPDATA%\ScreenTime\screentime.db` 后重启 tracker.py 即可重建。

**Q：端口 19999 被占用？**
> 修改 `server.py` 中的 `PORT` 常量，并同步更新 `panel.bat` 中的 URL。

---

## 更新日志

### v3.1 (2026-07)
- 修复 tracker 重启导致当天数据丢失的严重 Bug（DELETE+INSERT → INSERT OR REPLACE）
- 新增启动时加载已有数据，避免数据断层
- 新增空进程名过滤，清除脏数据
- 补全 system_metrics / daily_summary 表结构迁移
- 修复 ECharts 加载检测误判，移除 __echartsReady 机制
- 图表初始化增加 try-catch 保护
- 新增 echarts.min.js 本地静态文件，消除 CDN 依赖

### v3.0 (2026-06)
- 初始版本发布
- 系统监控 + 应用分析 + 数据可视化三大模块
- 10 张 SQLite 表设计
- 22 个 REST API 端点
- PWA 离线支持

---

## License

MIT © hongligongsi
