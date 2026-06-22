"""公共样式定义"""

import os
import sys


def get_combo_style() -> str:
    """获取带正确箭头路径的下拉框样式"""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    arrow_path = os.path.join(base, 'assets', 'arrow.png').replace('\\', '/')
    return COMBO_STYLE.replace('%ARROW_PATH%', arrow_path)

PRIMARY_COLOR = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
PRIMARY_PRESSED = "#1e40af"
DANGER_COLOR = "#dc2626"
SUCCESS_COLOR = "#16a34a"
WARNING_COLOR = "#ea580c"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#4b5563"
TEXT_MUTED = "#9ca3af"
BG_CARD = "white"
BG_PAGE = "#f8fafc"

INPUT_STYLE = """
    QLineEdit, QTextEdit {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        background: white;
        color: #111827;
        selection-background-color: #bfdbfe;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 2px solid #2563eb;
    }
"""

COMBO_STYLE = """
    QComboBox {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 8px 12px;
        padding-right: 36px;
        font-size: 13px;
        background: white;
        color: #111827;
        min-height: 20px;
    }
    QComboBox:focus {
        border: 2px solid #2563eb;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 32px;
        border: none;
        border-left: 1px solid #eee;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        background: transparent;
    }
    QComboBox::drop-down:hover {
        background: #f5f5f5;
    }
    QComboBox::down-arrow {
        image: url(%ARROW_PATH%);
        width: 12px;
        height: 12px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: white;
        outline: none;
        padding: 6px;
    }
    QComboBox QAbstractItemView::item {
        height: 40px;
        padding: 0 14px;
        border-radius: 6px;
        margin: 2px 4px;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #e8f0fe;
        color: #0078d4;
    }
    QComboBox QAbstractItemView::item:hover {
        background: #f5f5f5;
    }
"""

GROUP_LIST_STYLE = """
    QListWidget, QListView {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: white;
        outline: none;
        padding: 4px;
    }
    QListWidget::item, QListView::item {
        height: 40px;
        padding: 0 14px;
        border-radius: 6px;
        margin: 2px 4px;
        border: none;
        outline: none;
    }
    QListWidget::item:selected, QListView::item:selected {
        background: #e8f0fe;
        color: #0078d4;
        border: none;
        outline: none;
    }
    QListWidget::item:hover, QListView::item:hover {
        background: #f5f5f5;
        border: none;
        outline: none;
    }
"""

ICON_BTN_STYLE = """
    QToolButton {
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 4px;
        font-size: 14px;
        color: #888;
    }
    QToolButton:hover {
        background: #f0f0f0;
        color: #333;
    }
    QToolButton:pressed {
        background: #e0e0e0;
    }
"""

PRIMARY_BTN_STYLE = """
    QPushButton {
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover { background: #1d4ed8; }
    QPushButton:pressed { background: #1e40af; }
    QPushButton:disabled { background: #9ca3af; color: #e5e7eb; }
"""

BTN_STYLE = """
    QPushButton {
        background: #f3f4f6;
        color: #111827;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 13px;
    }
    QPushButton:hover { background: #e5e7eb; }
    QPushButton:pressed { background: #d1d5db; }
"""

LINK_BTN_STYLE = """
    QPushButton {
        color: #2563eb;
        border: none;
        background: transparent;
        font-size: 13px;
    }
    QPushButton:hover { text-decoration: underline; }
"""

DANGER_BTN_STYLE = """
    QPushButton {
        color: #dc2626;
        border: none;
        background: transparent;
        font-size: 13px;
    }
    QPushButton:hover { text-decoration: underline; }
"""

CLOSE_BTN_STYLE = """
    QPushButton {
        color: #9ca3af;
        font-size: 15px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 15px;
    }
    QPushButton:hover { color: white; background: #ef4444; }
"""

CARD_STYLE = "background: white; border-radius: 12px; border: 1px solid #e5e7eb;"

LABEL_STYLE = "color: #111827; font-size: 13px; font-weight: 500; background: transparent; border: none;"
LABEL_MUTED_STYLE = "color: #9ca3af; font-size: 12px; background: transparent; border: none;"

INPUT_MIN_HEIGHT = 38
BTN_MIN_HEIGHT = 38
DIALOG_WIDTH = 440
