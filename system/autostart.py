"""开机自启管理：通过 Windows 注册表实现。"""

import os
import sys

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False


class AutoStart:
    """开机自启管理（注册表方式）。

    写入 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run，
    无需管理员权限，用户级自启。
    """

    REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "WinScheduler"

    @staticmethod
    def _get_command() -> str:
        """获取自启命令行（兼容 PyInstaller）。

        打包后：直接运行 exe；开发模式：python + main.py 完整路径，
        否则注册的是裸 python.exe，开机后不会启动调度器。
        """
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --minimized'
        script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py"))
        return f'"{sys.executable}" "{script}" --minimized'

    @classmethod
    def enable(cls):
        """启用开机自启。"""
        if not _HAS_WINREG:
            raise RuntimeError("winreg 不可用（非 Windows 系统）")
        command = cls._get_command()
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            cls.REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(
                key, cls.APP_NAME, 0, winreg.REG_SZ, command,
            )
        finally:
            winreg.CloseKey(key)

    @classmethod
    def disable(cls):
        """禁用开机自启。"""
        if not _HAS_WINREG:
            return
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            cls.REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, cls.APP_NAME)
        except FileNotFoundError:
            pass  # 值不存在，视为已禁用
        finally:
            winreg.CloseKey(key)

    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否已启用开机自启。"""
        if not _HAS_WINREG:
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REGISTRY_KEY,
                0,
                winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, cls.APP_NAME)
                return True
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            return False
        except OSError:
            return False
