"""开机自启管理：通过 Windows 注册表实现。"""

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
    def _get_exe_path() -> str:
        """获取当前可执行文件路径（兼容 PyInstaller）。"""
        if getattr(sys, "frozen", False):
            return sys.executable
        return sys.executable

    @classmethod
    def enable(cls):
        """启用开机自启。"""
        if not _HAS_WINREG:
            raise RuntimeError("winreg 不可用（非 Windows 系统）")
        exe_path = cls._get_exe_path()
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            cls.REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(
                key, cls.APP_NAME, 0, winreg.REG_SZ,
                f'"{exe_path}" --minimized',
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
