"""类型别名：任务与运行日志均以 dict 形式在各层之间传递。"""

from typing import Any

Task = dict[str, Any]
RunLog = dict[str, Any]
