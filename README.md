# 任务调度器 (WinScheduler)

> Windows 桌面定时任务调度系统 v1.0

一个基于 PySide6 + APScheduler 的 Windows 桌面定时任务管理工具，支持 cron 表达式、固定间隔和一次性定时三种触发方式，实时日志采集与着色，系统托盘后台运行，开机自启。

## 功能特性

- **三种触发方式**：Cron 表达式 / 固定间隔 / 一次性定时
- **指定运行目录**：每个任务可独立设置工作目录 (cwd)
- **实时日志**：按级别着色显示（INFO / WARN / ERROR / SUCCESS）
- **历史日志**：支持按任务、状态筛选，查看完整运行记录
- **系统托盘**：最小化到托盘，后台持续调度
- **开机自启**：通过注册表实现，无需管理员权限
- **单实例锁**：防止重复打开
- **数据持久化**：SQLite 存储任务和日志，重启不丢失
- **暗色主题**：护眼的深色界面

## 快速开始

### 环境要求

- Python 3.11+
- Windows 10/11

### 安装依赖

```bash
# 创建虚拟环境
uv venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

启动后最小化到托盘（用于开机自启场景）：
```bash
python main.py --minimized
```

## 使用说明

### 创建任务

1. 点击工具栏「新建」按钮
2. 填写任务名称和执行命令
3. 选择触发方式：
   - **Cron 表达式**：填写各时间字段（秒/分/时/日/月/周），支持 `*`、`*/5`、`1,3,5`、`1-5` 语法
   - **固定间隔**：设置天/小时/分钟/秒
   - **一次性定时**：选择具体的运行时间
4. 可选设置工作目录、最大并发、宽限期、超时时间
5. 点击「确定」保存

### 管理任务

- **双击任务行**：打开编辑对话框
- **右键任务行**：运行/停止/编辑/复制命令/删除/查看日志
- **工具栏 ▶ 运行**：手动触发选中任务
- **工具栏 ■ 停止**：终止正在运行的任务

### 日志查看

- **实时日志** Tab：实时显示任务输出，支持搜索过滤
- **历史记录** Tab：按任务/状态筛选历史运行记录，点击查看详情

### 系统托盘

- **关闭窗口**：自动最小化到系统托盘（可在设置中关闭）
- **双击托盘图标**：显示主窗口
- **右键托盘图标**：显示窗口 / 暂停调度 / 退出

## 打包发布

```bash
pyinstaller build.spec
```

输出目录：`dist/WinScheduler/`

数据文件位置（运行时自动创建）：
```
%APPDATA%\WinScheduler\
├── tasks.db          # 数据库
└── config.json       # 配置文件（预留）
```

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| GUI | PySide6 6.6+ | 窗口界面、表格、日志面板、系统托盘 |
| 调度 | APScheduler 3.10+ | cron/interval/date 触发器 |
| ORM | SQLAlchemy 2.0+ | 数据库操作 |
| 数据库 | SQLite | 本地数据存储 |
| 打包 | PyInstaller 6.0+ | 打包为 Windows exe |

## 项目结构

```
WinScheduler/
├── main.py                    # 程序入口
├── config.py                  # 全局配置（路径、常量、QSS 主题）
├── requirements.txt
├── build.spec                 # PyInstaller spec
├── database/
│   ├── models.py              # SQLAlchemy 模型（Task / RunLog / AppConfig）
│   └── manager.py             # DatabaseManager（CRUD）
├── core/
│   ├── scheduler_manager.py   # SchedulerManager（封装 APScheduler）
│   ├── task_executor.py       # TaskExecutor（subprocess + 线程）
│   └── log_collector.py       # LogCollector（级别解析/着色）
├── ui/
│   ├── main_window.py         # 主窗口
│   ├── task_edit_dialog.py    # 任务编辑对话框
│   ├── log_panel.py           # 日志面板（实时 + 历史）
│   ├── tray_icon.py           # 系统托盘
│   ├── settings_dialog.py     # 设置对话框
│   └── icons.py               # 程序化图标生成
├── system/
│   ├── autostart.py           # 开机自启（注册表）
│   └── single_instance.py     # 单实例锁（socket）
└── 设计方案.md
```

## License

MIT
