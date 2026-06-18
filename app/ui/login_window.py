"""主密码登录窗口

首次运行：设置主密码 + 生成恢复密钥
后续运行：输入主密码解锁 / 忘记密码恢复
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QMouseEvent

from qfluentwidgets import (
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    PushButton,
    CaptionLabel,
    InfoBar,
    InfoBarPosition,
)

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
    TITLE_STYLE,
    SUBTITLE_STYLE,
    CLOSE_BTN_STYLE,
    LINK_BTN_STYLE,
    INPUT_MIN_HEIGHT,
    BTN_MIN_HEIGHT,
    DIALOG_WIDTH,
    PRIMARY_COLOR,
    TEXT_MUTED,
)


class RecoveryKeyDialog(QDialog):
    """恢复密钥显示对话框"""

    def __init__(self, recovery_key: str, parent=None):
        super().__init__(parent)
        self._recovery_key = recovery_key
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("恢复密钥")
        self.setFixedSize(DIALOG_WIDTH, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        # 警告图标
        warning = QLabel("⚠️")
        warning.setFont(QFont("Microsoft YaHei", 32))
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)

        # 提示文字
        hint = QLabel("请妥善保存以下恢复密钥，忘记主密码时可用于恢复")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: #666; font-size: 13px; background: transparent;")
        layout.addWidget(hint)

        # 恢复密钥显示
        key_label = QLabel(self._recovery_key)
        key_label.setFont(QFont("Consolas", 22, QFont.Bold))
        key_label.setAlignment(Qt.AlignCenter)
        key_label.setStyleSheet(f"""
            QLabel {{
                color: {PRIMARY_COLOR};
                background: #f0f6ff;
                border: 2px dashed {PRIMARY_COLOR};
                border-radius: 8px;
                padding: 14px;
                letter-spacing: 6px;
            }}
        """)
        layout.addWidget(key_label)

        # 复制按钮
        copy_btn = PushButton("复制到剪贴板")
        copy_btn.setFixedHeight(BTN_MIN_HEIGHT)
        copy_btn.clicked.connect(self._copy_key)
        layout.addWidget(copy_btn, alignment=Qt.AlignCenter)

        # 确认按钮
        ok_btn = PrimaryPushButton("我已保存，继续")
        ok_btn.setFixedHeight(BTN_MIN_HEIGHT)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def _copy_key(self):
        from app.utils.clipboard import copy_to_clipboard
        copy_to_clipboard(self._recovery_key)
        InfoBar.success(
            title="成功",
            content="恢复密钥已复制到剪贴板",
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )


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
        section1.setStyleSheet(f"font-weight: 600; color: #333; font-size: 13px; background: transparent; margin-top: 8px;")
        layout.addWidget(section1)

        self._recovery_input = LineEdit()
        self._recovery_input.setPlaceholderText("输入恢复密钥 (如: ABCD-1234-EFGH-5678)")
        self._recovery_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._recovery_input)

        self._new_password_input = PasswordLineEdit()
        self._new_password_input.setPlaceholderText("设置新主密码")
        self._new_password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._new_password_input)

        self._confirm_password_input = PasswordLineEdit()
        self._confirm_password_input.setPlaceholderText("确认新主密码")
        self._confirm_password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        layout.addWidget(self._confirm_password_input)

        reset_btn = PrimaryPushButton("重置密码")
        reset_btn.setFixedHeight(BTN_MIN_HEIGHT)
        reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(reset_btn)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e8e8e8;")
        layout.addWidget(separator)

        # 方式2：查看密码提示
        hint_btn = PushButton("查看密码提示")
        hint_btn.setFixedHeight(BTN_MIN_HEIGHT)
        hint_btn.setStyleSheet(LINK_BTN_STYLE)
        hint_btn.clicked.connect(self._show_hint)
        layout.addWidget(hint_btn, alignment=Qt.AlignCenter)

        # 方式3：清除数据重新开始
        danger_btn = PushButton("清除所有数据，重新开始")
        danger_btn.setFixedHeight(BTN_MIN_HEIGHT)
        danger_btn.setStyleSheet(f"color: #e81123; border: none; background: transparent; font-size: 13px;")
        danger_btn.clicked.connect(self._on_reset_all)
        layout.addWidget(danger_btn, alignment=Qt.AlignCenter)

    def _on_reset(self):
        """使用恢复密钥重置密码"""
        recovery_key = self._recovery_input.text().strip().upper()
        new_password = self._new_password_input.text()
        confirm = self._confirm_password_input.text()

        if not recovery_key:
            InfoBar.warning(title="提示", content="请输入恢复密钥", position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        if len(new_password) < 6:
            InfoBar.warning(title="提示", content="新密码至少 6 个字符", position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        if new_password != confirm:
            InfoBar.warning(title="提示", content="两次输入的密码不一致", position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        stored_hash = self._config.get("recovery_key_hash")
        salt = bytes.fromhex(self._config.get("salt"))
        iterations = int(self._config.get("kdf_iterations"))

        if not stored_hash:
            InfoBar.error(title="错误", content="未设置恢复密钥", position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        if not verify_recovery_key(recovery_key, salt, stored_hash, iterations):
            InfoBar.error(title="错误", content="恢复密钥错误", position=InfoBarPosition.TOP, duration=2000, parent=self)
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

        InfoBar.success(title="成功", content="密码已重置", position=InfoBarPosition.TOP, duration=2000, parent=self)
        self.accept()

    def _show_hint(self):
        hint = self._config.get("password_hint")
        if hint:
            InfoBar.info(title="密码提示", content=hint, position=InfoBarPosition.TOP, duration=5000, parent=self)
        else:
            InfoBar.warning(title="提示", content="未设置密码提示", position=InfoBarPosition.TOP, duration=2000, parent=self)

    def _on_reset_all(self):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.warning(
            self,
            "确认清除",
            "此操作将删除所有密码数据，不可恢复！\n\n确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
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

    def _setup_ui(self):
        self.setWindowTitle("密码管理器")
        self.setFixedSize(DIALOG_WIDTH, 420 if self._is_first_run else 380)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

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
        icon_label.setPixmap(create_app_icon().pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

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
        subtitle = CaptionLabel(subtitle_text)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(SUBTITLE_STYLE)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # 密码输入框
        self._password_input = PasswordLineEdit()
        self._password_input.setPlaceholderText("输入主密码")
        self._password_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._password_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._password_input)

        # 确认密码输入框
        self._confirm_input = PasswordLineEdit()
        self._confirm_input.setPlaceholderText("确认主密码")
        self._confirm_input.setFixedHeight(INPUT_MIN_HEIGHT)
        self._confirm_input.returnPressed.connect(self._on_submit)
        if not self._is_first_run:
            self._confirm_input.hide()
        layout.addWidget(self._confirm_input)

        # 密码提示
        self._hint_input = LineEdit()
        self._hint_input.setPlaceholderText("设置密码提示（可选）")
        self._hint_input.setFixedHeight(INPUT_MIN_HEIGHT)
        if not self._is_first_run:
            self._hint_input.hide()
        else:
            layout.addWidget(self._hint_input)

        # 提交按钮
        btn_text = "设置主密码" if self._is_first_run else "解锁"
        self._submit_btn = PrimaryPushButton(btn_text)
        self._submit_btn.setFixedHeight(BTN_MIN_HEIGHT)
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

        # 忘记密码
        if not self._is_first_run:
            forgot_btn = PushButton("忘记密码？")
            forgot_btn.setCursor(Qt.PointingHandCursor)
            forgot_btn.setStyleSheet(LINK_BTN_STYLE)
            forgot_btn.clicked.connect(self._on_forgot)
            layout.addWidget(forgot_btn, alignment=Qt.AlignCenter)

    def _show_error(self, message: str):
        InfoBar.error(
            title="错误",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

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

        RecoveryKeyDialog(recovery_key, self).exec_()
        self.login_success.emit(key)

    def _handle_login(self, password: str):
        stored_hash = self._config.get("master_password_hash")
        salt = bytes.fromhex(self._config.get("salt"))
        iterations = int(self._config.get("kdf_iterations"))

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
                RecoveryKeyDialog(new_recovery, self).exec_()
                self.login_success.emit(new_key)
            else:
                self.need_restart.emit()
