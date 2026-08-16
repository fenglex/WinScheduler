"""数据库管理器：SQLite 持久化（标准库 sqlite3，无第三方依赖）。

- 数据文件：%APPDATA%/WinScheduler/tasks.db
- 线程模型：单连接 + RLock 串行化（写入方包括主线程与任务工作线程），
  开启 WAL 模式降低读写冲突。
- 时间字段以 ISO 8601 文本存储，读取时还原为 datetime。
- 对外接口与旧内存桩完全一致（模块级函数 + DatabaseManager 类）。
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any

from config import DB_PATH

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

# update_task_times 的“未传参”哨兵：None 表示清空，_UNSET 表示不更新
_UNSET = object()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
    return _conn


def _iso(dt) -> str | None:
    """datetime → ISO 文本；None → None。"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _from_iso(s) -> datetime | None:
    """ISO 文本 → datetime；无效/空 → None。"""
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def init_db() -> None:
    """创建表结构（幂等）。"""
    with _lock:
        conn = _get_conn()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            description    TEXT NOT NULL DEFAULT '',
            command        TEXT NOT NULL,
            command_type   TEXT NOT NULL DEFAULT 'shell',
            work_dir       TEXT NOT NULL DEFAULT '',
            trigger_type   TEXT NOT NULL DEFAULT 'cron',
            trigger_config TEXT NOT NULL DEFAULT '{}',
            enabled        INTEGER NOT NULL DEFAULT 1,
            max_instances  INTEGER NOT NULL DEFAULT 1,
            misfire_grace  INTEGER NOT NULL DEFAULT 60,
            timeout        INTEGER NOT NULL DEFAULT 0,
            next_run_at    TEXT,
            last_run_at    TEXT,
            last_status    TEXT,
            created_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL,
            started_at  TEXT,
            finished_at TEXT,
            exit_code   INTEGER,
            status      TEXT NOT NULL DEFAULT 'running',
            duration    REAL,
            log_content TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_run_logs_task ON run_logs(task_id);
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        conn.commit()


# ── 任务 CRUD ────────────────────────────────────────

def _row_to_task(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "command": row["command"],
        "command_type": row["command_type"],
        "work_dir": row["work_dir"],
        "trigger_type": row["trigger_type"],
        "trigger_config": row["trigger_config"],
        "enabled": bool(row["enabled"]),
        "max_instances": row["max_instances"],
        "misfire_grace": row["misfire_grace"],
        "timeout": row["timeout"],
        "next_run_at": _from_iso(row["next_run_at"]),
        "last_run_at": _from_iso(row["last_run_at"]),
        "last_status": row["last_status"],
        "created_at": _from_iso(row["created_at"]),
    }


_TASK_FIELDS = {
    "name", "description", "command", "command_type", "work_dir",
    "trigger_type", "trigger_config", "enabled", "max_instances",
    "misfire_grace", "timeout",
}


def get_all_tasks() -> list[dict]:
    with _lock:
        rows = _get_conn().execute(
            "SELECT * FROM tasks ORDER BY id").fetchall()
        return [_row_to_task(r) for r in rows]


def get_task(task_id: int) -> dict | None:
    with _lock:
        row = _get_conn().execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None


def create_task(data: dict) -> int:
    now = datetime.now().isoformat()
    task = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "command": data.get("command", ""),
        "command_type": data.get("command_type", "shell"),
        "work_dir": data.get("work_dir", ""),
        "trigger_type": data.get("trigger_type", "cron"),
        "trigger_config": data.get("trigger_config", "{}"),
        "enabled": 1 if data.get("enabled", True) else 0,
        "max_instances": data.get("max_instances", 1),
        "misfire_grace": data.get("misfire_grace", 60),
        "timeout": data.get("timeout", 0),
    }
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO tasks (name, description, command, command_type,"
            " work_dir, trigger_type, trigger_config, enabled, max_instances,"
            " misfire_grace, timeout, created_at)"
            " VALUES (:name, :description, :command, :command_type,"
            " :work_dir, :trigger_type, :trigger_config, :enabled,"
            " :max_instances, :misfire_grace, :timeout, :created_at)",
            {**task, "created_at": now},
        )
        conn.commit()
        return cur.lastrowid


def update_task(task_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in _TASK_FIELDS}
    if "enabled" in fields:
        fields["enabled"] = 1 if fields["enabled"] else 0
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = :id",
            {**fields, "id": task_id},
        )
        conn.commit()
        return cur.rowcount > 0


def delete_task(task_id: int) -> bool:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM run_logs WHERE task_id = ?", (task_id,))
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0


def set_task_enabled(task_id: int, enabled: bool) -> bool:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE tasks SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, task_id),
        )
        conn.commit()
        return cur.rowcount > 0


def update_task_times(task_id: int, *, next_run=_UNSET, last_run=_UNSET,
                      status=_UNSET) -> bool:
    """更新任务的调度时间/状态。

    next_run=None 表示清空下次运行时间（如作业已不存在），
    未传的关键字不更新。
    """
    sets, params = [], {}
    if next_run is not _UNSET:
        sets.append("next_run_at = :next_run")
        params["next_run"] = _iso(next_run)
    if last_run is not _UNSET:
        sets.append("last_run_at = :last_run")
        params["last_run"] = _iso(last_run)
    if status is not _UNSET:
        sets.append("last_status = :status")
        params["status"] = status
    if not sets:
        return False
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = :id",
            {**params, "id": task_id},
        )
        conn.commit()
        return cur.rowcount > 0


# ── 运行日志 ─────────────────────────────────────────

def _row_to_log(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "started_at": _from_iso(row["started_at"]),
        "finished_at": _from_iso(row["finished_at"]),
        "exit_code": row["exit_code"],
        "status": row["status"],
        "duration": row["duration"],
        "log_content": row["log_content"],
    }


def create_run_log(task_id: int, started_at) -> int:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO run_logs (task_id, started_at, status)"
            " VALUES (?, ?, 'running')",
            (task_id, _iso(started_at)),
        )
        conn.commit()
        return cur.lastrowid


def finish_run_log(log_id: int, finished_at, exit_code: int, status: str,
                   duration: float, log_content: str) -> bool:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE run_logs SET finished_at = ?, exit_code = ?, status = ?,"
            " duration = ?, log_content = ? WHERE id = ?",
            (_iso(finished_at), exit_code, status, duration,
             log_content, log_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_run_logs(*, task_id=None, status=None, limit=500) -> list[dict]:
    sql = "SELECT * FROM run_logs"
    conds, params = [], []
    if task_id is not None:
        conds.append("task_id = ?")
        params.append(task_id)
    if status:
        conds.append("status = ?")
        params.append(status)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _lock:
        rows = _get_conn().execute(sql, params).fetchall()
        return [_row_to_log(r) for r in rows]


def cleanup_old_logs(days: int) -> int:
    """删除结束时间早于 N 天前的日志（运行中的不删）。返回删除条数。"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "DELETE FROM run_logs"
            " WHERE finished_at IS NOT NULL AND finished_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount


# ── 配置 ─────────────────────────────────────────────

def get_config(key: str, default: Any = None) -> Any:
    with _lock:
        row = _get_conn().execute(
            "SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return default


def set_config(key: str, value: Any) -> bool:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        conn.commit()
        return True


class DatabaseManager:
    """统一对外的类入口（供 `from database.manager import DatabaseManager` 使用）。

    实例方法全部委托到模块级函数。
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
