"""公共样式定义

统一全应用的视觉风格。
"""

# 主题色
PRIMARY_COLOR = "#0078d4"  # Windows 蓝
PRIMARY_HOVER = "#106ebe"
PRIMARY_PRESSED = "#005a9e"

DANGER_COLOR = "#e81123"
DANGER_HOVER = "#c50f1f"

SUCCESS_COLOR = "#107c10"
WARNING_COLOR = "#d83b01"

# 文字色
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#666666"
TEXT_MUTED = "#999999"

# 背景色
BG_CARD = "white"
BG_PAGE = "#f5f5f5"
BG_INPUT = "#fafafa"

# 边框
BORDER_LIGHT = "1px solid rgba(0, 0, 0, 0.06)"
BORDER_INPUT = "1px solid #e0e0e0"
BORDER_FOCUS = f"2px solid {PRIMARY_COLOR}"

# 圆角
RADIUS_CARD = "12px"
RADIUS_BUTTON = "6px"
RADIUS_INPUT = "6px"

# 卡片样式
CARD_STYLE = f"""
    background: {BG_CARD};
    border-radius: {RADIUS_CARD};
    border: {BORDER_LIGHT};
"""

# 标题样式
TITLE_STYLE = f"""
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 600;
    background: transparent;
    border: none;
"""

SUBTITLE_STYLE = f"""
    color: {TEXT_SECONDARY};
    font-size: 13px;
    background: transparent;
    border: none;
"""

# 标签样式
LABEL_STYLE = f"""
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    border: none;
"""

LABEL_MUTED_STYLE = f"""
    color: {TEXT_MUTED};
    font-size: 12px;
    background: transparent;
    border: none;
"""

# 关闭按钮样式
CLOSE_BTN_STYLE = f"""
    QPushButton {{
        color: {TEXT_MUTED};
        font-size: 15px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 15px;
    }}
    QPushButton:hover {{
        color: white;
        background: {DANGER_COLOR};
    }}
    QPushButton:pressed {{
        background: {DANGER_HOVER};
    }}
"""

# 链接按钮样式（如"忘记密码"）
LINK_BTN_STYLE = f"""
    color: {PRIMARY_COLOR};
    border: none;
    background: transparent;
    font-size: 13px;
"""

# 危险按钮样式
DANGER_BTN_STYLE = f"""
    PushButton {{
        color: {DANGER_COLOR};
        border: none;
        background: transparent;
        font-size: 13px;
    }}
    PushButton:hover {{
        color: {DANGER_HOVER};
    }}
"""

# 分隔线样式
SEPARATOR_STYLE = """
    background: #e8e8e8;
    border: none;
    max-height: 1px;
"""

# 输入框最小高度
INPUT_MIN_HEIGHT = 38

# 按钮最小高度
BTN_MIN_HEIGHT = 38

# 对话框宽度
DIALOG_WIDTH = 440
