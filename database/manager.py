"""数据库管理器（内存桩）：用于 UI 预览。

⚠️ 注意：当前为最小占位实现，数据保存在内存中，进程退出即丢失。
原始仓库（README 中描述）应使用 SQLite + SQLAlchemy 实现持久化。
此桩仅用于：让 UI 代码完成 import 链路、PyInstaller 打包成功、用户查看美化效果。
"""

import threading
import time
import uuid
from datetime import datetime
from typing import Any

_lock = threading.RLock()
_next_id = 1
_tasks: list[dict] = []
_run_logs: list[dict] = []
_config: dict[str, Any] = {
    "autostart": False,
    "minimize_to_tray": True,
    "log_retention_days": 30,
}


def _alloc_id() -> int:
    global _next_id
    with _lock:
        nid = _next_id
        _next_id += 1
        return nid


def init_db() -> None:
    """初始化（桩：无操作）。"""
    pass


# ── 任务 CRUD ────────────────────────────────────────

def get_all_tasks() -> list[dict]:
    with _lock:
        return [dict(t) for t in _tasks]


def get_task(task_id: int) -> dict | None:
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                return dict(t)
    return None


def create_task(data: dict) -> int:
    task_id = _alloc_id()
    task = {
        "id": task_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "command": data.get("command", ""),
        "command_type": data.get("command_type", "shell"),
        "work_dir": data.get("work_dir", ""),
        "trigger_type": data.get("trigger_type", "cron"),
        "trigger_config": data.get("trigger_config", "{}"),
        "enabled": data.get("enabled", True),
        "max_instances": data.get("max_instances", 1),
        "misfire_grace": data.get("misfire_grace", 60),
        "timeout": data.get("timeout", 0),
        "next_run_at": None,
        "last_run_at": None,
        "last_status": None,
        "created_at": datetime.now().isoformat(),
    }
    with _lock:
        _tasks.append(task)
    return task_id


def update_task(task_id: int, data: dict) -> bool:
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                t.update({
                    k: v for k, v in data.items()
                    if k in {"name", "description", "command", "command_type",
                             "work_dir", "trigger_type", "trigger_config",
                             "enabled", "max_instances", "misfire_grace", "timeout"}
                })
                return True
    return False


def delete_task(task_id: int) -> bool:
    with _lock:
        before = len(_tasks)
        _tasks[:] = [t for t in _tasks if t["id"] != task_id]
        _run_logs[:] = [l for l in _run_logs if l["task_id"] != task_id]
        return len(_tasks) < before


def set_task_enabled(task_id: int, enabled: bool) -> bool:
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                t["enabled"] = bool(enabled)
                return True
    return False


def update_task_times(task_id: int, *, next_run=None, last_run=None, status=None) -> bool:
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                if next_run is not None:
                    t["next_run_at"] = next_run
                if last_run is not None:
                    t["last_run_at"] = last_run
                if status is not None:
                    t["last_status"] = status
                return True
    return False


# ── 运行日志 ─────────────────────────────────────────

def create_run_log(task_id: int, started_at) -> int:
    log_id = _alloc_id()
    with _lock:
        _run_logs.append({
            "id": log_id,
            "task_id": task_id,
            "started_at": started_at,
            "finished_at": None,
            "exit_code": None,
            "status": "running",
            "duration": None,
            "log_content": "",
        })
    return log_id


def finish_run_log(log_id: int, finished_at, exit_code: int, status: str,
                   duration: float, log_content: str) -> bool:
    with _lock:
        for l in _run_logs:
            if l["id"] == log_id:
                l.update({
                    "finished_at": finished_at,
                    "exit_code": exit_code,
                    "status": status,
                    "duration": duration,
                    "log_content": log_content,
                })
                return True
    return False


def get_run_logs(*, task_id=None, status=None, limit=500) -> list[dict]:
    with _lock:
        logs = list(_run_logs)
    if task_id is not None:
        logs = [l for l in logs if l["task_id"] == task_id]
    if status:
        logs = [l for l in logs if l["status"] == status]
    return logs[:limit]


def cleanup_old_logs(days: int) -> int:
    return 0


# ── 配置 ─────────────────────────────────────────────

def get_config(key: str, default: Any = None) -> Any:
    with _lock:
        return _config.get(key, default)


def set_config(key: str, value: Any) -> bool:
    with _lock:
        _config[key] = value
    return True


class DatabaseManager:
    """统一对外的类入口（供 `from database.manager import DatabaseManager` 使用）。

    实例方法全部委托到模块级函数，便于桩/真实实现切换。
    """

    def init_db(self) -> None:
        init_db()

    def get_all_tasks(self):
        return get_all_tasks()

    def get_task(self, task_id: int):
        return get_task(task_id)

    def create_task(self, data: dict) -> int:
        return create_task(data)

    def update_task(self, task_id: int, data: dict) -> bool:
        return update_task(task_id, data)

    def delete_task(self, task_id: int) -> bool:
        return delete_task(task_id)

    def set_task_enabled(self, task_id: int, enabled: bool) -> bool:
        return set_task_enabled(task_id, enabled)

    def update_task_times(self, task_id: int, **kwargs) -> bool:
        return update_task_times(task_id, **kwargs)

    def create_run_log(self, task_id: int, started_at) -> int:
        return create_run_log(task_id, started_at)

    def finish_run_log(self, *args, **kwargs) -> bool:
        return finish_run_log(*args, **kwargs)

    def get_run_logs(self, **kwargs):
        return get_run_logs(**kwargs)

    def cleanup_old_logs(self, days: int) -> int:
        return cleanup_old_logs(days)

    def get_config(self, key: str, default: Any = None) -> Any:
        return get_config(key, default)

    def set_config(self, key: str, value: Any) -> bool:
        return set_config(key, value)
