"""任务执行器：在子线程中运行外部命令，实时采集 stdout/stderr。

线程模型：
  - TaskExecutor 是 QObject，生命周期在主线程。
  - 每个任务在一个独立的 threading.Thread 中执行 subprocess。
  - 日志/状态通过 Qt 信号发射（跨线程自动走 QueuedConnection）。
  - 数据库写入在工作线程中完成（SQLAlchemy check_same_thread=False + WAL）。
"""

import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from config import COMMAND_POWERSHELL

from core.log_collector import LogCollector
from database.manager import DatabaseManager


@dataclass
class RunningTask:
    """一次任务运行的运行时上下文。"""

    task_id: int
    task_name: str
    log_id: int
    started_at: datetime
    process: subprocess.Popen | None = None
    thread: threading.Thread | None = None
    log_buffer: list[str] = field(default_factory=list)
    timed_out: bool = False
    killed: bool = False


class TaskExecutor(QObject):
    """管理子进程执行，采集输出，发射信号。"""

    # ── 信号 ──────────────────────────────────────────────
    # (task_id, task_name, level, formatted_line)
    log_line = Signal(int, str, str, str)
    # (task_id, task_name)
    task_started = Signal(int, str)
    # (task_id, exit_code, status, duration)
    task_finished = Signal(int, int, str, float)

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self._running: dict[int, RunningTask] = {}
        self._lock = threading.Lock()

    # ── 公开接口 ──────────────────────────────────────────

    def run_task(self, task: dict):
        """执行任务（可从 APScheduler 线程或主线程调用）。"""
        task_id = task["id"]
        with self._lock:
            if task_id in self._running:
                return  # 已在运行，跳过（受 max_instances 语义控制）

        started_at = datetime.now()
        log_id = self.db.create_run_log(task_id, started_at)

        rt = RunningTask(
            task_id=task_id,
            task_name=task["name"],
            log_id=log_id,
            started_at=started_at,
        )

        with self._lock:
            self._running[task_id] = rt

        # 发射开始信号 + 起始日志
        self.task_started.emit(task_id, task["name"])
        ts = started_at.strftime("%H:%M:%S")
        start_line = LogCollector.format_line(ts, task["name"], "INFO",
                                              f"开始执行: {task['command']}")
        self.log_line.emit(task_id, task["name"], "INFO", start_line)
        rt.log_buffer.append(start_line)

        thread = threading.Thread(target=self._worker, args=(task, rt), daemon=True)
        rt.thread = thread
        thread.start()

    def stop_task(self, task_id: int):
        """终止指定任务。"""
        with self._lock:
            rt = self._running.get(task_id)
        if rt and rt.process:
            rt.killed = True
            self._kill_process_tree(rt.process)

    def is_running(self, task_id: int) -> bool:
        with self._lock:
            return task_id in self._running

    def get_running_count(self) -> int:
        with self._lock:
            return len(self._running)

    def get_running_task_ids(self) -> list[int]:
        with self._lock:
            return list(self._running.keys())

    def stop_all(self, timeout: float = 5.0):
        """停止所有正在运行的任务（程序退出时调用）。"""
        with self._lock:
            rts = list(self._running.values())
        for rt in rts:
            rt.killed = True
            if rt.process:
                self._kill_process_tree(rt.process)
        # 等待工作线程结束
        for rt in rts:
            if rt.thread:
                rt.thread.join(timeout=timeout)

    @staticmethod
    def _kill_process_tree(process: subprocess.Popen):
        """终止进程及其所有子进程。

        Windows 上用 taskkill /F /T 杀死整个进程树，
        避免 shell=True 时 cmd.exe 被杀但子进程（如 python.exe）仍在运行。
        """
        if process.poll() is not None:
            return  # 进程已退出
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10,
                )
            else:
                import signal
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass

    # ── 工作线程 ──────────────────────────────────────────

    def _worker(self, task: dict, rt: RunningTask):
        """线程入口：启动子进程，逐行读取输出。"""
        try:
            self._execute(task, rt)
        except FileNotFoundError as e:
            err = LogCollector.format_line(
                datetime.now().strftime("%H:%M:%S"),
                rt.task_name, "ERROR",
                f"工作目录不存在: {e}",
            )
            self.log_line.emit(rt.task_id, rt.task_name, "ERROR", err)
            rt.log_buffer.append(err)
            self._finish(rt, exit_code=-1, status="failed")
        except Exception as e:
            err = LogCollector.format_line(
                datetime.now().strftime("%H:%M:%S"),
                rt.task_name, "ERROR",
                f"任务执行异常: {e}",
            )
            self.log_line.emit(rt.task_id, rt.task_name, "ERROR", err)
            rt.log_buffer.append(err)
            self._finish(rt, exit_code=-1, status="failed")

    def _execute(self, task: dict, rt: RunningTask):
        """执行子进程并采集输出。"""
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        cwd = task.get("work_dir") or None
        command_type = task.get("command_type", "shell")
        script_path: str | None = None

        # ── 构造 Popen 参数 ────────────────────────────────
        if command_type == COMMAND_POWERSHELL:
            # PowerShell 脚本：写入临时 .ps1 文件后执行
            fd, script_path = tempfile.mkstemp(suffix=".ps1", prefix="task_pilot_")
            with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
                # 强制 UTF-8 输出，配合 subprocess encoding="utf-8"
                f.write("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n")
                f.write(task["command"])

            popen_args = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
            ]
            use_shell = False
        else:
            # Shell 命令：直接交给 cmd.exe（shell=True）
            popen_args = task["command"]
            use_shell = True

        try:
            rt.process = subprocess.Popen(
                popen_args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # 合并 stderr 到 stdout
                text=True,
                bufsize=1,                  # 行缓冲
                encoding="utf-8",
                errors="replace",
                shell=use_shell,
                creationflags=creation_flags,
            )

            # 超时定时器
            timer = None
            timeout = task.get("timeout", 0)
            if timeout and timeout > 0:
                def _on_timeout():
                    rt.timed_out = True
                    self._kill_process_tree(rt.process)

                timer = threading.Timer(timeout, _on_timeout)
                timer.start()

            try:
                assert rt.process.stdout is not None
                for raw_line in rt.process.stdout:
                    line = raw_line.rstrip("\r\n")
                    if not line:
                        continue
                    level = LogCollector.parse_level(line)
                    ts = datetime.now().strftime("%H:%M:%S")
                    formatted = LogCollector.format_line(ts, rt.task_name, level, line)
                    self.log_line.emit(rt.task_id, rt.task_name, level, formatted)
                    rt.log_buffer.append(formatted)
            finally:
                if timer:
                    timer.cancel()

            rt.process.wait()
            exit_code = rt.process.returncode
        finally:
            # 清理 PowerShell 临时文件
            if script_path:
                try:
                    os.unlink(script_path)
                except OSError:
                    pass

        # 判定状态
        if rt.killed:
            status = "killed"
        elif rt.timed_out:
            status = "timeout"
        elif exit_code == 0:
            status = "success"
        else:
            status = "failed"

        self._finish(rt, exit_code, status)

    def _finish(self, rt: RunningTask, exit_code: int, status: str):
        """任务结束处理：发射信号、写库、清理。"""
        finished_at = datetime.now()
        duration = (finished_at - rt.started_at).total_seconds()

        # 结束日志
        ts = finished_at.strftime("%H:%M:%S")
        level = LogCollector.parse_level("", exit_code, is_final=True)
        end_msg = f"任务结束，退出码: {exit_code}，耗时: {duration:.1f}s，状态: {status}"
        end_line = LogCollector.format_line(ts, rt.task_name, level, end_msg)
        self.log_line.emit(rt.task_id, rt.task_name, level, end_line)
        rt.log_buffer.append(end_line)

        # 发射完成信号
        self.task_finished.emit(rt.task_id, exit_code, status, duration)

        # 持久化
        log_content = "\n".join(rt.log_buffer)
        self.db.finish_run_log(rt.log_id, finished_at, exit_code, status, duration, log_content)
        self.db.update_task_times(rt.task_id, last_run=finished_at, status=status)

        # 清理运行时状态
        with self._lock:
            self._running.pop(rt.task_id, None)
