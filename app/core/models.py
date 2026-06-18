"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass(frozen=True)
class Entry:
    """密码条目数据模型"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""
    group: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def with_update(self, **kwargs) -> "Entry":
        """不可变更新：返回新实例"""
        current = {
            "id": self.id,
            "title": self.title,
            "username": self.username,
            "password": self.password,
            "url": self.url,
            "notes": self.notes,
            "group": self.group,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
        }
        current.update(kwargs)
        return Entry(**current)


@dataclass(frozen=True)
class Config:
    """配置数据模型"""

    master_password_hash: str = ""
    salt: str = ""
    kdf_iterations: int = 600000
    version: int = 1
