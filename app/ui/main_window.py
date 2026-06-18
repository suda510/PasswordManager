"""主界面窗口

使用 QFluentWidgets 实现现代 Fluent Design 风格。
"""

import hashlib

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    FluentIcon as FIF,
    SearchLineEdit,
    ListWidget,
    PrimaryPushButton,
    PushButton,
    CardWidget,
    SubtitleLabel,
    BodyLabel,
    CaptionLabel,
    InfoBar,
    InfoBarPosition,
    ComboBox,
)

from app.core.db import Database
from app.core.models import Entry
from app.core.config_manager import ConfigManager
from app.core.crypto import (
    generate_salt,
    derive_key,
    hash_master_password,
    verify_master_password,
    DEFAULT_ITERATIONS,
)
from app.ui.dialogs import AddEditDialog, DeleteConfirmDialog
from app.ui.styles import (
    LABEL_STYLE,
    LABEL_MUTED_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
)
from app.utils.clipboard import copy_to_clipboard


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


def _first_char(text: str) -> str:
    """取首字符（中文取第一个字，英文取首字母大写）"""
    if not text:
        return "?"
    ch = text[0]
    return ch.upper() if ch.isascii() else ch


class EntryCardWidget(QFrame):
    """条目卡片组件：左侧头像 + 右侧标题/用户名"""

    def __init__(self, entry: Entry, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(56)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background: rgba(0, 0, 0, 0.04);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        # ── 首字母头像 ──
        avatar = QLabel(_first_char(self._entry.title))
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        color = _avatar_color(self._entry.title)
        avatar.setStyleSheet(f"""
            QLabel {{
                background: {color};
                color: white;
                font-size: 15px;
                font-weight: 600;
                border-radius: 18px;
                border: none;
            }}
        """)
        layout.addWidget(avatar)

        # ── 文字区域 ──
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = QLabel(self._entry.title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #1a1a1a;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(title_label)

        user_label = QLabel(self._entry.username or "（无用户名）")
        user_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #888;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(user_label)

        layout.addLayout(text_layout, stretch=1)


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self, db: Database, config: ConfigManager):
        super().__init__()
        self._db = db
        self._config = config
        self._current_entry = None
        self._setup_ui()
        self._load_entries()

    def _setup_ui(self):
        self.setWindowTitle("密码管理器")
        self.resize(960, 640)
        self.setMinimumSize(760, 480)

        self._home_page = self._create_home_page()
        self._home_page.setObjectName("homePage")
        self.addSubInterface(self._home_page, FIF.HOME, "主页")

        # 底部导航：修改密码
        self.navigationInterface.addItem(
            routeKey="changePassword",
            icon=FIF.FINGERPRINT,
            text="修改主密码",
            onClick=self._on_change_password,
            position=NavigationItemPosition.BOTTOM,
        )

    def _create_home_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 12, 20, 20)
        layout.setSpacing(16)

        # 左侧：搜索 + 分组下拉 + 列表 + 按钮
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self._search_input = SearchLineEdit()
        self._search_input.setPlaceholderText("搜索网站/软件名...")
        self._search_input.textChanged.connect(self._on_search)
        left_layout.addWidget(self._search_input)

        # 分组下拉框
        self._group_combo = ComboBox()
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.setPlaceholderText("全部分组")
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        left_layout.addWidget(self._group_combo)

        self._current_group = ""
        self._refresh_groups()

        list_card = CardWidget()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self._entry_list = ListWidget()
        self._entry_list.currentItemChanged.connect(self._on_entry_selected)
        list_layout.addWidget(self._entry_list)
        left_layout.addWidget(list_card)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self._add_btn = PrimaryPushButton("新增")
        self._edit_btn = PushButton("编辑")
        self._delete_btn = PushButton("删除")
        for btn in (self._add_btn, self._edit_btn, self._delete_btn):
            btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._add_btn)
        btn_layout.addWidget(self._edit_btn)
        btn_layout.addWidget(self._delete_btn)
        left_layout.addLayout(btn_layout)

        layout.addWidget(left_panel, stretch=1)

        # 右侧：详情卡片
        right_panel = CardWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(28, 24, 28, 24)
        right_layout.setSpacing(10)

        self._detail_title = SubtitleLabel("选择一个条目查看详情")
        right_layout.addWidget(self._detail_title)
        right_layout.addSpacing(4)

        fields = [
            ("分组", "group"),
            ("用户名", "username"),
            ("密码", "password"),
            ("网址", "url"),
            ("备注", "notes"),
        ]
        for label_text, field_name in fields:
            label = CaptionLabel(label_text)
            label.setStyleSheet(LABEL_MUTED_STYLE)
            value = BodyLabel("")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if field_name == "url":
                value.setOpenExternalLinks(True)
            if field_name == "notes":
                value.setWordWrap(True)
            right_layout.addWidget(label)
            right_layout.addWidget(value)
            setattr(self, f"_{field_name}_label", label)
            setattr(self, f"_{field_name}_value", value)

        right_layout.addSpacing(4)

        copy_layout = QHBoxLayout()
        copy_layout.setSpacing(8)
        self._copy_username_btn = PushButton("复制用户名")
        self._copy_password_btn = PrimaryPushButton("复制密码")
        self._copy_username_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._copy_password_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._copy_username_btn.setEnabled(False)
        self._copy_password_btn.setEnabled(False)
        self._copy_username_btn.clicked.connect(self._copy_username)
        self._copy_password_btn.clicked.connect(self._copy_password)
        copy_layout.addWidget(self._copy_username_btn)
        copy_layout.addWidget(self._copy_password_btn)
        copy_layout.addStretch()
        right_layout.addLayout(copy_layout)
        right_layout.addStretch()

        layout.addWidget(right_panel, stretch=1)

        return page

    # ── 分组管理 ──

    def _refresh_groups(self):
        """刷新分组下拉框"""
        self._group_combo.blockSignals(True)
        current_text = self._group_combo.currentText()

        self._group_combo.clear()
        self._group_combo.addItem("全部分组", "")

        groups = self._db.get_groups()
        for group in groups:
            self._group_combo.addItem(group, group)

        # 恢复之前选中的分组
        if current_text:
            idx = self._group_combo.findText(current_text)
            if idx >= 0:
                self._group_combo.setCurrentIndex(idx)

        self._group_combo.blockSignals(False)

    def _on_group_changed(self, index: int):
        """分组下拉框切换"""
        self._current_group = self._group_combo.itemData(index) or ""
        self._load_entries()

    # ── 条目列表 ──

    def _add_list_item(self, entry: Entry):
        """添加一个卡片式列表项"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, entry.id)
        item.setSizeHint(self._entry_card_size_hint())
        self._entry_list.addItem(item)
        card = EntryCardWidget(entry)
        self._entry_list.setItemWidget(item, card)

    def _entry_card_size_hint(self):
        """卡片尺寸"""
        from PyQt5.QtCore import QSize
        return QSize(200, 56)

    def _load_entries(self):
        self._entry_list.clear()
        if self._current_group:
            self._entries = self._db.get_entries_by_group(self._current_group)
        else:
            self._entries = self._db.get_all_entries()
        for entry in self._entries:
            self._add_list_item(entry)

    def _on_search(self, text: str):
        if not text.strip():
            self._load_entries()
            return
        self._entry_list.clear()
        results = self._db.search_entries(text.strip())
        if self._current_group:
            results = [e for e in results if e.group == self._current_group]
        self._entries = results
        for entry in self._entries:
            self._add_list_item(entry)

    def _on_entry_selected(self, current, _previous):
        if current is None:
            self._clear_detail()
            return
        entry_id = current.data(Qt.UserRole)
        self._current_entry = self._db.get_entry(entry_id)
        if self._current_entry:
            self._show_detail(self._current_entry)

    # ── 详情面板 ──

    def _show_detail(self, entry: Entry):
        self._detail_title.setText(entry.title)
        self._group_value.setText(entry.group if entry.group else "（未分组）")
        self._username_value.setText(entry.username)
        self._password_value.setText("•" * len(entry.password))
        self._url_value.setText(
            f'<a href="{entry.url}">{entry.url}</a>' if entry.url else "（无）"
        )
        self._notes_value.setText(entry.notes if entry.notes else "（无）")
        self._copy_username_btn.setEnabled(True)
        self._copy_password_btn.setEnabled(True)

    def _clear_detail(self):
        self._current_entry = None
        self._detail_title.setText("选择一个条目查看详情")
        self._group_value.setText("")
        self._username_value.setText("")
        self._password_value.setText("")
        self._url_value.setText("")
        self._notes_value.setText("")
        self._copy_username_btn.setEnabled(False)
        self._copy_password_btn.setEnabled(False)

    # ── 通用操作 ──

    def _show_info(self, message: str):
        InfoBar.success(
            title="成功",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self,
        )

    def _copy_username(self):
        if self._current_entry:
            copy_to_clipboard(self._current_entry.username)
            self._show_info("用户名已复制到剪贴板")

    def _copy_password(self):
        if self._current_entry:
            copy_to_clipboard(self._current_entry.password)
            self._show_info("密码已复制到剪贴板")

    def _on_add(self):
        dialog = AddEditDialog(self, groups=self._db.get_groups())
        if dialog.exec_():
            self._db.add_entry(dialog.get_entry())
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已添加")

    def _on_edit(self):
        if not self._current_entry:
            InfoBar.info(title="提示", content="请先选择一个条目", position=InfoBarPosition.TOP_RIGHT, duration=2000, parent=self)
            return
        dialog = AddEditDialog(self, self._current_entry, groups=self._db.get_groups())
        if dialog.exec_():
            self._db.update_entry(dialog.get_entry())
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已更新")

    def _on_delete(self):
        if not self._current_entry:
            InfoBar.info(title="提示", content="请先选择一个条目", position=InfoBarPosition.TOP_RIGHT, duration=2000, parent=self)
            return
        dialog = DeleteConfirmDialog(self._current_entry.title, self)
        if dialog.exec_():
            self._db.delete_entry(self._current_entry.id)
            self._clear_detail()
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已删除")

    def _on_change_password(self):
        """修改主密码"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
        from qfluentwidgets import PasswordLineEdit, LineEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("修改主密码")
        dialog.setFixedSize(440, 350)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel("修改主密码")
        title.setFont(QFont("Segoe UI", 18, QFont.DemiBold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title)

        # 当前密码
        cur_label = QLabel("当前密码")
        cur_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(cur_label)
        cur_input = PasswordLineEdit()
        cur_input.setPlaceholderText("输入当前主密码")
        cur_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(cur_input)

        # 新密码
        new_label = QLabel("新密码")
        new_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(new_label)
        new_input = PasswordLineEdit()
        new_input.setPlaceholderText("输入新主密码")
        new_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(new_input)

        # 确认新密码
        confirm_label = QLabel("确认新密码")
        confirm_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(confirm_label)
        confirm_input = PasswordLineEdit()
        confirm_input.setPlaceholderText("再次输入新主密码")
        confirm_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(confirm_input)

        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = PushButton("取消")
        save_btn = PrimaryPushButton("确认修改")
        cancel_btn.setFixedHeight(BTN_MIN_HEIGHT)
        save_btn.setFixedHeight(BTN_MIN_HEIGHT)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def on_save():
            cur_password = cur_input.text()
            new_password = new_input.text()
            confirm = confirm_input.text()

            if not cur_password or not new_password:
                InfoBar.warning(title="提示", content="请填写所有字段", position=InfoBarPosition.TOP, duration=2000, parent=dialog)
                return

            if len(new_password) < 6:
                InfoBar.warning(title="提示", content="新密码至少 6 个字符", position=InfoBarPosition.TOP, duration=2000, parent=dialog)
                return

            if new_password != confirm:
                InfoBar.warning(title="提示", content="两次输入的新密码不一致", position=InfoBarPosition.TOP, duration=2000, parent=dialog)
                return

            # 验证当前密码
            stored_hash = self._config.get("master_password_hash")
            salt = bytes.fromhex(self._config.get("salt"))
            iterations = int(self._config.get("kdf_iterations"))

            if not verify_master_password(cur_password, salt, stored_hash, iterations):
                InfoBar.error(title="错误", content="当前密码错误", position=InfoBarPosition.TOP, duration=2000, parent=dialog)
                return

            # 更新密码
            new_salt = generate_salt()
            new_hash = hash_master_password(new_password, new_salt, DEFAULT_ITERATIONS)
            self._config.set("master_password_hash", new_hash)
            self._config.set("salt", new_salt.hex())
            self._config.set("kdf_iterations", str(DEFAULT_ITERATIONS))

            InfoBar.success(title="成功", content="主密码已修改", position=InfoBarPosition.TOP, duration=2000, parent=dialog)
            dialog.accept()

        save_btn.clicked.connect(on_save)
        dialog.exec_()
