"""日志收集器：解析级别、格式化、颜色映射。"""

import re

from config import LOG_COLORS


class LogCollector:
    """日志级别识别与格式化工具。

    通过正则匹配 stdout 内容中的关键词判定日志级别，
    退出码 0 且无错误关键词时判定为 INFO/SUCCESS。
    """

    LEVEL_PATTERNS = {
        "ERROR": re.compile(
            r"\b(error|exception|traceback|fatal|failed|failure|critical)\b",
            re.IGNORECASE,
        ),
        "WARN": re.compile(
            r"\b(warn|warning|deprecated|caution)\b",
            re.IGNORECASE,
        ),
        "DEBUG": re.compile(r"\b(debug|verbose)\b", re.IGNORECASE),
    }

    @classmethod
    def parse_level(cls, line: str, exit_code: int | None = None,
                    is_final: bool = False) -> str:
        """识别单行日志级别。

        Args:
            line: 日志文本行。
            exit_code: 退出码（仅 is_final 时有意义）。
            is_final: 是否为任务结束的最终判定。
        """
        if is_final:
            if exit_code is not None and exit_code != 0:
                return "ERROR"
            return "SUCCESS"
        if cls.LEVEL_PATTERNS["ERROR"].search(line):
            return "ERROR"
        if cls.LEVEL_PATTERNS["WARN"].search(line):
            return "WARN"
        if cls.LEVEL_PATTERNS["DEBUG"].search(line):
            return "DEBUG"
        return "INFO"

    @classmethod
    def format_line(cls, timestamp: str, task_name: str, level: str, line: str) -> str:
        """格式化日志行：[时间] [级别] [任务名] 内容。"""
        return f"[{timestamp}] [{level:>5s}] [{task_name}] {line}"

    @classmethod
    def get_color(cls, level: str) -> str:
        """获取级别对应的十六进制颜色。"""
        return LOG_COLORS.get(level, LOG_COLORS["INFO"])
