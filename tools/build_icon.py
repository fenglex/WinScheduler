"""生成 Windows 应用图标 app.ico（多尺寸 PNG-in-ICO）。

不依赖 Pillow：复用 ui/icons._make_pixmap 程序化绘制主图标，
按 Vista+ 标准把多张 PNG 直接嵌入 ICO 容器。Windows 资源管理器
会按当前显示场景自动选择合适分辨率。

用法：
    python tools/build_icon.py                 # 默认输出到 app.ico
    python tools/build_icon.py path/to/out.ico # 自定义路径

依赖：PySide6（项目本身就装这个）。
"""

import os
import struct
import sys

# 让脚本既能 `python tools/build_icon.py` 跑，也能从任意位置 import
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from ui.icons import _make_pixmap

# ICO 内置的标准尺寸（覆盖任务栏、桌面、Alt-Tab、高 DPI）
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _pixmap_to_png_bytes(pixmap) -> bytes:
    """把 QPixmap 编码为 PNG 字节流。"""
    img: QImage = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(buf.data())


def build_ico(output_path: str) -> int:
    """生成多尺寸 ICO 文件，返回写入字节数。"""
    # QApplication 必须在 QPixmap 绘制前实例化（offscreen 即可）
    _app = QApplication.instance() or QApplication(sys.argv)

    pngs: list[tuple[int, bytes]] = []
    for size in ICON_SIZES:
        pm = _make_pixmap(size)
        pngs.append((size, _pixmap_to_png_bytes(pm)))

    # ── 写 ICO 容器 ────────────────────────────────
    # 头部：6 字节
    header = struct.pack("<HHH", 0, 1, len(pngs))
    # 目录条目：每张 16 字节，紧跟头部
    data_offset = 6 + 16 * len(pngs)
    directory = b""
    image_data = b""
    for size, png in pngs:
        # 256 在字节里用 0 表示（0 实际是 256）
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        directory += struct.pack(
            "<BBBBHHII",
            w, h,         # Width, Height
            0,            # ColorCount（>256 色时为 0）
            0,            # Reserved
            1,            # ColorPlanes
            32,           # BitCount
            len(png),     # ImageSize
            data_offset,  # ImageOffset
        )
        image_data += png
        data_offset += len(png)

    blob = header + directory + image_data

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(blob)

    print(f"[OK] 生成图标: {output_path}")
    print(f"     尺寸: {', '.join(f'{s}x{s}' for s in ICON_SIZES)}")
    print(f"     大小: {len(blob):,} 字节 ({len(blob) / 1024:.1f} KB)")
    return len(blob)


def main() -> int:
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        out = os.path.join(_PROJECT_DIR, "app.ico")
    return 0 if build_ico(out) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
