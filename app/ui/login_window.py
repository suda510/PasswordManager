"""主密码登录窗口（纯原生 PyQt5）

首次运行：设置主密码 + 生成恢复密钥
后续运行：输入主密码解锁 / 忘记密码恢复
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QMouseEvent

from app.core.crypto import (
    generate_salt,
    derive_key,
    hash_master_password,
    verify_master_password,
    generate_recovery_key,
    hash_recovery_key,
    verify_recovery_key,
    DEFAULT_ITERATIONS,
)
from app.core.config_manager import ConfigManager
from app.ui.styles import (
    CARD_STYLE,
    CLOSE_BTN_STYLE,
    LINK_BTN_STYLE,
    BTN_STYLE,
    PRIMARY_BTN_STYLE,
    INPUT_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
    DIALOG_WIDTH,
    PRIMARY_COLOR,
)


def _toast(parent, message, level="info", duration=2500):
    """标题右侧自动消失的通知"""
    colors = {"info": "#323232", "error": "#e81123", "warn": "#d83b01"}
    bg = colors.get(level, "#323232")

    # 截断过长文字
    display = message if len(message) <= 25 else message[:25] + "..."

    label = QLabel(parent)
    label.setText(f" {display} ")
    label.setFont(QFont("Microsoft YaHei", 10))
    label.adjustSize()
    label.setFixedHeight(30)
    label.setStyleSheet(f"* {{ background: {bg}; color: white; border-radius: 4px; }}")

    label.move(280, 26)
    label.raise_()
    label.show()

    QTimer.singleShot(duration, label.deleteLater)


def _confirm(parent, title, message):
    """自定义确认对话框，返回 True/False"""
    dialog = QDialog(None)
    dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    dialog.setFixedSize(400, 200)
    dialog.setWindowTitle(title)
    dialog.setStyleSheet("""
        QDialog { background: white; }
        QLabel { color: #1a1a1a; background: transparent; }
        QPushButton {
            border-radius: 6px; padding: 8px 20px; font-size: 13px;
        }
    """)

    # 居中到父窗口
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


class RecoveryKeyDialog(QDialog):
    """恢复密钥显示对话框"""

    def __init__(self, recovery_key: str, parent=None):
        super().__init__(parent)
        self._recovery_key = recovery_key
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("恢复密钥")
        self.setFixedSize(DIALOG_WIDTH + 40, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 24, 32, 24)

        # 警告图标
        warning = QLabel("⚠️")
        warning.setFont(QFont("Microsoft YaHei", 28))
        warning.setAlignment(Qt.AlignCenter)
        warning.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(warning)

        # 提示文字
        hint = QLabel("请妥善保存以下恢复密钥，忘记主密码时可用于恢复")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hint.setFont(QFont("Microsoft YaHei", 11))
        hint.setStyleSheet("color: #666; background: transparent; border: none;")
        layout.addWidget(hint)

        # 恢复密钥显示
        key_label = QLabel(self._recovery_key)
        key_label.setFont(QFont("Consolas", 18, QFont.Bold))
        key_label.setAlignment(Qt.AlignCenter)
        key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        key_label.setStyleSheet(f"""
            QLabel {{
                color: {PRIMARY_COLOR};
                background: #f0f6ff;
                border: 2px dashed {PRIMARY_COLOR};
                border-radius: 8px;
                padding: 12px;
                letter-spacing: 4px;
            }}
        """)
        layout.addWidget(key_label)

        # 复制按钮
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.setFixedHeight(BTN_MIN_HEIGHT)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(BTN_STYLE)
        copy_btn.clicked.connect(self._copy_key)
        layout.addWidget(copy_btn, alignment=Qt.AlignCenter)

        # 确认按钮
        ok_btn = QPushButton("我已保存，继续")
        ok_btn.setFixedHeight(BTN_MIN_HEIGHT)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def _copy_key(self):
        from app.utils.clipboard import copy_to_clipboard
        copy_to_clipboard(self._recovery_key)
        _toast(self, "恢复密钥已复制到剪贴板")


class ForgotPasswordDialog(QDialog):
    """忘记密码对话框"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._new_key = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("忘记密码")
        self.setFixedSize(DIALOG_WIDTH, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(INPUT_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        # 标题
        title = QLabel("忘记主密码？")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title)

        # 方式1：恢复密钥
        section1 = QLabel("方式一：使用恢复密钥重置密码")
        section1.setStyleSheet("font-weight: 600; color: #333; font-size: 13px; background: transparent; margin-top: 8px;")
        layout.addWidget(section1)

        self._recovery_input = QLineEdit()
        self._recovery_input.setPlaceholderText("输入恢复密钥 (如: ABCD-1234-EFGH-5678)")
        self._recovery_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._recovery_input)

        self._new_password_input = QLineEdit()
        self._new_password_input.setEchoMode(QLineEdit.Password)
        self._new_password_input.setPlaceholderText("设置新主密码")
        self._new_password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._new_password_input)

        self._confirm_password_input = QLineEdit()
        self._confirm_password_input.setEchoMode(QLineEdit.Password)
        self._confirm_password_input.setPlaceholderText("确认新主密码")
        self._confirm_password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._confirm_password_input)

        reset_btn = QPushButton("重置密码")
        reset_btn.setFixedHeight(BTN_MIN_HEIGHT)
        reset_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(reset_btn)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e8e8e8;")
        layout.addWidget(separator)

        # 方式2：查看密码提示
        hint_btn = QPushButton("查看密码提示")
        hint_btn.setFixedHeight(BTN_MIN_HEIGHT)
        hint_btn.setStyleSheet(LINK_BTN_STYLE)
        hint_btn.clicked.connect(self._show_hint)
        layout.addWidget(hint_btn, alignment=Qt.AlignCenter)

        # 方式3：清除数据重新开始
        danger_btn = QPushButton("清除所有数据，重新开始")
        danger_btn.setFixedHeight(BTN_MIN_HEIGHT)
        danger_btn.setStyleSheet("""
            QPushButton {
                color: #e81123;
                border: none;
                background: transparent;
                font-size: 13px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        danger_btn.setCursor(Qt.PointingHandCursor)
        danger_btn.clicked.connect(self._on_reset_all)
        layout.addWidget(danger_btn, alignment=Qt.AlignCenter)

    def _on_reset(self):
        """使用恢复密钥重置密码"""
        recovery_key = self._recovery_input.text().strip().upper()
        new_password = self._new_password_input.text()
        confirm = self._confirm_password_input.text()

        if not recovery_key:
            _toast(self, "请输入恢复密钥", "warn")
            return

        if len(new_password) < 6:
            _toast(self, "新密码至少 6 个字符", "warn")
            return

        if new_password != confirm:
            _toast(self, "两次输入的密码不一致", "warn")
            return

        stored_hash = self._config.get("recovery_key_hash")
        if not stored_hash:
            _toast(self, "未设置恢复密钥", "error")
            return

        try:
            salt = self._config.get_salt()
            iterations = self._config.get_iterations()
        except ValueError as e:
            _toast(self, str(e), "error")
            return

        if not verify_recovery_key(recovery_key, salt, stored_hash, iterations):
            _toast(self, "恢复密钥错误", "error")
            return

        # 警告：重置密码后旧数据将无法解密
        if not _confirm(
            self,
            "警告",
            "重置主密码后，之前保存的所有密码数据将无法解密。\n\n"
            "这是由于密码加密机制的限制。\n"
            "确定要继续吗？",
        ):
            return

        new_salt = generate_salt()
        new_key = derive_key(new_password, new_salt, DEFAULT_ITERATIONS)
        new_hash = hash_master_password(new_password, new_salt, DEFAULT_ITERATIONS)

        self._config.set("master_password_hash", new_hash)
        self._config.set("salt", new_salt.hex())
        self._config.set("kdf_iterations", str(DEFAULT_ITERATIONS))

        new_recovery = generate_recovery_key()
        new_recovery_hash = hash_recovery_key(new_recovery, new_salt, DEFAULT_ITERATIONS)
        self._config.set("recovery_key_hash", new_recovery_hash)

        self._new_key = new_key
        self._new_recovery = new_recovery

        _toast(self, "密码已重置")
        self.accept()

    def _show_hint(self):
        hint = self._config.get("password_hint")
        if not hint:
            _toast(self, "未设置密码提示", "warn")
            return
        # 自定义弹框，样式与 _confirm 统一
        dialog = QDialog(None)
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        dialog.setFixedSize(400, 200)
        dialog.setWindowTitle("密码提示")
        dialog.setStyleSheet("""
            QDialog { background: white; }
            QLabel { color: #1a1a1a; background: transparent; }
            QPushButton {
                background: #0078d4; color: white; border: none;
                border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #106ebe; }
        """)

        # 居中到父窗口
        parent = self.parent() or self
        if parent:
            px = parent.x() + (parent.width() - 400) // 2
            py = parent.y() + (parent.height() - 200) // 2
            dialog.move(px, py)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 20, 28, 20)

        title = QLabel("密码提示")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.DemiBold))
        layout.addWidget(title)

        hint_label = QLabel(hint)
        hint_label.setFont(QFont("Microsoft YaHei", 12))
        hint_label.setWordWrap(True)
        hint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hint_label.setStyleSheet("color: #333; background: #f8f8f8; border: 1px solid #eee; border-radius: 6px; padding: 10px;")
        layout.addWidget(hint_label)

        layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.setFixedHeight(BTN_MIN_HEIGHT)
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignRight)

        dialog.exec_()

    def _on_reset_all(self):
        if _confirm(
            self,
            "确认清除",
            "此操作将删除所有密码数据，不可恢复！\n\n确定要继续吗？",
        ):
            self._config.clear_all()
            self.accept()

    def get_new_key(self):
        return self._new_key

    def get_new_recovery(self):
        return getattr(self, "_new_recovery", None)


class LoginWindow(QWidget):
    """登录窗口"""

    login_success = pyqtSignal(bytes)
    need_restart = pyqtSignal()

    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self._is_first_run = not self._config.has_master_password()
        self._drag_pos = None
        if self._is_first_run:
            self._show_welcome()
        self._setup_ui()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        event.accept()

    def _show_info(self, message: str):
        _toast(self, message)

    def _show_error(self, message: str):
        _toast(self, message, "error")

    def _show_welcome(self):
        """首次使用弹出欢迎提示"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setFixedSize(DIALOG_WIDTH, 440)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("welcomeCard")
        card.setStyleSheet(f"#welcomeCard {{{CARD_STYLE}}}")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setSpacing(16)
        layout.setContentsMargins(36, 32, 36, 32)

        # 标题
        icon = QLabel("\U0001f510")
        icon.setFont(QFont("Microsoft YaHei", 36))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon)

        title = QLabel("欢迎使用密码管理器")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
        layout.addWidget(title)

        layout.addSpacing(8)

        # 特性说明
        features = [
            ("\U0001f4f4", "完全离线", "不联网，不上传任何数据"),
            ("\U0001f4be", "仅存本地", "数据保存在你的电脑上"),
            ("\U0001f512", "AES-256 加密", "密码高强度加密存储"),
        ]

        for emoji, title_text, desc_text in features:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.setAlignment(Qt.AlignCenter)

            emoji_label = QLabel(emoji)
            emoji_label.setFont(QFont("Microsoft YaHei", 20))
            emoji_label.setFixedSize(36, 36)
            emoji_label.setAlignment(Qt.AlignCenter)
            emoji_label.setStyleSheet("background: transparent; border: none;")
            row.addWidget(emoji_label)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)

            ft = QLabel(title_text)
            ft.setFont(QFont("Microsoft YaHei", 12, QFont.DemiBold))
            ft.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
            text_col.addWidget(ft)

            fd = QLabel(desc_text)
            fd.setFont(QFont("Microsoft YaHei", 10))
            fd.setStyleSheet("color: #888; background: transparent; border: none;")
            text_col.addWidget(fd)

            row.addLayout(text_col)
            row.addStretch()
            layout.addLayout(row)

        layout.addSpacing(8)

        # 开始按钮
        start_btn = QPushButton("开始使用")
        start_btn.setFixedHeight(BTN_MIN_HEIGHT)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        start_btn.clicked.connect(dialog.accept)
        layout.addWidget(start_btn)

        dialog.exec_()

    def _setup_ui(self):
        self.setWindowTitle("密码管理器")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(DIALOG_WIDTH, 420 if self._is_first_run else 380)
        self.setStyleSheet("background: #f5f5f5;")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # 卡片容器
        card = QWidget()
        card.setObjectName("loginCard")
        card.setStyleSheet(f"#loginCard {{{CARD_STYLE}}}")
        outer_layout.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(36, 20, 36, 28)

        # 顶部栏：关闭按钮
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)
        layout.addLayout(top_bar)

        # 图标
        from app.ui.icon_gen import create_app_icon
        icon_label = QLabel()
        icon_label.setFixedSize(72, 72)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_label.setPixmap(create_app_icon().pixmap(64, 64))
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # 标题（渐变效果）
        title = QLabel("密码管理器")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:0.5 #00b4d8, stop:1 #0078d4);
                padding: 4px 0;
            }
        """)
        layout.addWidget(title)

        # 提示文字
        subtitle_text = "首次使用，请设置主密码" if self._is_first_run else "请输入主密码解锁"
        subtitle = QLabel(subtitle_text)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("Microsoft YaHei", 10))
        subtitle.setStyleSheet("color: #999; background: transparent; border: none;")
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # 密码输入框
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setPlaceholderText("输入主密码")
        self._password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._password_input.setStyleSheet(INPUT_STYLE)
        self._password_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._password_input)

        # 确认密码输入框
        self._confirm_input = QLineEdit()
        self._confirm_input.setEchoMode(QLineEdit.Password)
        self._confirm_input.setPlaceholderText("确认主密码")
        self._confirm_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._confirm_input.setStyleSheet(INPUT_STYLE)
        self._confirm_input.returnPressed.connect(self._on_submit)
        if not self._is_first_run:
            self._confirm_input.hide()
        layout.addWidget(self._confirm_input)

        # 密码提示
        self._hint_input = QLineEdit()
        self._hint_input.setPlaceholderText("设置密码提示（可选）")
        self._hint_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._hint_input.setStyleSheet(INPUT_STYLE)
        if not self._is_first_run:
            self._hint_input.hide()
        else:
            layout.addWidget(self._hint_input)

        # 提交按钮
        btn_text = "设置主密码" if self._is_first_run else "解锁"
        self._submit_btn = QPushButton(btn_text)
        self._submit_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._submit_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

        # 忘记密码
        if not self._is_first_run:
            forgot_btn = QPushButton("忘记密码？")
            forgot_btn.setCursor(Qt.PointingHandCursor)
            forgot_btn.setStyleSheet(LINK_BTN_STYLE)
            forgot_btn.clicked.connect(self._on_forgot)
            layout.addWidget(forgot_btn, alignment=Qt.AlignCenter)

    def _on_submit(self):
        password = self._password_input.text()

        if not password:
            self._show_error("请输入主密码")
            return

        if len(password) < 6:
            self._show_error("主密码至少 6 个字符")
            return

        if self._is_first_run:
            self._handle_first_run(password)
        else:
            self._handle_login(password)

    def _handle_first_run(self, password: str):
        confirm = self._confirm_input.text()
        if password != confirm:
            self._show_error("两次输入的密码不一致")
            return

        salt = generate_salt()
        key = derive_key(password, salt, DEFAULT_ITERATIONS)
        master_hash = hash_master_password(password, salt, DEFAULT_ITERATIONS)

        recovery_key = generate_recovery_key()
        recovery_hash = hash_recovery_key(recovery_key, salt, DEFAULT_ITERATIONS)

        hint = self._hint_input.text().strip()

        self._config.set("master_password_hash", master_hash)
        self._config.set("salt", salt.hex())
        self._config.set("kdf_iterations", str(DEFAULT_ITERATIONS))
        self._config.set("version", "1")
        self._config.set("recovery_key_hash", recovery_hash)
        if hint:
            self._config.set("password_hint", hint)

        RecoveryKeyDialog(recovery_key).exec_()
        self.login_success.emit(key)

    def _handle_login(self, password: str):
        stored_hash = self._config.get("master_password_hash")
        try:
            salt = self._config.get_salt()
            iterations = self._config.get_iterations()
        except ValueError:
            self._show_error("配置损坏，请重新设置")
            return

        if verify_master_password(password, salt, stored_hash, iterations):
            key = derive_key(password, salt, iterations)
            self.login_success.emit(key)
        else:
            self._show_error("主密码错误")
            self._password_input.clear()
            self._password_input.setFocus()

    def _on_forgot(self):
        dialog = ForgotPasswordDialog(self._config, self)
        if dialog.exec_():
            new_key = dialog.get_new_key()
            if new_key:
                new_recovery = dialog.get_new_recovery()
                RecoveryKeyDialog(new_recovery).exec_()
                self.login_success.emit(new_key)
            else:
                self.need_restart.emit()
