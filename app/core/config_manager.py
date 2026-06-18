"""配置管理器

独立于加密密钥，用于读取/写入配置表。
登录窗口使用此类，不需要加密密钥。
"""

import json
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

    # ── 自定义分组管理 ──

    def get_custom_groups(self) -> list[str]:
        """获取用户自定义分组列表"""
        raw = self.get("custom_groups")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_custom_groups(self, groups: list[str]) -> None:
        """保存用户自定义分组列表"""
        self.set("custom_groups", json.dumps(groups, ensure_ascii=False))

    def add_custom_group(self, name: str) -> bool:
        """添加自定义分组，已存在返回 False"""
        groups = self.get_custom_groups()
        if name in groups:
            return False
        groups.append(name)
        groups.sort(key=str.casefold)
        self.set_custom_groups(groups)
        return True

    def rename_custom_group(self, old_name: str, new_name: str) -> None:
        """重命名自定义分组"""
        groups = self.get_custom_groups()
        if old_name in groups:
            groups = [new_name if g == old_name else g for g in groups]
            groups.sort(key=str.casefold)
            self.set_custom_groups(groups)

    def delete_custom_group(self, name: str) -> None:
        """删除自定义分组"""
        groups = self.get_custom_groups()
        groups = [g for g in groups if g != name]
        self.set_custom_groups(groups)

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
