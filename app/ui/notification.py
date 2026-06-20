"""统一通知组件

所有通知使用此模块，确保样式、位置、动画一致。
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


def show_toast(parent, message, level="info", duration=2500):
    """显示通知

    Args:
        parent: 父窗口
        message: 通知内容
        level: "info" / "warn" / "error"
        duration: 显示时长（毫秒）
    """
    colors = {
        "info": "rgba(50,50,50,200)",
        "error": "rgba(232,17,35,200)",
        "warn": "rgba(216,59,1,200)",
    }
    bg = colors.get(level, colors["info"])

    # 截断过长文字
    display = message if len(message) <= 30 else message[:30] + "..."

    label = QLabel(parent)
    label.setText(display)
    label.setFont(QFont("Microsoft YaHei", 11))
    label.setAlignment(Qt.AlignCenter)
    label.adjustSize()
    label.setFixedSize(label.width() + 32, 38)
    label.setStyleSheet(f"* {{ background: {bg}; color: white; border-radius: 8px; }}")

    # 定位：右上角
    label.move(parent.width() - label.width() - 16, 12)
    label.raise_()
    label.show()

    # 淡入动画
    label.setWindowOpacity(0.0)
    fade_in = QPropertyAnimation(label, b"windowOpacity")
    fade_in.setDuration(150)
    fade_in.setStartValue(0.0)
    fade_in.setEndValue(1.0)
    fade_in.setEasingCurve(QEasingCurve.OutCubic)
    fade_in.start()
    label._fade_in = fade_in  # 保持引用

    # 定时后淡出并销毁
    def fade_out():
        fade_anim = QPropertyAnimation(label, b"windowOpacity")
        fade_anim.setDuration(200)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.InCubic)
        fade_anim.finished.connect(label.deleteLater)
        fade_anim.start()
        label._fade_out = fade_anim  # 保持引用

    QTimer.singleShot(duration, fade_out)
