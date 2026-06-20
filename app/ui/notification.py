"""统一通知组件

滑入/滑出动画，半透明背景，视觉一致。
"""

from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QColor


# 通知队列（防止被 GC）
_active = []


def show_toast(parent, message, level="info", duration=2500):
    """显示通知（从右侧滑入，定时后滑出）

    Args:
        parent: 父窗口
        message: 通知内容
        level: "info" / "warn" / "error"
        duration: 显示时长（毫秒）
    """
    colors = {
        "info": ("rgba(40,40,40,210)", "#fff"),
        "error": ("rgba(200,30,30,210)", "#fff"),
        "warn": ("rgba(200,100,10,210)", "#fff"),
    }
    bg, fg = colors.get(level, colors["info"])

    display = message if len(message) <= 28 else message[:28] + "..."

    label = QLabel(display, parent)
    label.setFont(QFont("Microsoft YaHei", 11))
    label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    label.setStyleSheet(f"""
        * {{
            background: {bg};
            color: {fg};
            border-radius: 8px;
            padding: 0 16px;
        }}
    """)
    label.adjustSize()
    label.setFixedSize(label.width() + 20, 38)

    # 阴影
    shadow = QGraphicsDropShadowEffect(label)
    shadow.setBlurRadius(16)
    shadow.setOffset(0, 2)
    shadow.setColor(QColor(0, 0, 0, 60))
    label.setGraphicsEffect(shadow)

    # 起止位置
    end_x = parent.width() - label.width() - 16
    end_y = 14
    start_x = parent.width() + 10
    label.move(start_x, end_y)
    label.raise_()
    label.show()

    _active.append(label)

    # 滑入动画
    slide_in = QPropertyAnimation(label, b"pos")
    slide_in.setDuration(250)
    slide_in.setStartValue(QPoint(start_x, end_y))
    slide_in.setEndValue(QPoint(end_x, end_y))
    slide_in.setEasingCurve(QEasingCurve.OutCubic)
    slide_in.start()
    label._anim_in = slide_in

    # 定时后滑出
    def slide_out():
        slide = QPropertyAnimation(label, b"pos")
        slide.setDuration(250)
        slide.setStartValue(QPoint(end_x, end_y))
        slide.setEndValue(QPoint(start_x, end_y))
        slide.setEasingCurve(QEasingCurve.InCubic)
        slide.finished.connect(lambda: _cleanup(label))
        slide.start()
        label._anim_out = slide

    QTimer.singleShot(duration, slide_out)


def _cleanup(label):
    """清理通知"""
    if label in _active:
        _active.remove(label)
    label.deleteLater()
