"""新增/编辑/删除弹窗"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    LineEdit,
    TextEdit,
    PrimaryPushButton,
    PushButton,
    PasswordLineEdit,
    MessageBox,
    EditableComboBox,
)

from app.core.models import Entry
from app.ui.styles import (
    CARD_STYLE,
    TITLE_STYLE,
    LABEL_STYLE,
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
        self._setup_ui()

    def _setup_ui(self):
        title = "编辑条目" if self._is_edit else "新增条目"
        self.setWindowTitle(title)
        self.setFixedWidth(DIALOG_WIDTH)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 18, QFont.DemiBold))
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

            if is_password:
                input_widget = PasswordLineEdit()
            else:
                input_widget = LineEdit()
            input_widget.setPlaceholderText(placeholder)
            input_widget.setFixedHeight(INPUT_MIN_HEIGHT)
            layout.addWidget(input_widget)
            self._inputs[field_name] = input_widget

        # 分组选择
        group_label = QLabel("分组")
        group_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(group_label)
        self._group_combo = EditableComboBox()
        self._group_combo.setPlaceholderText("选择或输入分组（可选）")
        self._group_combo.setFixedHeight(INPUT_MIN_HEIGHT)
        self._group_combo.addItems(self._groups)
        layout.addWidget(self._group_combo)

        # 网址
        url_label = QLabel("网址")
        url_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(url_label)
        self._url_input = LineEdit()
        self._url_input.setPlaceholderText("https://example.com（可选）")
        self._url_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._url_input)

        # 备注
        notes_label = QLabel("备注")
        notes_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(notes_label)
        self._notes_input = TextEdit()
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
                idx = self._group_combo.findText(self._entry.group)
                if idx >= 0:
                    self._group_combo.setCurrentIndex(idx)
                else:
                    self._group_combo.setCurrentText(self._entry.group)

        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        self._cancel_btn = PushButton("取消")
        self._save_btn = PrimaryPushButton("保存")
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
        group = self._group_combo.currentText().strip()

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


class DeleteConfirmDialog(MessageBox):
    """删除确认对话框"""

    def __init__(self, entry_title: str, parent=None):
        super().__init__(
            "确认删除",
            f'确定要删除 "{entry_title}" 吗？\n此操作不可撤销。',
            parent,
        )
        self.yesButton.setText("删除")
        self.cancelButton.setText("取消")
