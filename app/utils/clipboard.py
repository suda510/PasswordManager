"""剪贴板操作封装

复制密码后 30 秒自动清除剪贴板。
"""

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

CLEAR_DELAY_MS = 30_000

_timer: QTimer = None


def _get_timer() -> QTimer:
    global _timer
    if _timer is None:
        _timer = QTimer()
        _timer.setSingleShot(True)
        _timer.timeout.connect(_clear)
    return _timer


def _clear():
    clipboard = QApplication.clipboard()
    if clipboard:
        clipboard.clear()


def copy_to_clipboard(text: str, auto_clear: bool = True):
    clipboard = QApplication.clipboard()
    if clipboard:
        clipboard.setText(text)
    if auto_clear:
        _get_timer().start(CLEAR_DELAY_MS)
