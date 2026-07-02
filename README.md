# Screen Time Dashboard

屏幕使用时间追踪仪表盘 — 实时监控 Windows 系统资源与应用使用习惯的数据看板。

## 功能特性

### 系统监控
- **CPU 使用率** — 实时百分比 + 历史趋势迷你图
- **内存使用率** — 实时百分比 + 已用 GB 数值
- **CPU 核心数** — 逻辑核心数显示
- **GPU 占用** — 独立显卡使用率
- **浏览器标签** — 追踪当前活跃标签页

### 应用分析
- **活跃时长** — 按小时/日统计应用前台使用时间
- **应用排行** — 按使用时长排序的应用明细表
- **启动次数** — 统计应用切换频率
- **通知统计** — 记录应用推送通知数量

### 数据可视化
- **7 日热力图** — 按小时展示每周使用强度分布
- **环形占比图** — 各应用使用时间占比
- **柱状趋势图** — 按小时/日展示使用趋势
- **分类统计** — 办公/开发/浏览器/社交/娱乐/工具六大类别
- **效率评分** — 综合工作效率、专注度、平衡性的评分（优秀/良好/一般）

### 其他
- 深色/亮色主题切换
- 中/英文双语界面
- CSV 数据导出
- 长期数据存储（SQLite）
- 每周环比变化趋势

## 技术栈

| 层级 | 技术 |
|------|------|
| 数据采集 | Python + psutil + GPUtil |
| 后端服务 | Flask（端口 19999） |
| 前端界面 | 原生 HTML/CSS/JS（无外部 CDN 依赖） |
| 数据存储 | SQLite（`%APPDATA%/ScreenTime/screentime.db`） |
| 计划任务 | Windows 任务计划程序 / 开机自启 |

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.9+
- NVIDIA 显卡（GPU 监控需要）

### 安装依赖

```bash
pip install flask psutil GPUtil
```

### 启动面板

双击 `panel.bat` 自动启动后端服务并打开浏览器，或手动运行：

```bash
python server.py        # 启动后端（端口 19999）
start http://localhost:19999
```

### 启动后台采集

```bash
pythonw tracker.py      # 静默后台运行，每分钟采集一次
```

## 项目结构

```
screen-time-dashboard/
├── tracker.py          # 后台数据采集（窗口追踪 + 系统指标）
├── server.py           # Flask Web 服务 + REST API
├── index.html          # 前端仪表盘界面
├── panel.bat           # 桌面快捷启动脚本
├── start.bat           # 同时启动采集 + 面板
├── future_features.md  # 未来规划功能清单
└── .gitignore
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/today` | 今日使用数据 |
| `GET /api/heatmap` | 7 日热力图数据 |
| `GET /api/score` | 效率评分 |
| `GET /api/system` | 系统指标（CPU/内存/GPU） |
| `GET /api/browser-tabs` | 浏览器标签活动 |
| `GET /api/custom-range?start=&end=` | 自定义日期范围查询 |
| `GET /api/export?start=&end=` | CSV 导出 |

## 截图

![仪表盘截图](screenshot.png)

## License

MIT
