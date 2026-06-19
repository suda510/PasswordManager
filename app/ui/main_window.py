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
    InfoBar,
    InfoBarPosition,
    ComboBox,
    ToolButton,
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
        self.setFixedHeight(60)
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

        title_label = QLabel(self._entry.title)
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.DemiBold))
        title_label.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        text_layout.addWidget(title_label)

        user_label = QLabel(self._entry.username or "（无用户名）")
        user_label.setFont(QFont("Microsoft YaHei", 10))
        user_label.setStyleSheet("color: #999; background: transparent; border: none;")
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

        # 底部导航
        self.navigationInterface.addItem(
            routeKey="export",
            icon=FIF.SAVE,
            text="导出数据",
            onClick=self._on_export,
            position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.addItem(
            routeKey="changePassword",
            icon=FIF.SETTING,
            text="修改主密码",
            onClick=self._on_change_password,
            position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.addItem(
            routeKey="about",
            icon=FIF.INFO,
            text="关于",
            onClick=self._on_about,
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

        # 分组下拉框 + 管理按钮
        group_row = QHBoxLayout()
        group_row.setSpacing(8)
        self._group_combo = ComboBox()
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.setPlaceholderText("全部分组")
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        group_row.addWidget(self._group_combo, stretch=1)

        group_manage_btn = PushButton("管理分组")
        group_manage_btn.setFixedHeight(INPUT_MIN_HEIGHT)
        group_manage_btn.clicked.connect(self._on_manage_groups)
        group_row.addWidget(group_manage_btn)
        left_layout.addLayout(group_row)

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
        self._url_block = self._create_field_block("网  址", "url")
        self._fields_layout.addWidget(self._url_block)
        self._url_block.hide()

        # 备注（有内容才显示）
        self._notes_block = self._create_field_block("备  注", "notes")
        self._fields_layout.addWidget(self._notes_block)
        self._notes_block.hide()

        self._fields_layout.addStretch()
        right_layout.addWidget(fields_widget, stretch=1)
        layout.addWidget(right_panel, stretch=1)

        return page

    # ── 分组管理 ──

    def _get_all_groups(self) -> list[str]:
        """获取所有分组（条目中使用的 + 自定义分组），去重排序"""
        db_groups = set(self._db.get_groups())
        custom_groups = set(self._config.get_custom_groups())
        all_groups = sorted(db_groups | custom_groups, key=str.casefold)
        return all_groups

    def _refresh_groups(self):
        """刷新分组下拉框"""
        self._group_combo.blockSignals(True)
        current_text = self._group_combo.currentText()

        self._group_combo.clear()
        self._group_combo.addItem("全部分组", "")

        for group in self._get_all_groups():
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

    def _on_manage_groups(self):
        """打开分组管理对话框"""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
        )
        from qfluentwidgets import LineEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("管理分组")
        dialog.setFixedSize(360, 420)
        dialog.setWindowIcon(self.windowIcon())

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("管理分组")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title)

        # 新增分组输入
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        new_group_input = LineEdit()
        new_group_input.setPlaceholderText("输入新分组名称")
        new_group_input.setFixedHeight(INPUT_MIN_HEIGHT)
        add_row.addWidget(new_group_input, stretch=1)

        add_btn = PrimaryPushButton("添加")
        add_btn.setFixedHeight(INPUT_MIN_HEIGHT)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # 分组列表
        group_list = QListWidget()
        group_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: white;
            }
            QListWidget::item {
                padding: 6px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #0078d4;
            }
        """)
        layout.addWidget(group_list, stretch=1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        rename_btn = PushButton("重命名")
        rename_btn.setFixedHeight(BTN_MIN_HEIGHT)
        rename_btn.setEnabled(False)

        delete_btn = PushButton("删除分组")
        delete_btn.setFixedHeight(BTN_MIN_HEIGHT)
        delete_btn.setEnabled(False)
        delete_btn.setStyleSheet("color: #e81123;")

        btn_row.addStretch()
        btn_row.addWidget(rename_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)

        # ── 刷新列表 ──
        def refresh_list():
            group_list.clear()
            groups = self._get_all_groups()
            for g in groups:
                count = len(self._db.get_entries_by_group(g))
                item = QListWidgetItem(f"{g}  ({count} 个条目)")
                item.setData(Qt.UserRole, g)
                group_list.addItem(item)

        refresh_list()

        # ── 事件绑定 ──
        def on_selection_changed():
            has_sel = group_list.currentItem() is not None
            rename_btn.setEnabled(has_sel)
            delete_btn.setEnabled(has_sel)

        group_list.currentItemChanged.connect(lambda: on_selection_changed())

        def on_add():
            name = new_group_input.text().strip()
            if not name:
                return
            all_groups = self._get_all_groups()
            if name in all_groups:
                InfoBar.warning(title="提示", content="该分组已存在",
                                position=InfoBarPosition.TOP, duration=2000, parent=dialog)
                return
            self._config.add_custom_group(name)
            new_group_input.clear()
            self._refresh_groups()
            refresh_list()
            InfoBar.success(title="成功", content=f'分组 "{name}" 已创建',
                            position=InfoBarPosition.TOP, duration=2000, parent=dialog)

        add_btn.clicked.connect(on_add)
        new_group_input.returnPressed.connect(on_add)

        def on_rename():
            item = group_list.currentItem()
            if not item:
                return
            old_name = item.data(Qt.UserRole)
            new_name_line = LineEdit()
            new_name_line.setText(old_name)
            new_name_line.setFixedHeight(INPUT_MIN_HEIGHT)

            rename_dialog = QDialog(dialog)
            rename_dialog.setWindowTitle("重命名分组")
            rename_dialog.setFixedWidth(320)
            rl = QVBoxLayout(rename_dialog)
            rl.setSpacing(12)
            rl.setContentsMargins(20, 16, 20, 16)

            rl.addWidget(QLabel(f'重命名分组 "{old_name}"'))
            rl.addWidget(new_name_line)

            btns = QHBoxLayout()
            btns.addStretch()
            cancel = PushButton("取消")
            confirm = PrimaryPushButton("确认")
            cancel.clicked.connect(rename_dialog.reject)
            confirm.clicked.connect(rename_dialog.accept)
            btns.addWidget(cancel)
            btns.addWidget(confirm)
            rl.addLayout(btns)

            if rename_dialog.exec_():
                new_name = new_name_line.text().strip()
                if new_name and new_name != old_name:
                    self._db.rename_group(old_name, new_name)
                    self._config.rename_custom_group(old_name, new_name)
                    self._refresh_groups()
                    self._load_entries()
                    refresh_list()
                    InfoBar.success(title="成功", content=f'已重命名为 "{new_name}"',
                                    position=InfoBarPosition.TOP, duration=2000, parent=dialog)

        rename_btn.clicked.connect(on_rename)

        def on_delete():
            item = group_list.currentItem()
            if not item:
                return
            group_name = item.data(Qt.UserRole)
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                dialog, "确认删除",
                f'删除分组 "{group_name}"？\n该分组下的条目将变为"未分组"。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._db.delete_group(group_name)
                self._config.delete_custom_group(group_name)
                self._refresh_groups()
                self._load_entries()
                refresh_list()
                InfoBar.success(title="成功", content=f'分组 "{group_name}" 已删除',
                                position=InfoBarPosition.TOP, duration=2000, parent=dialog)

        delete_btn.clicked.connect(on_delete)

        dialog.exec_()

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
        val_row.addWidget(value, stretch=1)

        setattr(self, f"_{field_name}_value", value)

        # 密码显隐切换
        if has_toggle:
            self._password_visible = False
            toggle_btn = ToolButton()
            toggle_btn.setFixedSize(26, 26)
            toggle_btn.setIcon(FIF.HIDE.icon())
            toggle_btn.setToolTip("显示密码")
            toggle_btn.setCursor(Qt.PointingHandCursor)
            toggle_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QToolButton:hover {
                    background: #f0f0f0;
                }
            """)
            toggle_btn.clicked.connect(lambda: self._toggle_password(toggle_btn))
            val_row.addWidget(toggle_btn, alignment=Qt.AlignVCenter)
            self._password_toggle_btn = toggle_btn

        # 复制按钮
        if copyable:
            copy_btn = ToolButton()
            copy_btn.setFixedSize(26, 26)
            copy_btn.setIcon(FIF.COPY.icon())
            copy_btn.setToolTip("复制")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QToolButton:hover {
                    background: #f0f0f0;
                }
            """)
            if field_name == "username":
                copy_btn.clicked.connect(self._copy_username)
            elif field_name == "password":
                copy_btn.clicked.connect(self._copy_password)
            val_row.addWidget(copy_btn, alignment=Qt.AlignVCenter)
            setattr(self, f"_{field_name}_copy_btn", copy_btn)

        block_layout.addLayout(val_row)
        return block

    def _toggle_password(self, btn: ToolButton):
        """切换密码显隐"""
        self._password_visible = not self._password_visible
        if self._password_visible:
            btn.setIcon(FIF.VIEW.icon())
            btn.setToolTip("隐藏密码")
            if self._current_entry:
                self._password_value.setText(self._current_entry.password)
        else:
            btn.setIcon(FIF.HIDE.icon())
            btn.setToolTip("显示密码")
            if self._current_entry:
                self._password_value.setText("•" * len(self._current_entry.password))

    def _show_detail(self, entry: Entry):
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
        self._password_toggle_btn.setIcon(FIF.HIDE.icon())
        self._password_value.setText("•" * len(entry.password) if entry.password else "（无）")

        # 网址（有内容才显示）
        if entry.url:
            self._url_value.setText(
                f'<a href="{entry.url}" style="color:#0078d4;text-decoration:none;">{entry.url}</a>'
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
        dialog = AddEditDialog(self, groups=self._get_all_groups())
        if dialog.exec_():
            self._db.add_entry(dialog.get_entry())
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已添加")

    def _on_edit(self):
        if not self._current_entry:
            InfoBar.info(title="提示", content="请先选择一个条目", position=InfoBarPosition.TOP_RIGHT, duration=2000, parent=self)
            return
        dialog = AddEditDialog(self, self._current_entry, groups=self._get_all_groups())
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

    def _on_export(self):
        """导出数据为 CSV"""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
        )
        from qfluentwidgets import PasswordLineEdit

        # ── 第一步：验证主密码 ──
        verify_dialog = QDialog(self)
        verify_dialog.setWindowTitle("身份验证")
        verify_dialog.setFixedWidth(380)
        verify_dialog.setWindowIcon(self.windowIcon())

        vlayout = QVBoxLayout(verify_dialog)
        vlayout.setSpacing(14)
        vlayout.setContentsMargins(28, 24, 28, 24)

        vtitle = QLabel("导出数据需要验证身份")
        vtitle.setFont(QFont("Microsoft YaHei", 14, QFont.DemiBold))
        vtitle.setStyleSheet("color: #1a1a1a; background: transparent;")
        vlayout.addWidget(vtitle)

        vhint = QLabel("请输入主密码以继续")
        vhint.setFont(QFont("Microsoft YaHei", 11))
        vhint.setStyleSheet("color: #666; background: transparent;")
        vlayout.addWidget(vhint)

        pwd_input = PasswordLineEdit()
        pwd_input.setPlaceholderText("输入主密码")
        pwd_input.setFixedHeight(INPUT_MIN_HEIGHT)
        vlayout.addWidget(pwd_input)

        vbtn_row = QHBoxLayout()
        vbtn_row.setSpacing(8)
        vbtn_row.addStretch()
        vcancel = PushButton("取消")
        vconfirm = PrimaryPushButton("验证")
        vcancel.setFixedHeight(BTN_MIN_HEIGHT)
        vconfirm.setFixedHeight(BTN_MIN_HEIGHT)
        vcancel.clicked.connect(verify_dialog.reject)
        vconfirm.clicked.connect(verify_dialog.accept)
        vbtn_row.addWidget(vcancel)
        vbtn_row.addWidget(vconfirm)
        vlayout.addLayout(vbtn_row)

        pwd_input.returnPressed.connect(verify_dialog.accept)

        if not verify_dialog.exec_():
            return

        password = pwd_input.text()
        stored_hash = self._config.get("master_password_hash")
        salt = bytes.fromhex(self._config.get("salt"))
        iterations = int(self._config.get("kdf_iterations"))

        if not verify_master_password(password, salt, stored_hash, iterations):
            InfoBar.error(title="错误", content="主密码错误",
                          position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        # ── 第二步：安全警告确认 ──
        reply = QMessageBox.warning(
            self,
            "安全警告",
            "即将导出所有密码为明文 CSV 文件。\n\n"
            "⚠️ 该文件包含所有账号密码的明文信息，\n"
            "请妥善保管，使用后建议立即删除。\n\n"
            "确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # ── 第三步：选择保存路径 ──
        path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "passwords.csv",
            "CSV 文件 (*.csv);;所有文件 (*)",
        )
        if not path:
            return

        # ── 第四步：导出 ──
        try:
            csv_data = self._db.export_csv()
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(csv_data)
            InfoBar.success(
                title="导出成功",
                content=f"已导出到 {path}",
                position=InfoBarPosition.TOP, duration=3000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败",
                content=str(e),
                position=InfoBarPosition.TOP, duration=3000, parent=self,
            )

    def _on_change_password(self):
        """修改主密码"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
        from qfluentwidgets import PasswordLineEdit, LineEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("修改主密码")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setFixedSize(440, 350)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel("修改主密码")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
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

    def _on_about(self):
        """关于对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        dialog = QDialog(self)
        dialog.setWindowTitle("关于")
        dialog.setFixedSize(360, 300)
        dialog.setWindowIcon(self.windowIcon())

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 24, 28, 24)

        # 图标
        icon_label = QLabel("🔐")
        icon_label.setFont(QFont("Microsoft YaHei", 32))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

        # 应用名
        name_label = QLabel("密码管理器")
        name_label.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        layout.addWidget(name_label)

        # 版本
        ver_label = QLabel("v1.0.0")
        ver_label.setFont(QFont("Microsoft YaHei", 11))
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet("color: #999; background: transparent; border: none;")
        layout.addWidget(ver_label)

        # 描述
        desc_label = QLabel("本地优先、离线可用的桌面密码管理器\nAES-256 加密 · 零云端依赖")
        desc_label.setFont(QFont("Microsoft YaHei", 11))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; background: transparent; border: none;")
        layout.addWidget(desc_label)

        layout.addSpacing(8)

        # GitHub 链接
        link_label = QLabel('<a href="https://github.com/suda510/PasswordManager" style="color:#0078d4;text-decoration:none;">GitHub 仓库</a>')
        link_label.setFont(QFont("Microsoft YaHei", 11))
        link_label.setAlignment(Qt.AlignCenter)
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(link_label)

        layout.addStretch()

        dialog.exec_()
