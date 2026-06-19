"""新增/编辑/删除弹窗（纯原生 PyQt5）"""

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from app.core.models import Entry
from app.ui.styles import (
    PRIMARY_BTN_STYLE,
    BTN_STYLE,
    LABEL_STYLE,
    INPUT_STYLE,
    COMBO_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
    DIALOG_WIDTH,
)


class AddEditDialog(QDialog):
    """新增/编辑条目对话框"""

    def __init__(self, parent=None, entry=None, groups=None):
        super().__init__(parent)
        self._entry = entry
        self._is_edit = entry is not None
        self._groups = groups or []
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if parent:
            self.setWindowIcon(parent.windowIcon())
        self._setup_ui()

    def _setup_ui(self):
        title = "编辑条目" if self._is_edit else "新增条目"
        self.setWindowTitle(title)
        self.setFixedWidth(DIALOG_WIDTH)
        self.setMinimumHeight(420)
        self.setStyleSheet(INPUT_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
        title_label.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title_label)
        layout.addSpacing(8)

        # 表单字段
        fields = [
            ("网站/软件名 *", "title", "例如：GitHub、淘宝", False),
            ("用户名", "username", "用户名/邮箱", False),
            ("密码", "password", "密码", True),
        ]

        self._inputs = {}
        for label_text, field_name, placeholder, is_password in fields:
            label = QLabel(label_text)
            label.setStyleSheet(LABEL_STYLE)
            layout.addWidget(label)

            input_widget = QLineEdit()
            input_widget.setPlaceholderText(placeholder)
            input_widget.setFixedHeight(INPUT_MIN_HEIGHT)
            if is_password:
                input_widget.setEchoMode(QLineEdit.Password)
            layout.addWidget(input_widget)
            self._inputs[field_name] = input_widget

        # 分组选择
        group_label = QLabel("分组")
        group_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(group_label)
        self._group_combo = QComboBox()
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.setStyleSheet(COMBO_STYLE)
        self._group_combo.addItem("（无分组）", "")
        for g in self._groups:
            self._group_combo.addItem(g, g)
        layout.addWidget(self._group_combo)

        # 网址
        url_label = QLabel("网址")
        url_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(url_label)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com（可选）")
        self._url_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._url_input)

        # 备注
        notes_label = QLabel("备注")
        notes_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(notes_label)
        self._notes_input = QTextEdit()
        self._notes_input.setPlaceholderText("备注信息（可选）")
        self._notes_input.setMaximumHeight(80)
        layout.addWidget(self._notes_input)

        # 填充编辑数据
        if self._is_edit:
            self._inputs["title"].setText(self._entry.title)
            self._inputs["username"].setText(self._entry.username)
            self._inputs["password"].setText(self._entry.password)
            self._url_input.setText(self._entry.url)
            self._notes_input.setPlainText(self._entry.notes)
            if self._entry.group:
                for i in range(self._group_combo.count()):
                    if self._group_combo.itemData(i) == self._entry.group:
                        self._group_combo.setCurrentIndex(i)
                        break

        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(BTN_STYLE)
        self._save_btn = QPushButton("保存")
        self._save_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._cancel_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._save_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

    def _on_save(self):
        title = self._inputs["title"].text().strip()
        if not title:
            self._inputs["title"].setFocus()
            return
        self.accept()

    def get_entry(self) -> Entry:
        title = self._inputs["title"].text().strip()
        username = self._inputs["username"].text().strip()
        password = self._inputs["password"].text()
        url = self._url_input.text().strip()
        notes = self._notes_input.toPlainText().strip()
        group = self._group_combo.currentData() or ""

        if self._is_edit:
            return self._entry.with_update(
                title=title, username=username, password=password,
                url=url, notes=notes, group=group,
            )
        else:
            return Entry(
                title=title, username=username, password=password,
                url=url, notes=notes, group=group,
            )


def confirm_delete(entry_title: str, parent=None) -> bool:
    """确认删除条目（自定义样式对话框）"""
    dialog = QDialog(parent)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setFixedSize(380, 200)
    dialog.setWindowTitle("确认删除")
    if parent:
        dialog.setWindowIcon(parent.windowIcon())

    layout = QVBoxLayout(dialog)
    layout.setSpacing(16)
    layout.setContentsMargins(28, 24, 28, 24)

    title = QLabel("确认删除")
    title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
    title.setStyleSheet("color: #1a1a1a; background: transparent;")
    layout.addWidget(title)

    msg = QLabel(f'确定要删除 "{entry_title}" 吗？\n此操作不可撤销。')
    msg.setFont(QFont("Microsoft YaHei", 11))
    msg.setStyleSheet("color: #666; background: transparent;")
    msg.setWordWrap(True)
    layout.addWidget(msg)

    layout.addStretch()

    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)
    btn_row.addStretch()

    cancel_btn = QPushButton("取消")
    cancel_btn.setStyleSheet(BTN_STYLE)
    cancel_btn.setFixedHeight(BTN_MIN_HEIGHT)
    cancel_btn.clicked.connect(dialog.reject)

    delete_btn = QPushButton("删除")
    delete_btn.setStyleSheet("""
        QPushButton {
            background: #e81123;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton:hover { background: #c50f1f; }
        QPushButton:pressed { background: #a80d1a; }
    """)
    delete_btn.setFixedHeight(BTN_MIN_HEIGHT)
    delete_btn.clicked.connect(dialog.accept)

    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(delete_btn)
    layout.addLayout(btn_row)

    return dialog.exec_() == QDialog.Accepted
