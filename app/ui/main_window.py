"""主界面窗口（纯原生 PyQt5）

使用 QMainWindow + QToolBar 实现现代风格。
"""

import hashlib
import html as html_mod
import re

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QGraphicsDropShadowEffect,
    QStackedLayout,
    QToolButton,
    QComboBox,
    QPushButton,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor

from app.core.db import Database
from app.core.models import Entry
from app.core.config_manager import ConfigManager
from app.ui.dialogs import AddEditDialog, confirm_delete
from app.ui.main_dialogs import (
    show_manage_groups,
    show_export_dialog,
    show_change_password_dialog,
    show_about_dialog,
)
from app.ui.styles import (
    LABEL_STYLE,
    INPUT_STYLE,
    ICON_BTN_STYLE,
    GROUP_LIST_STYLE,
    PRIMARY_BTN_STYLE,
    BTN_STYLE,
    CARD_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
    BG_PAGE,
    get_combo_style,
)
from app.utils.clipboard import copy_to_clipboard
from app.ui.icon_gen import create_copy_icon, create_eye_icon


# ── 首字母头像配色 ──
AVATAR_COLORS = [
    "#0078d4", "#107c10", "#d83b01", "#b4009e",
    "#008575", "#004e8c", "#8764b8", "#c30052",
    "#e3008c", "#7a7574", "#767676", "#0063b1",
]


def _avatar_color(text: str) -> str:
    """根据文本生成稳定的头像背景色"""
    idx = int(hashlib.md5(text.encode()).hexdigest(), 16) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


from app.ui.notification import show_toast as _toast, confirm_dialog as _confirm


def _first_char(text: str) -> str:
    """取首字符（中文取第一个字，英文取首字母大写）"""
    if not text:
        return "?"
    ch = text[0]
    return ch.upper() if ch.isascii() else ch


class EntryCardWidget(QFrame):
    """条目卡片组件：左侧头像 + 右侧标题/用户名"""

    def __init__(self, entry: Entry, keyword: str = "", parent=None):
        super().__init__(parent)
        self._entry = entry
        self._keyword = keyword
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(selected=False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)

        # ── 首字母头像 ──
        avatar = QLabel(_first_char(self._entry.title))
        avatar.setFixedSize(38, 38)
        avatar.setAlignment(Qt.AlignCenter)
        color = _avatar_color(self._entry.title)
        avatar.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        avatar.setStyleSheet(f"""
            QLabel {{
                background: {color};
                color: white;
                border-radius: 19px;
                border: none;
            }}
        """)
        layout.addWidget(avatar)

        # ── 文字区域 ──
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        # 标题（支持搜索高亮）
        title_text = self._entry.title
        if self._keyword and self._keyword.lower() in title_text.lower():
            highlighted = self._highlight(title_text, self._keyword)
            title_label = QLabel(highlighted)
        else:
            title_label = QLabel(title_text)
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.DemiBold))
        title_label.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        text_layout.addWidget(title_label)

        user_label = QLabel(self._entry.username or "（无用户名）")
        user_label.setFont(QFont("Microsoft YaHei", 10))
        user_label.setStyleSheet("color: #999; background: transparent; border: none;")
        text_layout.addWidget(user_label)

        layout.addLayout(text_layout, stretch=1)

    @staticmethod
    def _highlight(text: str, keyword: str) -> str:
        """高亮关键词"""
        pattern = re.escape(keyword)
        return re.sub(
            pattern,
            lambda m: f'<span style="background:#fff3cd; color:#856404; border-radius:2px; padding:0 2px;">{m.group()}</span>',
            text,
            flags=re.IGNORECASE,
        )

    def _update_style(self, selected: bool):
        """更新卡片样式（选中/未选中）"""
        if selected:
            self.setStyleSheet("""
                QFrame {
                    background: #e8f0fe;
                    border: none;
                    border-left: 3px solid #2563eb;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 6px;
                }
                QFrame:hover {
                    background: rgba(0, 0, 0, 0.04);
                }
            """)


class MainWindow(QMainWindow):
    """主窗口"""

    logout = pyqtSignal()

    def __init__(self, db: Database, config: ConfigManager):
        super().__init__()
        self._db = db
        self._config = config
        self._current_entry = None
        self._card_widgets = {}
        self._password_visible = False
        self._search_debounce = QTimer()
        self._search_debounce.setSingleShot(True)
        self._search_debounce.timeout.connect(self._do_search)
        self._setup_ui()
        self._load_entries()

    def moveEvent(self, event):
        """主窗口移动时关闭下拉框"""
        if hasattr(self, '_group_combo') and self._group_combo._popup:
            self._group_combo._popup.close()
        super().moveEvent(event)

    def _setup_ui(self):
        self.setWindowTitle("密码管理器")
        self.resize(960, 640)
        self.setMinimumSize(760, 480)
        self.setStyleSheet(f"background: {BG_PAGE};")

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 主背景渐变
        central.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8f9fa, stop:1 #e9ecef);
        """)

        # 主内容区
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 12, 20, 12)
        content_layout.setSpacing(16)

        # 左侧面板
        left_panel = self._create_left_panel()
        # 2. 左侧卡片阴影
        left_shadow = QGraphicsDropShadowEffect()
        left_shadow.setBlurRadius(20)
        left_shadow.setOffset(0, 2)
        left_shadow.setColor(QColor(0, 0, 0, 25))
        left_panel.setGraphicsEffect(left_shadow)
        content_layout.addWidget(left_panel, stretch=1)

        # 右侧面板
        right_panel = self._create_right_panel()
        # 2. 右侧卡片阴影
        right_shadow = QGraphicsDropShadowEffect()
        right_shadow.setBlurRadius(20)
        right_shadow.setOffset(0, 2)
        right_shadow.setColor(QColor(0, 0, 0, 25))
        right_panel.setGraphicsEffect(right_shadow)
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addWidget(content, stretch=1)

        # 底部按钮栏
        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(20, 8, 20, 12)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)

        # 7. 底部按钮带图标
        btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                color: #1a1a1a;
            }
            QPushButton:hover { background: #f0f0f0; }
        """

        for text, handler in [
            ("导出数据", self._on_export),
            ("修改主密码", self._on_change_password),
            ("锁定", self._on_lock),
            ("关于", self._on_about),
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(handler)
            card_layout.addWidget(btn)

        bottom_layout.addWidget(card)
        main_layout.addWidget(bottom)

    def _create_left_panel(self) -> QWidget:
        """创建左侧面板：搜索 + 分组 + 列表 + 按钮"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索网站/软件名...")
        self._search_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._search_input.setStyleSheet(INPUT_STYLE)
        self._search_input.textChanged.connect(self._on_search)
        left_layout.addWidget(self._search_input)

        # 分组下拉框 + 管理按钮
        group_row = QHBoxLayout()
        group_row.setSpacing(8)

        class AutoWidthCombo(QComboBox):
            """下拉宽度与控件宽度一致，四角圆角"""
            _popup = None

            def showPopup(self):
                # 已打开则关闭（切换行为）
                if self._popup and self._popup.isVisible():
                    self._popup.close()
                    return

                from PyQt5.QtWidgets import QListWidget, QListWidgetItem

                popup = QWidget(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
                popup.setAttribute(Qt.WA_TranslucentBackground)
                popup.setFocusPolicy(Qt.NoFocus)
                self._popup = popup

                layout = QVBoxLayout(popup)
                layout.setContentsMargins(0, 0, 0, 0)

                listw = QListWidget()
                listw.setStyleSheet("""
                    QListWidget {
                        background: white;
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                        padding: 4px;
                        outline: none;
                    }
                    QListWidget::item {
                        height: 40px;
                        padding: 0 14px;
                        border-radius: 6px;
                        margin: 2px 4px;
                    }
                    QListWidget::item:selected { background: #dbeafe; color: #2563eb; }
                    QListWidget::item:hover { background: #f5f5f5; }
                """)

                for i in range(self.count()):
                    item = QListWidgetItem(self.itemText(i))
                    item.setData(Qt.UserRole, i)
                    listw.addItem(item)

                if self.currentIndex() >= 0:
                    listw.setCurrentRow(self.currentIndex())

                def on_select(item):
                    self.setCurrentIndex(item.data(Qt.UserRole))
                    popup.close()

                listw.itemClicked.connect(on_select)
                layout.addWidget(listw)

                h = min(listw.sizeHintForRow(0) * self.count() + 12, 300)
                w = self.width()
                popup.setFixedSize(w, h)

                pos = self.mapToGlobal(self.rect().bottomLeft())
                popup.move(pos.x(), pos.y() + 2)
                popup.show()

                # 点击外部关闭
                def on_focus_change(old, new):
                    if new is None or not popup.isAncestorOf(new):
                        popup.close()
                        QApplication.instance().focusChanged.disconnect(on_focus_change)

                QApplication.instance().focusChanged.connect(on_focus_change)

            def closePopup(self):
                if self._popup:
                    self._popup.close()
                super().closePopup()

        self._group_combo = AutoWidthCombo()
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.setStyleSheet(get_combo_style())
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        group_row.addWidget(self._group_combo, stretch=1)

        group_manage_btn = QPushButton("管理分组")
        group_manage_btn.setFixedHeight(INPUT_MIN_HEIGHT)
        group_manage_btn.setStyleSheet(BTN_STYLE)
        group_manage_btn.clicked.connect(self._on_manage_groups)
        group_row.addWidget(group_manage_btn)
        left_layout.addLayout(group_row)

        self._current_group = ""
        self._refresh_groups()

        # 列表卡片
        list_card = QFrame()
        list_card.setStyleSheet(f"""
            QFrame {{
                {CARD_STYLE}
            }}
        """)
        list_shadow = QGraphicsDropShadowEffect()
        list_shadow.setBlurRadius(16)
        list_shadow.setOffset(0, 2)
        list_shadow.setColor(QColor(0, 0, 0, 20))
        list_card.setGraphicsEffect(list_shadow)

        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self._entry_list = QListWidget()
        self._entry_list.currentItemChanged.connect(self._on_entry_selected)
        self._entry_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 2px 6px;
                border: none;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        list_layout.addWidget(self._entry_list)
        left_layout.addWidget(list_card)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_template = """
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {hover}; }}
        """
        self._add_btn = QPushButton("新增")
        self._add_btn.setStyleSheet(btn_template.format(
            bg="#e3f2fd", fg="#1565c0", border="#bbdefb", hover="#bbdefb"))
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setStyleSheet(btn_template.format(
            bg="#e8f5e9", fg="#2e7d32", border="#c8e6c9", hover="#c8e6c9"))
        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet(btn_template.format(
            bg="#ffebee", fg="#c62828", border="#ffcdd2", hover="#ffcdd2"))
        for btn in (self._add_btn, self._edit_btn, self._delete_btn):
            btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._add_btn)
        btn_layout.addWidget(self._edit_btn)
        btn_layout.addWidget(self._delete_btn)
        left_layout.addLayout(btn_layout)

        return left_panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧面板：详情卡片"""
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                {CARD_STYLE}
            }}
        """)
        right_shadow = QGraphicsDropShadowEffect()
        right_shadow.setBlurRadius(16)
        right_shadow.setOffset(0, 2)
        right_shadow.setColor(QColor(0, 0, 0, 20))
        right_panel.setGraphicsEffect(right_shadow)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ── 顶部标题栏（带头像） ──
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 24, 28, 20)
        header_layout.setSpacing(14)

        self._detail_avatar = QLabel("?")
        self._detail_avatar.setFixedSize(44, 44)
        self._detail_avatar.setAlignment(Qt.AlignCenter)
        self._detail_avatar.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self._detail_avatar.setStyleSheet("""
            QLabel {
                background: #e0e0e0;
                color: white;
                border-radius: 22px;
                border: none;
            }
        """)
        header_layout.addWidget(self._detail_avatar)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self._detail_title = QLabel("选择一个条目查看详情")
        self._detail_title.setFont(QFont("Microsoft YaHei", 15, QFont.DemiBold))
        self._detail_title.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        title_col.addWidget(self._detail_title)
        header_layout.addLayout(title_col, stretch=1)
        right_layout.addWidget(header)

        # ── 分隔线 ──
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #eee;")
        right_layout.addWidget(sep)

        # ── 字段详情区 ──
        fields_widget = QWidget()
        fields_widget.setStyleSheet("background: transparent;")
        self._fields_layout = QVBoxLayout(fields_widget)
        self._fields_layout.setContentsMargins(28, 20, 28, 20)
        self._fields_layout.setSpacing(16)

        # 用户名（始终显示）
        self._username_block = self._create_field_block("用户名", "username", copyable=True)
        self._fields_layout.addWidget(self._username_block)

        # 密码（始终显示）
        self._password_block = self._create_field_block("密  码", "password", copyable=True, has_toggle=True)
        self._fields_layout.addWidget(self._password_block)

        # 网址（有内容才显示）
        self._url_block = self._create_field_block("网  址", "url", copyable=True)
        self._fields_layout.addWidget(self._url_block)
        self._url_block.hide()

        # 备注（有内容才显示）
        self._notes_block = self._create_field_block("备  注", "notes")
        self._fields_layout.addWidget(self._notes_block)
        self._notes_block.hide()

        self._fields_layout.addStretch()

        # ── 空状态占位 ──
        self._empty_state = QWidget()
        self._empty_state.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(16)

        # 大图标
        empty_icon = QLabel("🔐")
        empty_icon.setFont(QFont("Microsoft YaHei", 48))
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet("background: transparent; border: none;")
        empty_layout.addWidget(empty_icon)

        # 主提示
        empty_title = QLabel("选择一个条目查看详情")
        empty_title.setFont(QFont("Microsoft YaHei", 14, QFont.DemiBold))
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setStyleSheet("color: #aaa; background: transparent; border: none;")
        empty_layout.addWidget(empty_title)

        # 副提示
        empty_hint = QLabel("或点击「新增」添加密码条目")
        empty_hint.setFont(QFont("Microsoft YaHei", 11))
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setStyleSheet("color: #ccc; background: transparent; border: none;")
        empty_layout.addWidget(empty_hint)

        # 用 QStackedLayout 切换空状态和字段详情
        self._detail_stack = QStackedLayout()
        self._detail_stack.addWidget(self._empty_state)   # index 0
        self._detail_stack.addWidget(fields_widget)        # index 1
        self._detail_stack.setCurrentIndex(0)

        right_layout.addLayout(self._detail_stack, stretch=1)
        return right_panel

    # ── 分组管理 ──

    def _get_all_groups(self) -> list:
        """获取所有分组（条目中使用的 + 自定义分组），去重排序"""
        db_groups = set(self._db.get_groups())
        custom_groups = set(self._config.get_custom_groups())
        all_groups = sorted(db_groups | custom_groups, key=str.casefold)
        return all_groups

    def _refresh_groups(self):
        """刷新分组下拉框"""
        self._group_combo.blockSignals(True)
        current_group = self._current_group

        self._group_combo.clear()
        self._group_combo.addItem("全部分组", "")

        for group in self._get_all_groups():
            self._group_combo.addItem(group, group)

        # 下拉视图宽度 = combo 宽度
        self._group_combo.view().setMinimumWidth(self._group_combo.width())

        # 恢复之前选中的分组
        if current_group:
            for i in range(self._group_combo.count()):
                if self._group_combo.itemData(i) == current_group:
                    self._group_combo.setCurrentIndex(i)
                    break

        self._group_combo.blockSignals(False)

    def _on_group_changed(self, index: int):
        """分组下拉框切换"""
        self._current_group = self._group_combo.itemData(index) or ""
        self._load_entries()

    def _on_manage_groups(self):
        """打开分组管理对话框"""
        def on_changed():
            self._refresh_groups()
            self._load_entries()
        show_manage_groups(
            self, self._db, self._config, self.windowIcon(),
            self._get_all_groups, on_changed,
        )

    # ── 条目列表 ──

    def _add_list_item(self, entry: Entry, keyword: str = ""):
        """添加一个卡片式列表项"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, entry.id)
        item.setSizeHint(QSize(200, 60))
        self._entry_list.addItem(item)
        card = EntryCardWidget(entry, keyword=keyword)
        self._entry_list.setItemWidget(item, card)
        self._card_widgets[entry.id] = card

    def _load_entries(self):
        # 若搜索框有文本，走搜索逻辑
        if self._search_input.text().strip():
            self._do_search()
            return
        self._entry_list.setUpdatesEnabled(False)
        self._entry_list.clear()
        self._card_widgets.clear()
        self._current_entry = None
        if self._current_group:
            self._entries = self._db.get_entries_by_group(self._current_group)
        else:
            self._entries = self._db.get_all_entries()
        for entry in self._entries:
            self._add_list_item(entry)
        self._entry_list.setUpdatesEnabled(True)
        self._clear_detail()
        # 淡入动画
        self._fade_in_list()

    def _on_search(self, text: str):
        """搜索（带防抖）"""
        self._search_debounce.start(300)

    def _fade_in_list(self):
        """列表逐个淡入动画（样式表渐变）"""
        for i in range(self._entry_list.count()):
            item = self._entry_list.item(i)
            widget = self._entry_list.itemWidget(item)
            if widget:
                # 初始透明背景
                widget.setStyleSheet("""
                    QFrame {
                        background: rgba(255,255,255,0);
                        border: none;
                        border-left: 3px solid transparent;
                        border-radius: 6px;
                    }
                """)
                # 延迟恢复正式样式
                QTimer.singleShot(i * 30 + 50, lambda w=widget: w._update_style(False))

    def _do_search(self):
        """执行搜索"""
        text = self._search_input.text()
        if not text.strip():
            self._load_entries()
            return
        keyword = text.strip()
        self._entry_list.setUpdatesEnabled(False)
        self._entry_list.clear()
        self._card_widgets.clear()
        self._current_entry = None
        results = self._db.search_entries(keyword)
        if self._current_group:
            results = [e for e in results if e.group == self._current_group]
        self._entries = results
        for entry in self._entries:
            self._add_list_item(entry, keyword=keyword)
        self._entry_list.setUpdatesEnabled(True)
        self._clear_detail()

    def _update_card_selection(self, selected_id: str):
        """更新卡片选中态"""
        for entry_id, card in self._card_widgets.items():
            card._update_style(selected=(entry_id == selected_id))

    def _select_entry_by_id(self, entry_id: str):
        """根据 ID 选中条目"""
        for i in range(self._entry_list.count()):
            item = self._entry_list.item(i)
            if item and item.data(Qt.UserRole) == entry_id:
                self._entry_list.setCurrentItem(item)
                return

    def _on_entry_selected(self, current, _previous):
        if current is None:
            self._update_card_selection("")
            self._clear_detail()
            return
        entry_id = current.data(Qt.UserRole)
        self._current_entry = self._db.get_entry(entry_id)
        if self._current_entry:
            self._update_card_selection(entry_id)
            self._show_detail(self._current_entry)
        else:
            self._update_card_selection("")
            self._clear_detail()

    # ── 详情面板 ──

    def _create_field_block(self, label_text: str, field_name: str,
                            copyable: bool = False, has_toggle: bool = False) -> QWidget:
        """创建一个字段块：标签 + 值行（值 + 可选按钮）"""
        block = QWidget()
        block.setStyleSheet("background: transparent;")
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(4)

        # 标签
        label = QLabel(label_text)
        label.setFont(QFont("Microsoft YaHei", 10))
        label.setStyleSheet("color: #999; background: transparent; border: none;")
        block_layout.addWidget(label)

        # 值行
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(6)

        value = QLabel("")
        value.setFont(QFont("Microsoft YaHei", 13))
        value.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setWordWrap(True)
        if field_name == "url":
            value.setOpenExternalLinks(True)
        val_row.addWidget(value, stretch=1)

        setattr(self, f"_{field_name}_value", value)

        # 密码显隐切换
        if has_toggle:
            toggle_btn = QToolButton()
            toggle_btn.setFixedSize(26, 26)
            toggle_btn.setIcon(create_eye_icon(True))
            toggle_btn.setToolTip("显示密码")
            toggle_btn.setCursor(Qt.PointingHandCursor)
            toggle_btn.setStyleSheet(ICON_BTN_STYLE)
            toggle_btn.clicked.connect(lambda: self._toggle_password(toggle_btn))
            val_row.addWidget(toggle_btn, alignment=Qt.AlignVCenter)
            self._password_toggle_btn = toggle_btn

        # 复制按钮
        if copyable:
            copy_btn = QToolButton()
            copy_btn.setFixedSize(26, 26)
            copy_btn.setIcon(create_copy_icon())
            copy_btn.setToolTip("复制")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setStyleSheet(ICON_BTN_STYLE)
            if field_name == "username":
                copy_btn.clicked.connect(self._copy_username)
            elif field_name == "password":
                copy_btn.clicked.connect(self._copy_password)
            elif field_name == "url":
                copy_btn.clicked.connect(self._copy_url)
            val_row.addWidget(copy_btn, alignment=Qt.AlignVCenter)
            setattr(self, f"_{field_name}_copy_btn", copy_btn)

        block_layout.addLayout(val_row)
        return block

    def _toggle_password(self, btn: QToolButton):
        """切换密码显隐"""
        self._password_visible = not self._password_visible
        if self._password_visible:
            btn.setIcon(create_eye_icon(False))
            btn.setToolTip("隐藏密码")
            if self._current_entry:
                self._password_value.setText(self._current_entry.password)
        else:
            btn.setIcon(create_eye_icon(True))
            btn.setToolTip("显示密码")
            if self._current_entry:
                self._password_value.setText("•" * len(self._current_entry.password))

    def _show_detail(self, entry: Entry):
        self._detail_stack.setCurrentIndex(1)  # 显示字段详情
        # 头像
        ch = _first_char(entry.title)
        color = _avatar_color(entry.title)
        self._detail_avatar.setText(ch)
        self._detail_avatar.setStyleSheet(f"""
            QLabel {{
                background: {color};
                color: white;
                border-radius: 22px;
                border: none;
            }}
        """)

        # 标题
        self._detail_title.setText(entry.title)

        # 用户名
        self._username_value.setText(entry.username or "（无）")

        # 密码（重置为隐藏状态）
        self._password_visible = False
        self._password_toggle_btn.setIcon(create_eye_icon(True))
        self._password_value.setText("•" * len(entry.password) if entry.password else "（无）")

        # 网址（有内容才显示）
        if entry.url:
            safe_url = html_mod.escape(entry.url, quote=True)
            safe_text = html_mod.escape(entry.url)
            self._url_value.setText(
                f'<a href="{safe_url}" style="color:#2563eb;text-decoration:none;">{safe_text}</a>'
            )
            self._url_block.show()
        else:
            self._url_block.hide()

        # 备注（有内容才显示）
        if entry.notes:
            self._notes_value.setText(entry.notes)
            self._notes_block.show()
        else:
            self._notes_block.hide()

        # 启用复制按钮
        self._username_copy_btn.setEnabled(True)
        self._password_copy_btn.setEnabled(True)

    def _clear_detail(self):
        self._current_entry = None
        self._detail_stack.setCurrentIndex(0)  # 显示空状态
        self._detail_avatar.setText("?")
        self._detail_avatar.setStyleSheet("""
            QLabel {
                background: #e0e0e0;
                color: white;
                border-radius: 22px;
                border: none;
            }
        """)
        self._detail_title.setText("选择一个条目查看详情")
        self._username_value.setText("")
        self._password_value.setText("")
        self._url_value.setText("")
        self._notes_value.setText("")
        self._url_block.hide()
        self._notes_block.hide()
        self._username_copy_btn.setEnabled(False)
        self._password_copy_btn.setEnabled(False)

    # ── 通用操作 ──

    def _show_info(self, message: str):
        _toast(self, message)

    def _copy_username(self):
        if self._current_entry:
            copy_to_clipboard(self._current_entry.username)
            self._show_info("用户名已复制到剪贴板")

    def _copy_password(self):
        if self._current_entry:
            copy_to_clipboard(self._current_entry.password)
            self._show_info("密码已复制到剪贴板")

    def _copy_url(self):
        if self._current_entry:
            copy_to_clipboard(self._current_entry.url)
            self._show_info("网址已复制到剪贴板")

    def _on_add(self):
        dialog = AddEditDialog(self, groups=self._get_all_groups())
        if dialog.exec_():
            self._db.add_entry(dialog.get_entry())
            self._refresh_groups()
            self._load_entries()
            self._show_info("条目已添加")

    def _on_edit(self):
        if not self._current_entry:
            _toast(self, "请先选择一个条目")
            return
        entry_id = self._current_entry.id
        dialog = AddEditDialog(self, self._current_entry, groups=self._get_all_groups())
        if dialog.exec_():
            self._db.update_entry(dialog.get_entry())
            self._refresh_groups()
            self._load_entries()
            # 延迟选中，等淡入动画完成后再更新选中态
            QTimer.singleShot(200, lambda: self._select_entry_by_id(entry_id))
            self._show_info("条目已更新")

    def _on_delete(self):
        if not self._current_entry:
            _toast(self, "请先选择一个条目")
            return
        if confirm_delete(self._current_entry.title, self):
            self._db.delete_entry(self._current_entry.id)
            self._clear_detail()
            self._refresh_groups()
            self._load_entries()
            self._show_info("条目已删除")

    def _on_lock(self):
        """锁定：返回登录界面（数据库由 main.py handler 关闭）"""
        self.logout.emit()

    def _on_export(self):
        """导出数据为 CSV"""
        show_export_dialog(self, self._db, self._config, self.windowIcon())

    def _on_change_password(self):
        """修改主密码"""
        if show_change_password_dialog(self, self._config, self._db, self.windowIcon()):
            self.logout.emit()

    def _on_about(self):
        """关于对话框"""
        show_about_dialog(self, self.windowIcon())
