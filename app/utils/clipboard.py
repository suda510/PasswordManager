"""剪贴板操作封装"""

from PyQt5.QtWidgets import QApplication


def copy_to_clipboard(text: str) -> None:
    """复制文本到系统剪贴板

    Args:
        text: 要复制的文本
    """
    clipboard = QApplication.clipboard()
    if clipboard:
        clipboard.setText(text)
