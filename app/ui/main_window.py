"""主界面窗口（纯原生 PyQt5）

使用 QMainWindow + QToolBar 实现现代风格。
"""

import hashlib
import html as html_mod

from PyQt5.QtWidgets import (
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
    QToolBar,
    QToolButton,
    QComboBox,
    QPushButton,
    QAction,
    QFileDialog,
    QDialog,
    QSizeGrip,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QIcon

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
from app.ui.dialogs import AddEditDialog, confirm_delete
from app.ui.styles import (
    LABEL_STYLE,
    INPUT_STYLE,
    COMBO_STYLE,
    ICON_BTN_STYLE,
    GROUP_LIST_STYLE,
    PRIMARY_BTN_STYLE,
    BTN_STYLE,
    CARD_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
    PRIMARY_COLOR,
    BG_PAGE,
)
from app.utils.clipboard import copy_to_clipboard
from app.ui.icon_gen import create_copy_icon, create_eye_icon, create_arrow_icon
from app.utils.paths import get_data_dir


def _get_combo_style() -> str:
    """获取带正确箭头路径的下拉框样式"""
    import os, sys
    # 打包后资源在 sys._MEIPASS，开发时在项目根目录
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    arrow_path = os.path.join(base, 'assets', 'arrow.png').replace('\\', '/')
    return COMBO_STYLE.replace('%ARROW_PATH%', arrow_path)


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


def _toast(parent, message, level="info"):
    """右上角自动消失的通知"""
    colors = {"info": "#323232", "error": "#e81123", "warn": "#d83b01"}
    bg = colors.get(level, "#323232")

    label = QLabel(parent)
    label.setText(f" {message} ")
    label.setFont(QFont("Microsoft YaHei", 10))
    label.adjustSize()
    label.setFixedHeight(30)
    label.setStyleSheet(f"* {{ background: {bg}; color: white; border-radius: 4px; }}")

    label.move(parent.width() - label.width() - 16, 12)
    label.raise_()
    label.show()

    QTimer.singleShot(2500, label.deleteLater)


def _confirm(parent, title, message):
    """自定义确认对话框，返回 True/False"""
    dialog = QDialog(None)
    dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
    dialog.setFixedSize(400, 200)
    dialog.setWindowTitle(title)
    dialog.setStyleSheet("""
        QDialog { background: white; }
        QLabel { color: #1a1a1a; background: transparent; }
        QPushButton { border-radius: 6px; padding: 8px 20px; font-size: 13px; }
    """)
    if parent:
        px = parent.x() + (parent.width() - 400) // 2
        py = parent.y() + (parent.height() - 200) // 2
        dialog.move(px, py)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)
    layout.setContentsMargins(28, 20, 28, 20)

    t = QLabel(title)
    t.setFont(QFont("Microsoft YaHei", 14, QFont.DemiBold))
    t.setStyleSheet("color: #1a1a1a; background: transparent;")
    layout.addWidget(t)

    m = QLabel(message)
    m.setFont(QFont("Microsoft YaHei", 11))
    m.setStyleSheet("color: #666; background: transparent;")
    m.setWordWrap(True)
    layout.addWidget(m)

    layout.addStretch()

    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)
    btn_row.addStretch()

    cancel = QPushButton("取消")
    cancel.setStyleSheet(BTN_STYLE)
    cancel.setFixedHeight(BTN_MIN_HEIGHT)
    cancel.clicked.connect(dialog.reject)

    ok = QPushButton("确定")
    ok.setStyleSheet(PRIMARY_BTN_STYLE)
    ok.setFixedHeight(BTN_MIN_HEIGHT)
    ok.clicked.connect(dialog.accept)

    btn_row.addWidget(cancel)
    btn_row.addWidget(ok)
    layout.addLayout(btn_row)

    return dialog.exec_() == QDialog.Accepted


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

        title_label = QLabel(self._entry.title)
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.DemiBold))
        title_label.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        text_layout.addWidget(title_label)

        user_label = QLabel(self._entry.username or "（无用户名）")
        user_label.setFont(QFont("Microsoft YaHei", 10))
        user_label.setStyleSheet("color: #999; background: transparent; border: none;")
        text_layout.addWidget(user_label)

        layout.addLayout(text_layout, stretch=1)

    def _update_style(self, selected: bool):
        """更新卡片样式（选中/未选中）"""
        if selected:
            self.setStyleSheet("""
                QFrame {
                    background: #e8f0fe;
                    border: none;
                    border-left: 3px solid #0078d4;
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

        # 主内容区
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 12, 20, 12)
        content_layout.setSpacing(16)

        # 左侧面板
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, stretch=1)

        # 右侧面板
        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addWidget(content, stretch=1)

        # 底部工具栏
        self._setup_toolbar()

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
            """下拉宽度与控件宽度一致"""
            def showPopup(self):
                self.view().setMinimumWidth(self.width())
                super().showPopup()

        from PyQt5.QtWidgets import QStyledItemDelegate
        from PyQt5.QtCore import QSize

        class FixedHeightDelegate(QStyledItemDelegate):
            """固定行高 delegate"""
            def sizeHint(self, option, index):
                return QSize(option.rect.width(), 40)

        self._group_combo = AutoWidthCombo()
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.setStyleSheet(_get_combo_style())
        # 下拉视图样式（popup 窗口去掉边框）
        self._group_combo.setItemDelegate(FixedHeightDelegate())
        self._group_combo.view().setStyleSheet(GROUP_LIST_STYLE)
        # 设置 popup 窗口无边框
        self._group_combo.view().window().setStyleSheet("background: white; border: none;")
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
        self._add_btn = QPushButton("新增")
        self._add_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setStyleSheet(BTN_STYLE)
        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet(BTN_STYLE)
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
        self._url_block = self._create_field_block("网  址", "url")
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
        empty_layout.setSpacing(12)

        empty_icon = QLabel("\U0001f512")
        empty_icon.setFont(QFont("Microsoft YaHei", 40))
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet("background: transparent; border: none;")
        empty_layout.addWidget(empty_icon)

        empty_text = QLabel("选择一个条目查看详情")
        empty_text.setFont(QFont("Microsoft YaHei", 12))
        empty_text.setAlignment(Qt.AlignCenter)
        empty_text.setStyleSheet("color: #bbb; background: transparent; border: none;")
        empty_layout.addWidget(empty_text)

        # 用 QStackedLayout 切换空状态和字段详情
        self._detail_stack = QStackedLayout()
        self._detail_stack.addWidget(self._empty_state)   # index 0
        self._detail_stack.addWidget(fields_widget)        # index 1
        self._detail_stack.setCurrentIndex(0)

        right_layout.addLayout(self._detail_stack, stretch=1)
        return right_panel

    def _setup_toolbar(self):
        """创建底部工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: white;
                border-top: 1px solid #e8e8e8;
                padding: 4px 12px;
                spacing: 8px;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                color: #1a1a1a;
            }
            QToolButton:hover {
                background: #f0f0f0;
            }
        """)
        self.addToolBar(Qt.BottomToolBarArea, toolbar)

        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(1, 1)
        toolbar.addWidget(spacer)

        # 导出
        export_action = toolbar.addAction("导出数据")
        export_action.triggered.connect(self._on_export)

        # 修改密码
        change_pwd_action = toolbar.addAction("修改主密码")
        change_pwd_action.triggered.connect(self._on_change_password)

        # 关于
        about_action = toolbar.addAction("关于")
        about_action.triggered.connect(self._on_about)

        # 锁定
        lock_action = toolbar.addAction("锁定")
        lock_action.triggered.connect(self._on_lock)

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
        current_text = self._group_combo.currentText()

        self._group_combo.clear()
        self._group_combo.addItem("全部分组", "")

        for group in self._get_all_groups():
            self._group_combo.addItem(group, group)

        # 下拉视图宽度 = combo 宽度
        self._group_combo.view().setMinimumWidth(self._group_combo.width())

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
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
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
        new_group_input = QLineEdit()
        new_group_input.setPlaceholderText("输入新分组名称")
        new_group_input.setFixedHeight(INPUT_MIN_HEIGHT)
        new_group_input.setStyleSheet(INPUT_STYLE)
        add_row.addWidget(new_group_input, stretch=1)

        add_btn = QPushButton("添加")
        add_btn.setFixedHeight(INPUT_MIN_HEIGHT)
        add_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # 分组列表
        group_list = QListWidget()
        group_list.setStyleSheet(GROUP_LIST_STYLE)
        layout.addWidget(group_list, stretch=1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        rename_btn = QPushButton("重命名")
        rename_btn.setFixedHeight(BTN_MIN_HEIGHT)
        rename_btn.setStyleSheet(BTN_STYLE)
        rename_btn.setEnabled(False)

        delete_btn = QPushButton("删除分组")
        delete_btn.setFixedHeight(BTN_MIN_HEIGHT)
        delete_btn.setStyleSheet("color: #e81123; border: none; background: transparent; font-size: 13px;")
        delete_btn.setEnabled(False)

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
                _toast(dialog, "该分组已存在", "warn")
                return
            self._config.add_custom_group(name)
            new_group_input.clear()
            self._refresh_groups()
            refresh_list()
            _toast(dialog, f'分组 "{name}" 已创建')

        add_btn.clicked.connect(on_add)
        new_group_input.returnPressed.connect(on_add)

        def on_rename():
            item = group_list.currentItem()
            if not item:
                return
            old_name = item.data(Qt.UserRole)

            rn_dialog = QDialog(dialog)
            rn_dialog.setWindowFlags(rn_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            rn_dialog.setWindowTitle("重命名分组")
            rn_dialog.setFixedSize(360, 180)
            rn_dialog.setStyleSheet(INPUT_STYLE)

            rn_layout = QVBoxLayout(rn_dialog)
            rn_layout.setSpacing(12)
            rn_layout.setContentsMargins(24, 20, 24, 20)

            rn_title = QLabel(f'重命名分组 "{old_name}"')
            rn_title.setFont(QFont("Microsoft YaHei", 13, QFont.DemiBold))
            rn_title.setStyleSheet("color: #1a1a1a; background: transparent;")
            rn_layout.addWidget(rn_title)

            rn_input = QLineEdit()
            rn_input.setText(old_name)
            rn_input.setFixedHeight(INPUT_MIN_HEIGHT)
            rn_layout.addWidget(rn_input)

            rn_btn_row = QHBoxLayout()
            rn_btn_row.setSpacing(8)
            rn_btn_row.addStretch()
            rn_cancel = QPushButton("取消")
            rn_cancel.setStyleSheet(BTN_STYLE)
            rn_cancel.setFixedHeight(BTN_MIN_HEIGHT)
            rn_cancel.clicked.connect(rn_dialog.reject)
            rn_ok = QPushButton("确定")
            rn_ok.setStyleSheet(PRIMARY_BTN_STYLE)
            rn_ok.setFixedHeight(BTN_MIN_HEIGHT)
            rn_ok.clicked.connect(rn_dialog.accept)
            rn_input.returnPressed.connect(rn_dialog.accept)
            rn_btn_row.addWidget(rn_cancel)
            rn_btn_row.addWidget(rn_ok)
            rn_layout.addLayout(rn_btn_row)

            if rn_dialog.exec_() != QDialog.Accepted:
                return
            new_name = rn_input.text().strip()
            if not new_name or new_name == old_name:
                return
            if new_name in self._get_all_groups():
                _toast(dialog, "该分组名已存在", "warn")
                return
            self._db.rename_group(old_name, new_name)
            self._config.rename_custom_group(old_name, new_name)
            self._refresh_groups()
            self._load_entries()
            refresh_list()
            _toast(dialog, f'已重命名为 "{new_name}"')

        rename_btn.clicked.connect(on_rename)

        def on_delete():
            item = group_list.currentItem()
            if not item:
                return
            group_name = item.data(Qt.UserRole)
            reply = _confirm(dialog, "确认删除",
                f'删除分组 "{group_name}"？\n该分组下的条目将变为"未分组"。')
            if reply:
                self._db.delete_group(group_name)
                self._config.delete_custom_group(group_name)
                self._refresh_groups()
                self._load_entries()
                refresh_list()
                _toast(dialog, f'分组 "{group_name}" 已删除')

        delete_btn.clicked.connect(on_delete)

        dialog.exec_()

    # ── 条目列表 ──

    def _add_list_item(self, entry: Entry):
        """添加一个卡片式列表项"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, entry.id)
        item.setSizeHint(QSize(200, 60))
        self._entry_list.addItem(item)
        card = EntryCardWidget(entry)
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

    def _on_search(self, text: str):
        """搜索（带防抖）"""
        self._search_debounce.start(300)

    def _do_search(self):
        """执行搜索"""
        text = self._search_input.text()
        if not text.strip():
            self._load_entries()
            return
        # 批量更新，减少重绘
        self._entry_list.setUpdatesEnabled(False)
        self._entry_list.clear()
        self._card_widgets.clear()
        self._current_entry = None
        results = self._db.search_entries(text.strip())
        if self._current_group:
            results = [e for e in results if e.group == self._current_group]
        self._entries = results
        for entry in self._entries:
            self._add_list_item(entry)
        self._entry_list.setUpdatesEnabled(True)
        self._clear_detail()

    def _update_card_selection(self, selected_id: str):
        """更新卡片选中态"""
        for entry_id, card in self._card_widgets.items():
            card._update_style(selected=(entry_id == selected_id))

    def _on_entry_selected(self, current, _previous):
        if current is None:
            self._update_card_selection("")
            self._clear_detail()
            return
        entry_id = current.data(Qt.UserRole)
        self._current_entry = self._db.get_entry(entry_id)
        self._update_card_selection(entry_id)
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
        self._password_toggle_btn.setText("👁")
        self._password_value.setText("•" * len(entry.password) if entry.password else "（无）")

        # 网址（有内容才显示）
        if entry.url:
            safe_url = html_mod.escape(entry.url, quote=True)
            safe_text = html_mod.escape(entry.url)
            self._url_value.setText(
                f'<a href="{safe_url}" style="color:#0078d4;text-decoration:none;">{safe_text}</a>'
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

    def _on_add(self):
        dialog = AddEditDialog(self, groups=self._get_all_groups())
        if dialog.exec_():
            self._db.add_entry(dialog.get_entry())
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已添加")

    def _on_edit(self):
        if not self._current_entry:
            _toast(self, "请先选择一个条目")
            return
        dialog = AddEditDialog(self, self._current_entry, groups=self._get_all_groups())
        if dialog.exec_():
            self._db.update_entry(dialog.get_entry())
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已更新")

    def _on_delete(self):
        if not self._current_entry:
            _toast(self, "请先选择一个条目")
            return
        if confirm_delete(self._current_entry.title, self):
            self._db.delete_entry(self._current_entry.id)
            self._clear_detail()
            self._load_entries()
            self._refresh_groups()
            self._show_info("条目已删除")

    def _on_lock(self):
        """锁定：返回登录界面（数据库由 main.py handler 关闭）"""
        self.logout.emit()

    def _on_export(self):
        """导出数据为 CSV"""
        # ── 第一步：验证主密码（自定义样式对话框） ──
        verify_dialog = QDialog(self)
        verify_dialog.setWindowFlags(verify_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        verify_dialog.setWindowTitle("身份验证")
        verify_dialog.setFixedSize(380, 220)
        verify_dialog.setWindowIcon(self.windowIcon())
        verify_dialog.setStyleSheet(INPUT_STYLE)

        vl = QVBoxLayout(verify_dialog)
        vl.setSpacing(12)
        vl.setContentsMargins(28, 24, 28, 24)

        vt = QLabel("身份验证")
        vt.setFont(QFont("Microsoft YaHei", 14, QFont.DemiBold))
        vt.setStyleSheet("color: #1a1a1a; background: transparent;")
        vl.addWidget(vt)

        vh = QLabel("导出数据需要验证身份，请输入主密码")
        vh.setFont(QFont("Microsoft YaHei", 11))
        vh.setStyleSheet("color: #666; background: transparent;")
        vl.addWidget(vh)

        pwd_input = QLineEdit()
        pwd_input.setPlaceholderText("输入主密码")
        pwd_input.setEchoMode(QLineEdit.Password)
        pwd_input.setFixedHeight(INPUT_MIN_HEIGHT)
        vl.addWidget(pwd_input)

        vbtn_row = QHBoxLayout()
        vbtn_row.setSpacing(8)
        vbtn_row.addStretch()
        vcancel = QPushButton("取消")
        vcancel.setStyleSheet(BTN_STYLE)
        vcancel.setFixedHeight(BTN_MIN_HEIGHT)
        vcancel.clicked.connect(verify_dialog.reject)
        vok = QPushButton("验证")
        vok.setStyleSheet(PRIMARY_BTN_STYLE)
        vok.setFixedHeight(BTN_MIN_HEIGHT)
        vok.clicked.connect(verify_dialog.accept)
        pwd_input.returnPressed.connect(verify_dialog.accept)
        vbtn_row.addWidget(vcancel)
        vbtn_row.addWidget(vok)
        vl.addLayout(vbtn_row)

        if verify_dialog.exec_() != QDialog.Accepted:
            return

        password = pwd_input.text()
        if not password:
            return

        stored_hash = self._config.get("master_password_hash")
        try:
            salt = self._config.get_salt()
            iterations = self._config.get_iterations()
        except ValueError as e:
            _toast(self, str(e), "error")
            return

        if not verify_master_password(password, salt, stored_hash, iterations):
            _toast(self, "主密码错误", "error")
            return

        # ── 第二步：安全警告确认 ──
        reply = _confirm(
            self,
            "安全警告",
            "即将导出所有密码为明文 CSV 文件。\n\n"
            "该文件包含所有账号密码的明文信息，\n"
            "请妥善保管，使用后建议立即删除。",
        )
        if not reply:
            return

        # ── 第三步：选择保存路径 ──
        path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "data_export.csv",
            "CSV 文件 (*.csv);;所有文件 (*)",
        )
        if not path:
            return

        # ── 第四步：导出 ──
        try:
            csv_data = self._db.export_csv()
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(csv_data)
            _toast(self, "导出成功")
        except Exception:
            _toast(self, "导出失败", "error")

    def _on_change_password(self):
        """修改主密码"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("修改主密码")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setFixedSize(440, 350)
        dialog.setStyleSheet(INPUT_STYLE)

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
        cur_input = QLineEdit()
        cur_input.setEchoMode(QLineEdit.Password)
        cur_input.setPlaceholderText("输入当前主密码")
        cur_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(cur_input)

        # 新密码
        new_label = QLabel("新密码")
        new_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(new_label)
        new_input = QLineEdit()
        new_input.setEchoMode(QLineEdit.Password)
        new_input.setPlaceholderText("输入新主密码")
        new_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(new_input)

        # 确认新密码
        confirm_label = QLabel("确认新密码")
        confirm_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(confirm_label)
        confirm_input = QLineEdit()
        confirm_input.setEchoMode(QLineEdit.Password)
        confirm_input.setPlaceholderText("再次输入新主密码")
        confirm_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(confirm_input)

        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(BTN_STYLE)
        save_btn = QPushButton("确认修改")
        save_btn.setStyleSheet(PRIMARY_BTN_STYLE)
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
                _toast(dialog, "请填写所有字段", "warn")
                return

            if len(new_password) < 6:
                _toast(dialog, "新密码至少 6 个字符", "warn")
                return

            if new_password != confirm:
                _toast(dialog, "两次输入的新密码不一致", "warn")
                return

            # 验证当前密码
            stored_hash = self._config.get("master_password_hash")
            try:
                salt = self._config.get_salt()
                iterations = self._config.get_iterations()
            except ValueError as e:
                _toast(dialog, str(e), "error")
                return

            if not verify_master_password(cur_password, salt, stored_hash, iterations):
                _toast(dialog, "当前密码错误", "error")
                return

            # 派生新密钥并重新加密所有数据
            new_salt = generate_salt()
            new_key = derive_key(new_password, new_salt, DEFAULT_ITERATIONS)
            new_hash = hash_master_password(new_password, new_salt, DEFAULT_ITERATIONS)

            try:
                self._db.rekey(new_key)
            except Exception:
                _toast(dialog, "数据加密失败，请重试", "error")
                return

            # 更新配置
            self._config.set("master_password_hash", new_hash)
            self._config.set("salt", new_salt.hex())
            self._config.set("kdf_iterations", str(DEFAULT_ITERATIONS))

            _toast(dialog, "主密码已修改，请重新登录")
            dialog.accept()

        save_btn.clicked.connect(on_save)

        # 标志位：on_save 中 accept 时置为 True
        accepted = [False]
        _orig_accept = dialog.accept

        def _mark_accept():
            accepted[0] = True
            _orig_accept()

        dialog.accept = _mark_accept

        dialog.exec_()

        if accepted[0]:
            self.logout.emit()

    def _on_about(self):
        """关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("关于")
        dialog.setFixedSize(380, 400)
        dialog.setWindowIcon(self.windowIcon())

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 24, 28, 24)

        # 图标
        icon_label = QLabel("\U0001f510")
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

        layout.addSpacing(4)

        # 特性说明
        features = [
            ("完全离线，不联网不上传", "#555"),
            ("数据仅保存在你的电脑上", "#555"),
            ("AES-256 加密保护", "#555"),
        ]
        for text, color in features:
            fl = QLabel(text)
            fl.setFont(QFont("Microsoft YaHei", 11))
            fl.setAlignment(Qt.AlignCenter)
            fl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            layout.addWidget(fl)

        layout.addSpacing(4)

        # 描述
        desc_label = QLabel("你的密码，只属于你")
        desc_label.setFont(QFont("Microsoft YaHei", 10))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #999; background: transparent; border: none;")
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
