"""生成应用图标文件

运行此脚本生成 assets/icon.ico，供 PyInstaller 打包使用。
用法：python scripts/generate_icon.py
"""

import os
import sys

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, QIODevice, QByteArray, QBuffer

from app.ui.icon_gen import _create_icon_pixmap


def save_as_ico(pixmaps: list[tuple[int, QPixmap]], path: str):
    """将多个 QPixmap 保存为 .ico 文件（Windows 格式）"""
    # ICO 文件头：6 字节
    #   2 bytes: reserved (0)
    #   2 bytes: type (1 = icon)
    #   2 bytes: image count
    # 每个条目：16 字节
    #   1 byte: width, 1 byte: height, 1 byte: colors, 1 byte: reserved
    #   2 bytes: planes, 2 bytes: bpp
    #   4 bytes: data size, 4 bytes: data offset

    images = []
    for size, pm in pixmaps:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        # 保存为 32-bit RGBA PNG
        pm.save(buf, "PNG")
        images.append((size, ba.data()))

    count = len(images)
    header_size = 6 + count * 16
    offset = header_size

    entries = []
    data_blocks = []
    for size, data in images:
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entry = bytes([
            w, h,
            0, 0,  # colors, reserved
        ]) + (1).to_bytes(2, 'little') + (32).to_bytes(2, 'little')  # planes, bpp
        entry += len(data).to_bytes(4, 'little')
        entry += offset.to_bytes(4, 'little')
        entries.append(entry)
        data_blocks.append(data)
        offset += len(data)

    with open(path, 'wb') as f:
        f.write(b'\x00\x00')  # reserved
        f.write((1).to_bytes(2, 'little'))  # type = icon
        f.write(count.to_bytes(2, 'little'))
        for entry in entries:
            f.write(entry)
        for block in data_blocks:
            f.write(block)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    pixmaps = [(sz, _create_icon_pixmap(sz)) for sz in sizes]

    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    ico_path = os.path.join(assets_dir, 'icon.ico')

    save_as_ico(pixmaps, ico_path)
    print(f"图标已生成：{ico_path}")

    # 同时保存 PNG 版本
    png_path = os.path.join(assets_dir, 'icon.png')
    _create_icon_pixmap(256).save(png_path, "PNG")
    print(f"PNG 图标：{png_path}")


if __name__ == "__main__":
    main()
