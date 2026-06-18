"""程序化生成应用图标

生成与登录窗口 🔐 一致的金色挂锁+钥匙图标。
"""

from PyQt5.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush,
    QLinearGradient, QPainterPath,
)
from PyQt5.QtCore import Qt, QPointF


def _create_icon_pixmap(size: int = 256) -> QPixmap:
    """绘制金色挂锁+钥匙图标（与 🔐 一致）"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    s = size
    cx = s / 2.0

    # ── 配色 ──
    gold_light = QColor("#FFD54F")
    gold_mid = QColor("#FFC107")
    gold_dark = QColor("#FF8F00")
    gold_darker = QColor("#E65100")
    key_silver = QColor("#B0BEC5")
    key_silver_dark = QColor("#78909C")
    hole_color = QColor("#5D4037")

    # ── 锁扣（U 形拱门） ──
    shackle_w = s * 0.36
    shackle_h = s * 0.30
    shackle_thick = s * 0.07
    shackle_x = cx - shackle_w / 2
    shackle_y = s * 0.10
    shackle_r = shackle_w / 2

    shackle_grad = QLinearGradient(shackle_x, shackle_y, shackle_x + shackle_w, shackle_y)
    shackle_grad.setColorAt(0.0, gold_dark)
    shackle_grad.setColorAt(0.3, gold_light)
    shackle_grad.setColorAt(0.6, gold_mid)
    shackle_grad.setColorAt(1.0, gold_dark)

    pen = QPen(QBrush(shackle_grad), shackle_thick)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(
        int(shackle_x), int(shackle_y),
        int(shackle_w), int(shackle_h),
        int(shackle_r), int(shackle_r),
    )

    # ── 锁身（圆角矩形） ──
    body_w = s * 0.56
    body_h = s * 0.44
    body_x = cx - body_w / 2
    body_y = s * 0.38
    body_r = s * 0.06

    body_grad = QLinearGradient(body_x, body_y, body_x, body_y + body_h)
    body_grad.setColorAt(0.0, gold_light)
    body_grad.setColorAt(0.4, gold_mid)
    body_grad.setColorAt(1.0, gold_dark)

    # 阴影
    shadow_offset = s * 0.015
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(0, 0, 0, 30)))
    p.drawRoundedRect(
        int(body_x + shadow_offset), int(body_y + shadow_offset),
        int(body_w), int(body_h),
        int(body_r), int(body_r),
    )

    # 锁身主体
    p.setBrush(QBrush(body_grad))
    p.setPen(QPen(gold_darker, s * 0.015))
    p.drawRoundedRect(int(body_x), int(body_y), int(body_w), int(body_h), int(body_r), int(body_r))

    # 锁身高光
    highlight_h = body_h * 0.25
    highlight_grad = QLinearGradient(body_x, body_y, body_x, body_y + highlight_h)
    highlight_grad.setColorAt(0.0, QColor(255, 255, 255, 90))
    highlight_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(highlight_grad))
    p.setPen(Qt.NoPen)
    # 裁剪到锁身范围
    clip_path = QPainterPath()
    clip_path.addRoundedRect(body_x, body_y, body_w, body_h, body_r, body_r)
    p.setClipPath(clip_path)
    p.drawRoundedRect(int(body_x), int(body_y), int(body_w), int(highlight_h), int(body_r), int(body_r))
    p.setClipping(False)

    # ── 锁孔（竖槽 + 圆孔） ──
    hole_cx = cx
    hole_cy = body_y + body_h * 0.42
    hole_r = s * 0.055

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(hole_color))
    p.drawEllipse(
        int(hole_cx - hole_r), int(hole_cy - hole_r),
        int(hole_r * 2), int(hole_r * 2),
    )

    slot_w = s * 0.04
    slot_h = s * 0.10
    p.drawRoundedRect(
        int(hole_cx - slot_w / 2), int(hole_cy),
        int(slot_w), int(slot_h),
        int(slot_w / 2), int(slot_w / 2),
    )

    # ── 钥匙（从锁孔右侧伸出） ──
    key_shaft_y = hole_cy + slot_h * 0.3
    key_start_x = cx + hole_r * 0.6
    key_end_x = cx + s * 0.38
    key_thick = s * 0.035

    # 钥匙杆
    key_grad = QLinearGradient(key_start_x, key_shaft_y - key_thick, key_start_x, key_shaft_y + key_thick)
    key_grad.setColorAt(0.0, key_silver)
    key_grad.setColorAt(0.5, key_silver_dark)
    key_grad.setColorAt(1.0, key_silver)

    key_pen = QPen(QBrush(key_grad), key_thick)
    key_pen.setCapStyle(Qt.RoundCap)
    p.setPen(key_pen)
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(key_start_x, key_shaft_y), QPointF(key_end_x, key_shaft_y))

    # 钥匙齿（两个小横杠）
    tooth_w = s * 0.04
    tooth_thick = s * 0.03
    tooth1_x = key_end_x - s * 0.06
    tooth2_x = key_end_x - s * 0.13

    tooth_pen = QPen(QBrush(key_grad), tooth_thick)
    tooth_pen.setCapStyle(Qt.RoundCap)
    p.setPen(tooth_pen)
    p.drawLine(
        QPointF(tooth1_x, key_shaft_y),
        QPointF(tooth1_x, key_shaft_y + s * 0.06),
    )
    p.drawLine(
        QPointF(tooth2_x, key_shaft_y),
        QPointF(tooth2_x, key_shaft_y + s * 0.045),
    )

    # 钥匙头（圆环）
    key_head_cx = key_end_x + s * 0.01
    key_head_r = s * 0.045
    p.setPen(QPen(key_silver_dark, s * 0.025))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(
        QPointF(key_head_cx, key_shaft_y),
        key_head_r, key_head_r,
    )

    p.end()
    return pixmap


def create_app_icon() -> QIcon:
    """创建应用图标（多尺寸）"""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_create_icon_pixmap(size))
    return icon
