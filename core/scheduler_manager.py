"""调度管理器：封装 APScheduler，管理任务注册/移除/暂停/恢复。

设计决策：
  - 使用 MemoryJobStore 而非 SQLAlchemyJobStore（避免 pickle 序列化自定义对象的问题）。
  - 任务定义持久化在 tasks 表中，启动时从数据库恢复。
  - 作业回调仅传 task_id，触发时从 DB 取最新定义，保证编辑后立即生效。
"""

import json
from datetime import datetime

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

try:
    from tzlocal import get_localzone
    _LOCAL_TZ = get_localzone()
except Exception:
    _LOCAL_TZ = None

from config import TRIGGER_CRON, TRIGGER_DATE, TRIGGER_INTERVAL
from core.task_executor import TaskExecutor
from database.manager import DatabaseManager


class SchedulerManager:
    """封装 APScheduler，管理任务生命周期。"""

    def __init__(self, db_manager: DatabaseManager, executor: TaskExecutor):
        self.db = db_manager
        self.executor = executor
        self._started = False

        scheduler_kwargs = {
            "jobstores": {"default": MemoryJobStore()},
            "executors": {"default": ThreadPoolExecutor(max_workers=10)},
            "job_defaults": {
                "max_instances": 1,
                "misfire_grace_time": 60,
                "coalesce": True,
            },
        }
        if _LOCAL_TZ is not None:
            scheduler_kwargs["timezone"] = _LOCAL_TZ

        self.scheduler = BackgroundScheduler(**scheduler_kwargs)

    # ── 生命周期 ──────────────────────────────────────────

    def start(self):
        """启动调度器，从数据库恢复所有启用的任务。"""
        self.scheduler.start()
        self._started = True
        self._reload_jobs()

    def shutdown(self, wait: bool = False):
        """关闭调度器。"""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False

    @property
    def running(self) -> bool:
        return self._started and self.scheduler.running

    # ── 任务管理 ──────────────────────────────────────────

    def _reload_jobs(self):
        """从数据库恢复所有启用的任务到调度器。"""
        for task in self.db.get_all_tasks():
            if task["enabled"]:
                self._register_job(task)
        self.sync_next_run_times()

    def _register_job(self, task: dict):
        """注册单个任务到调度器。"""
        job_id = str(task["id"])
        try:
            trigger = self._build_trigger(task["trigger_type"], task["trigger_config"])
        except Exception as e:
            print(f"[SchedulerManager] 触发器构建失败 [{task['name']}]: {e}")
            return

        self.scheduler.add_job(
            func=self._job_callback,
            trigger=trigger,
            args=[task["id"]],
            id=job_id,
            replace_existing=True,
            max_instances=task.get("max_instances", 1),
            misfire_grace_time=task.get("misfire_grace", 60),
            coalesce=True,
        )

    def _job_callback(self, task_id: int):
        """APScheduler 作业触发时的回调（运行在调度器线程池中）。

        从 DB 取最新任务定义，保证编辑后立即生效。
        """
        task = self.db.get_task(task_id)
        if task and task["enabled"]:
            self.executor.run_task(task)

    # ── 公开操作 ──────────────────────────────────────────

    def add_or_update(self, task: dict):
        """添加或更新任务调度（任务编辑/创建后调用）。"""
        if task["enabled"]:
            self._register_job(task)
        else:
            self.remove_job(task["id"])
        self.sync_next_run_times()

    def remove_job(self, task_id: int):
        """从调度器移除任务。"""
        try:
            self.scheduler.remove_job(str(task_id))
        except Exception:
            pass  # JobLookupError 等，任务不在调度器中

    def pause_job(self, task_id: int):
        """暂停任务。"""
        try:
            self.scheduler.pause_job(str(task_id))
        except Exception:
            pass

    def resume_job(self, task_id: int):
        """恢复任务。"""
        try:
            self.scheduler.resume_job(str(task_id))
        except Exception:
            pass

    def pause_all(self):
        """暂停整个调度器。"""
        if self._started:
            self.scheduler.pause()

    def resume_all(self):
        """恢复整个调度器。"""
        if self._started:
            self.scheduler.resume()

    def run_now(self, task_id: int):
        """手动触发任务（不走调度器，直接执行）。"""
        task = self.db.get_task(task_id)
        if task:
            self.executor.run_task(task)

    # ── 时间同步 ──────────────────────────────────────────

    def get_next_run_time(self, task_id: int) -> datetime | None:
        """获取指定任务的下一次运行时间。"""
        job = self.scheduler.get_job(str(task_id))
        return job.next_run_time if job else None

    def sync_next_run_times(self):
        """将调度器中的 next_run_time 同步到数据库（供 UI 刷新）。"""
        for task in self.db.get_all_tasks():
            next_run = self.get_next_run_time(task["id"])
            self.db.update_task_times(task["id"], next_run=next_run)

    # ── 触发器构建 ────────────────────────────────────────

    @staticmethod
    def _build_trigger(trigger_type: str, config_str: str):
        """根据类型和 JSON 配置构建 APScheduler 触发器。"""
        config = json.loads(config_str) if config_str else {}
        config = {k: v for k, v in config.items() if v is not None and v != ""}

        if trigger_type == TRIGGER_CRON:
            return CronTrigger(**config)
        elif trigger_type == TRIGGER_INTERVAL:
            return IntervalTrigger(**config)
        elif trigger_type == TRIGGER_DATE:
            if "run_date" in config:
                config["run_date"] = datetime.fromisoformat(config["run_date"])
            return DateTrigger(**config)
        else:
            raise ValueError(f"未知触发器类型: {trigger_type}")

    # ── 显示工具 ──────────────────────────────────────────

    @staticmethod
    def describe_trigger(trigger_type: str, config_str: str) -> str:
        """将触发器配置转为人类可读的调度描述。"""
        try:
            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            return "配置错误"

        if trigger_type == TRIGGER_CRON:
            parts = []
            for field in ("minute", "hour", "day", "month", "day_of_week"):
                val = config.get(field)
                if val is not None and val != "" and val != "*":
                    label = {
                        "minute": "分", "hour": "时",
                        "day": "日", "month": "月", "day_of_week": "周",
                    }[field]
                    parts.append(f"{label}={val}")
            # 如果没有任何明确字段，显示 cron 风格表达式
            if not parts:
                m = config.get("minute", "*")
                h = config.get("hour", "*")
                dom = config.get("day", "*")
                mon = config.get("month", "*")
                dow = config.get("day_of_week", "*")
                return f"{m} {h} {dom} {mon} {dow}"
            return " ".join(parts)

        elif trigger_type == TRIGGER_INTERVAL:
            parts = []
            for unit, label in [("days", "天"), ("hours", "小时"),
                                ("minutes", "分"), ("seconds", "秒")]:
                val = config.get(unit)
                if val:
                    parts.append(f"{val}{label}")
            return f"每{' '.join(parts)}" if parts else "间隔配置缺失"

        elif trigger_type == TRIGGER_DATE:
            run_date = config.get("run_date", "")
            if run_date:
                try:
                    dt = datetime.fromisoformat(run_date)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return str(run_date)
            return "未设置时间"

        return trigger_type
