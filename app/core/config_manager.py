"""配置管理器

独立于加密密钥，用于读取/写入配置表。
登录窗口使用此类，不需要加密密钥。
"""

import sqlite3
from typing import Optional

from app.utils.paths import get_db_path


class ConfigManager:
    """配置管理器（无需加密密钥）"""

    def __init__(self):
        self._db_path = get_db_path()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_connection()
        self._init_table()

    def _init_connection(self):
        """建立数据库连接"""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

    def _init_table(self):
        """初始化配置表"""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def get(self, key: str) -> Optional[str]:
        """获取配置值"""
        row = self._conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        """设置配置值"""
        self._conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()

    def has_master_password(self) -> bool:
        """是否已设置主密码"""
        return self.get("master_password_hash") is not None

    def clear_all(self) -> None:
        """清除所有数据（配置表和条目表）"""
        self._conn.execute("DELETE FROM config")
        self._conn.execute("DELETE FROM entries")
        self._conn.commit()

    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
