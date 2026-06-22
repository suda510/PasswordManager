"""主窗口的大型对话框（从 MainWindow 提取）

每个函数接收 (parent, db, config, ...) 参数，不依赖 MainWindow 实例。
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from app.core.crypto import (
    generate_salt,
    derive_key_and_hash,
    verify_master_password,
    DEFAULT_ITERATIONS,
)
from app.ui.notification import show_toast as _toast, confirm_dialog as _confirm
from app.ui.styles import (
    LABEL_STYLE, INPUT_STYLE, BTN_STYLE, PRIMARY_BTN_STYLE,
    GROUP_LIST_STYLE, INPUT_MIN_HEIGHT, BTN_MIN_HEIGHT,
)


def show_manage_groups(parent, db, config, icon, get_all_groups, on_changed):
    """分组管理对话框"""
    dialog = QDialog(parent)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("管理分组")
    dialog.setFixedSize(360, 420)
    dialog.setWindowIcon(icon)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)
    layout.setContentsMargins(24, 20, 24, 20)

    title = QLabel("管理分组")
    title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
    title.setStyleSheet("color: #1a1a1a; background: transparent;")
    layout.addWidget(title)

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

    group_list = QListWidget()
    group_list.setStyleSheet(GROUP_LIST_STYLE)
    layout.addWidget(group_list, stretch=1)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)

    rename_btn = QPushButton("重命名")
    rename_btn.setFixedHeight(BTN_MIN_HEIGHT)
    rename_btn.setStyleSheet(BTN_STYLE)
    rename_btn.setCursor(Qt.PointingHandCursor)
    rename_btn.setEnabled(False)

    delete_btn = QPushButton("删除分组")
    delete_btn.setFixedHeight(BTN_MIN_HEIGHT)
    delete_btn.setStyleSheet("""
        QPushButton {
            color: #dc2626;
            background: #fff0f0;
            border: 1px solid #ffd0d0;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
        }
        QPushButton:hover { background: #ffe0e0; }
    """)
    delete_btn.setCursor(Qt.PointingHandCursor)
    delete_btn.setEnabled(False)

    btn_row.addStretch()
    btn_row.addWidget(rename_btn)
    btn_row.addWidget(delete_btn)
    layout.addLayout(btn_row)

    def refresh_list():
        group_list.clear()
        for g in get_all_groups():
            count = len(db.get_entries_by_group(g))
            item = QListWidgetItem(f"{g}  ({count} 个条目)")
            item.setData(Qt.UserRole, g)
            group_list.addItem(item)

    refresh_list()

    def on_selection_changed():
        has_sel = group_list.currentItem() is not None
        rename_btn.setEnabled(has_sel)
        delete_btn.setEnabled(has_sel)

    group_list.currentItemChanged.connect(lambda: on_selection_changed())

    def on_add():
        name = new_group_input.text().strip()
        if not name:
            return
        if name in get_all_groups():
            _toast(dialog, "该分组已存在", "warn")
            return
        config.add_custom_group(name)
        new_group_input.clear()
        on_changed()
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
        if new_name in get_all_groups():
            _toast(dialog, "该分组名已存在", "warn")
            return
        db.rename_group(old_name, new_name)
        config.rename_custom_group(old_name, new_name)
        on_changed()
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
            db.delete_group(group_name)
            config.delete_custom_group(group_name)
            on_changed()
            refresh_list()
            _toast(dialog, f'分组 "{group_name}" 已删除')

    delete_btn.clicked.connect(on_delete)

    dialog.exec_()


def show_export_dialog(parent, db, config, icon):
    """导出数据对话框"""
    verify_dialog = QDialog(parent)
    verify_dialog.setWindowFlags(verify_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    verify_dialog.setWindowTitle("身份验证")
    verify_dialog.setFixedSize(380, 220)
    verify_dialog.setWindowIcon(icon)
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

    stored_hash = config.get("master_password_hash")
    try:
        salt = config.get_salt()
        iterations = config.get_iterations()
    except ValueError as e:
        _toast(parent, str(e), "error")
        return

    if not verify_master_password(password, salt, stored_hash, iterations):
        _toast(parent, "主密码错误", "error")
        return

    reply = _confirm(
        parent,
        "安全警告",
        "即将导出所有密码为明文 CSV 文件。\n\n"
        "该文件包含所有账号密码的明文信息，\n"
        "请妥善保管，使用后建议立即删除。",
    )
    if not reply:
        return

    path, _ = QFileDialog.getSaveFileName(
        parent, "导出数据", "data_export.csv",
        "CSV 文件 (*.csv);;所有文件 (*)",
    )
    if not path:
        return

    try:
        csv_data = db.export_csv()
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(csv_data)
        _toast(parent, "导出成功")
    except Exception:
        _toast(parent, "导出失败", "error")


def show_change_password_dialog(parent, config, db, icon):
    """修改主密码对话框，返回 True 表示需要 logout"""
    dialog = QDialog(parent)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("修改主密码")
    dialog.setWindowIcon(icon)
    dialog.setFixedSize(440, 350)
    dialog.setStyleSheet(INPUT_STYLE)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(14)
    layout.setContentsMargins(32, 28, 32, 28)

    title = QLabel("修改主密码")
    title.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
    title.setStyleSheet("color: #1a1a1a; background: transparent;")
    layout.addWidget(title)

    cur_label = QLabel("当前密码")
    cur_label.setStyleSheet(LABEL_STYLE)
    layout.addWidget(cur_label)
    cur_input = QLineEdit()
    cur_input.setEchoMode(QLineEdit.Password)
    cur_input.setPlaceholderText("输入当前主密码")
    cur_input.setFixedHeight(INPUT_MIN_HEIGHT)
    layout.addWidget(cur_input)

    new_label = QLabel("新密码")
    new_label.setStyleSheet(LABEL_STYLE)
    layout.addWidget(new_label)
    new_input = QLineEdit()
    new_input.setEchoMode(QLineEdit.Password)
    new_input.setPlaceholderText("输入新主密码")
    new_input.setFixedHeight(INPUT_MIN_HEIGHT)
    layout.addWidget(new_input)

    confirm_label = QLabel("确认新密码")
    confirm_label.setStyleSheet(LABEL_STYLE)
    layout.addWidget(confirm_label)
    confirm_input = QLineEdit()
    confirm_input.setEchoMode(QLineEdit.Password)
    confirm_input.setPlaceholderText("再次输入新主密码")
    confirm_input.setFixedHeight(INPUT_MIN_HEIGHT)
    layout.addWidget(confirm_input)

    layout.addSpacing(8)

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

        stored_hash = config.get("master_password_hash")
        try:
            salt = config.get_salt()
            iterations = config.get_iterations()
        except ValueError as e:
            _toast(dialog, str(e), "error")
            return

        if not verify_master_password(cur_password, salt, stored_hash, iterations):
            _toast(dialog, "当前密码错误", "error")
            return

        new_salt = generate_salt()
        new_key, new_hash = derive_key_and_hash(new_password, new_salt, DEFAULT_ITERATIONS)

        try:
            db.rekey(new_key)
        except Exception:
            _toast(dialog, "数据加密失败，请重试", "error")
            return

        config.set("master_password_hash", new_hash)
        config.set("salt", new_salt.hex())
        config.set("kdf_iterations", str(DEFAULT_ITERATIONS))

        _toast(dialog, "主密码已修改，请重新登录")
        dialog.accept()

    save_btn.clicked.connect(on_save)

    accepted = [False]
    _orig_accept = dialog.accept

    def _mark_accept():
        accepted[0] = True
        _orig_accept()

    dialog.accept = _mark_accept

    dialog.exec_()
    return accepted[0]


def show_about_dialog(parent, icon):
    """关于对话框"""
    dialog = QDialog(parent)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setWindowTitle("关于")
    dialog.setFixedSize(380, 400)
    dialog.setWindowIcon(icon)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)
    layout.setContentsMargins(28, 24, 28, 24)

    icon_label = QLabel("\U0001f510")
    icon_label.setFont(QFont("Microsoft YaHei", 32))
    icon_label.setAlignment(Qt.AlignCenter)
    icon_label.setStyleSheet("background: transparent; border: none;")
    layout.addWidget(icon_label)

    name_label = QLabel("密码管理器")
    name_label.setFont(QFont("Microsoft YaHei", 16, QFont.DemiBold))
    name_label.setAlignment(Qt.AlignCenter)
    name_label.setStyleSheet("color: #1a1a1a; background: transparent; border: none;")
    layout.addWidget(name_label)

    ver_label = QLabel("v1.0.0")
    ver_label.setFont(QFont("Microsoft YaHei", 11))
    ver_label.setAlignment(Qt.AlignCenter)
    ver_label.setStyleSheet("color: #999; background: transparent; border: none;")
    layout.addWidget(ver_label)

    layout.addSpacing(4)

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

    desc_label = QLabel("你的密码，只属于你")
    desc_label.setFont(QFont("Microsoft YaHei", 10))
    desc_label.setAlignment(Qt.AlignCenter)
    desc_label.setStyleSheet("color: #999; background: transparent; border: none;")
    layout.addWidget(desc_label)

    layout.addSpacing(8)

    link_label = QLabel('<a href="https://github.com/suda510/PasswordManager" style="color:#2563eb;text-decoration:none;">GitHub 仓库</a>')
    link_label.setFont(QFont("Microsoft YaHei", 11))
    link_label.setAlignment(Qt.AlignCenter)
    link_label.setOpenExternalLinks(True)
    link_label.setStyleSheet("background: transparent; border: none;")
    layout.addWidget(link_label)

    layout.addStretch()

    dialog.exec_()
