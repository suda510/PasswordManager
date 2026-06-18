"""AppData 路径管理

确保应用数据目录存在，提供数据库文件路径。
"""

import os
from pathlib import Path


# 应用名称
APP_NAME = "PasswordManager"


def get_data_dir() -> Path:
    """获取应用数据目录

    Windows: %APPDATA%/PasswordManager
    其他平台: ~/.PasswordManager

    Returns:
        数据目录路径（已创建）
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~")

    data_dir = Path(base) / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """获取数据库文件路径

    Returns:
        data.enc 文件路径
    """
    return get_data_dir() / "data.enc"
