"""公共样式定义"""

PRIMARY_COLOR = "#0078d4"
PRIMARY_HOVER = "#106ebe"
PRIMARY_PRESSED = "#005a9e"
DANGER_COLOR = "#e81123"
SUCCESS_COLOR = "#107c10"
WARNING_COLOR = "#d83b01"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#666666"
TEXT_MUTED = "#999999"
BG_CARD = "white"
BG_PAGE = "#f5f5f5"

INPUT_STYLE = """
    QLineEdit, QTextEdit {
        border: 1px solid #ddd;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        background: white;
        color: #1a1a1a;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 2px solid #0078d4;
    }
"""

COMBO_STYLE = """
    QComboBox {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 12px;
        padding-right: 36px;
        font-size: 13px;
        background: white;
        color: #1a1a1a;
        min-height: 20px;
    }
    QComboBox:focus {
        border: 2px solid #0078d4;
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
        height: 44px;
        padding: 0 14px;
        border-radius: 8px;
        margin: 2px 0;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #e8f0fe;
        color: #0078d4;
        border-left: 3px solid #0078d4;
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
        margin: 1px 2px;
    }
    QListWidget::item:selected, QListView::item:selected {
        background: #e8f0fe;
        color: #0078d4;
    }
    QListWidget::item:hover, QListView::item:hover {
        background: #f5f5f5;
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
        background: #0078d4;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover { background: #106ebe; }
    QPushButton:pressed { background: #005a9e; }
    QPushButton:disabled { background: #ccc; }
"""

BTN_STYLE = """
    QPushButton {
        background: #f0f0f0;
        color: #1a1a1a;
        border: 1px solid #ddd;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
    }
    QPushButton:hover { background: #e5e5e5; }
    QPushButton:pressed { background: #d9d9d9; }
"""

LINK_BTN_STYLE = """
    QPushButton {
        color: #0078d4;
        border: none;
        background: transparent;
        font-size: 13px;
    }
    QPushButton:hover { text-decoration: underline; }
"""

DANGER_BTN_STYLE = """
    QPushButton {
        color: #e81123;
        border: none;
        background: transparent;
        font-size: 13px;
    }
    QPushButton:hover { text-decoration: underline; }
"""

CLOSE_BTN_STYLE = """
    QPushButton {
        color: #999;
        font-size: 15px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 15px;
    }
    QPushButton:hover { color: white; background: #e81123; }
"""

CARD_STYLE = "background: white; border-radius: 10px; border: 1px solid rgba(0,0,0,0.06);"

LABEL_STYLE = "color: #1a1a1a; font-size: 13px; font-weight: 500; background: transparent; border: none;"
LABEL_MUTED_STYLE = "color: #999; font-size: 12px; background: transparent; border: none;"

INPUT_MIN_HEIGHT = 38
BTN_MIN_HEIGHT = 38
DIALOG_WIDTH = 440
