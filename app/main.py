"""密码管理器 入口"""

import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont


def _set_windows_appusermodelid():
    """设置 Windows AppUserModelID，使任务栏正确显示自定义图标"""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "PasswordManager.App.1.0"
        )


def main():
    """应用入口"""
    _set_windows_appusermodelid()

    app = QApplication(sys.argv)
    app.setApplicationName("密码管理器")

    # 全局字体
    font = QFont("Microsoft YaHei", 11)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    from app.ui.icon_gen import create_app_icon
    app.setWindowIcon(create_app_icon())

    from app.core.config_manager import ConfigManager
    from app.core.db import Database
    from app.ui.login_window import LoginWindow
    from app.ui.main_window import MainWindow

    config = ConfigManager()
    windows = {}

    def create_login_window():
        """创建登录窗口"""
        login_window = LoginWindow(config)
        windows["login"] = login_window

        def on_login_success(key: bytes):
            login_window.close()
            db = Database(key)
            main_window = MainWindow(db, config)
            windows["main"] = main_window
            main_window.show()

            def on_logout():
                """修改密码后重新登录"""
                main_window.close()
                db.close()
                nonlocal config
                config.close()
                config = ConfigManager()
                create_login_window()

            main_window.logout.connect(on_logout)

        def on_need_restart():
            """清除数据后重新创建登录窗口"""
            login_window.close()
            # 重新打开配置管理器
            nonlocal config
            config.close()
            config = ConfigManager()
            create_login_window()

        login_window.login_success.connect(on_login_success)
        login_window.need_restart.connect(on_need_restart)
        login_window.show()

    create_login_window()

    ret = app.exec_()
    config.close()
    sys.exit(ret)


if __name__ == "__main__":
    main()
