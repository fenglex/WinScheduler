"""单实例锁：通过 socket 端口绑定实现，无需 pywin32 依赖。"""

import socket

from config import SINGLE_INSTANCE_PORT


class SingleInstance:
    """单实例锁。

    利用 socket.bind 占用本地端口，第二个实例 bind 会失败。
    程序退出时通过 release() 释放。
    """

    def __init__(self):
        self._socket: socket.socket | None = None

    def acquire(self) -> bool:
        """尝试获取锁。成功返回 True，已有实例运行返回 False。"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
            self._socket.listen(1)
            return True
        except OSError:
            self._socket = None
            return False

    def release(self):
        """释放锁。"""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
