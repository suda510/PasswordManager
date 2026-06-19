"""SQLite 数据层

管理数据库连接、建表和 CRUD 操作。
所有密码字段在存储前加密，读取后解密。
"""

import csv
import io
import sqlite3
from typing import Optional

from app.core.models import Entry
from app.core.crypto import encrypt_field, decrypt_field
from app.utils.paths import get_data_dir, get_db_path


class Database:
    """数据库管理器"""

    def __init__(self, encryption_key: bytes):
        """初始化数据库连接

        Args:
            encryption_key: 用于加密/解密字段的密钥
        """
        self._key = encryption_key
        self._db_path = get_db_path()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_connection()
        self._init_tables()

    def _init_connection(self):
        """建立数据库连接"""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

    def _init_tables(self):
        """初始化数据库表"""
        cursor = self._conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                username_nonce TEXT,
                username_cipher TEXT,
                password_nonce TEXT,
                password_cipher TEXT,
                url TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                "group" TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 迁移：为旧表添加 group 列
        cursor.execute("PRAGMA table_info(entries)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "group" not in columns:
            cursor.execute('ALTER TABLE entries ADD COLUMN "group" TEXT DEFAULT \'\'')
            self._conn.commit()

        self._conn.commit()

    def _encrypt_entry_fields(self, entry: Entry) -> dict:
        """加密条目中的敏感字段"""
        username_enc = encrypt_field(self._key, entry.username)
        password_enc = encrypt_field(self._key, entry.password)
        return {
            "id": entry.id,
            "title": entry.title,
            "username_nonce": username_enc["nonce"],
            "username_cipher": username_enc["ciphertext"],
            "password_nonce": password_enc["nonce"],
            "password_cipher": password_enc["ciphertext"],
            "url": entry.url,
            "notes": entry.notes,
            "group": entry.group,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    def _decrypt_entry_row(self, row: sqlite3.Row) -> Entry:
        """解密数据库行到 Entry 对象"""
        username = decrypt_field(self._key, row["username_nonce"], row["username_cipher"])
        password = decrypt_field(self._key, row["password_nonce"], row["password_cipher"])
        return Entry(
            id=row["id"],
            title=row["title"],
            username=username,
            password=password,
            url=row["url"],
            notes=row["notes"],
            group=row["group"] if "group" in row.keys() else "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_entry(self, entry: Entry) -> Entry:
        """新增条目

        Args:
            entry: 要添加的条目

        Returns:
            添加的条目
        """
        data = self._encrypt_entry_fields(entry)
        self._conn.execute(
            """INSERT INTO entries
               (id, title, username_nonce, username_cipher,
                password_nonce, password_cipher, url, notes, "group",
                created_at, updated_at)
               VALUES (:id, :title, :username_nonce, :username_cipher,
                       :password_nonce, :password_cipher, :url, :notes, :group,
                       :created_at, :updated_at)""",
            data,
        )
        self._conn.commit()
        return entry

    def update_entry(self, entry: Entry) -> Entry:
        """更新条目

        Args:
            entry: 要更新的条目（根据 id 匹配）

        Returns:
            更新后的条目

        Raises:
            ValueError: 条目不存在
        """
        data = self._encrypt_entry_fields(entry)
        cursor = self._conn.execute(
            """UPDATE entries SET
               title = :title,
               username_nonce = :username_nonce,
               username_cipher = :username_cipher,
               password_nonce = :password_nonce,
               password_cipher = :password_cipher,
               url = :url,
               notes = :notes,
               "group" = :group,
               updated_at = :updated_at
               WHERE id = :id""",
            data,
        )
        if cursor.rowcount == 0:
            raise ValueError(f"条目不存在: {entry.id}")
        self._conn.commit()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        """删除条目

        Args:
            entry_id: 条目 ID

        Raises:
            ValueError: 条目不存在
        """
        cursor = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"条目不存在: {entry_id}")
        self._conn.commit()

    def get_entry(self, entry_id: str) -> Optional[Entry]:
        """获取单个条目

        Args:
            entry_id: 条目 ID

        Returns:
            条目对象，不存在返回 None
        """
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            return None
        return self._decrypt_entry_row(row)

    def get_all_entries(self) -> list[Entry]:
        """获取所有条目

        Returns:
            条目列表
        """
        rows = self._conn.execute(
            "SELECT * FROM entries ORDER BY title COLLATE NOCASE"
        ).fetchall()
        return [self._decrypt_entry_row(row) for row in rows]

    def search_entries(self, keyword: str) -> list[Entry]:
        """按标题搜索条目

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的条目列表
        """
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE title LIKE ? ORDER BY title COLLATE NOCASE",
            (pattern,),
        ).fetchall()
        return [self._decrypt_entry_row(row) for row in rows]

    def get_groups(self) -> list[str]:
        """获取所有分组名称

        Returns:
            去重后的分组列表（按字母排序），不含空分组
        """
        rows = self._conn.execute(
            'SELECT DISTINCT "group" FROM entries WHERE "group" != \'\' ORDER BY "group" COLLATE NOCASE'
        ).fetchall()
        return [row["group"] for row in rows]

    def get_entries_by_group(self, group: str) -> list[Entry]:
        """按分组获取条目

        Args:
            group: 分组名称

        Returns:
            该分组下的条目列表
        """
        rows = self._conn.execute(
            'SELECT * FROM entries WHERE "group" = ? ORDER BY title COLLATE NOCASE',
            (group,),
        ).fetchall()
        return [self._decrypt_entry_row(row) for row in rows]

    def rename_group(self, old_name: str, new_name: str) -> int:
        """重命名分组

        Args:
            old_name: 旧分组名
            new_name: 新分组名

        Returns:
            受影响的条目数
        """
        cursor = self._conn.execute(
            'UPDATE entries SET "group" = ? WHERE "group" = ?',
            (new_name, old_name),
        )
        self._conn.commit()
        return cursor.rowcount

    def delete_group(self, group_name: str) -> int:
        """删除分组（将该分组下所有条目的分组清空）

        Args:
            group_name: 分组名称

        Returns:
            受影响的条目数
        """
        cursor = self._conn.execute(
            'UPDATE entries SET "group" = \'\' WHERE "group" = ?',
            (group_name,),
        )
        self._conn.commit()
        return cursor.rowcount

    def rekey(self, new_key: bytes) -> None:
        """更换加密密钥并重新加密所有条目

        Args:
            new_key: 新的加密密钥
        """
        # 用旧密钥解密所有条目
        entries = self.get_all_entries()

        # 切换到新密钥
        old_key = self._key
        self._key = new_key

        try:
            # 在事务中用新密钥重新加密所有条目
            for entry in entries:
                data = self._encrypt_entry_fields(entry)
                self._conn.execute(
                    """UPDATE entries SET
                       title = :title,
                       username_nonce = :username_nonce,
                       username_cipher = :username_cipher,
                       password_nonce = :password_nonce,
                       password_cipher = :password_cipher,
                       url = :url,
                       notes = :notes,
                       "group" = :group,
                       updated_at = :updated_at
                       WHERE id = :id""",
                    data,
                )
            self._conn.commit()
        except Exception:
            # 失败时回滚并恢复旧密钥
            self._conn.rollback()
            self._key = old_key
            raise

    def export_csv(self) -> str:
        """导出所有条目为 CSV 字符串

        Returns:
            CSV 格式字符串（UTF-8 BOM，兼容 Excel 中文显示）
        """
        entries = self.get_all_entries()
        output = io.StringIO()
        # 写 BOM 头，确保 Excel 正确识别 UTF-8
        output.write("﻿")
        writer = csv.writer(output)
        writer.writerow(["网站/软件名", "用户名", "密码", "网址", "备注", "分组"])
        for e in entries:
            writer.writerow([e.title, e.username, e.password, e.url, e.notes, e.group])
        return output.getvalue()

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
