"""源文件模型

记录需要备份的文件信息，包括Hash值用于去重比对。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import BigInteger, String, Boolean, DateTime, CHAR
from .base import Base


class SourceFile(Base):
    """源文件信息表"""
    __tablename__ = 'source_files'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称（用于区分不同主机）
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 文件路径
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 三种Hash值
    md5_hash: Mapped[str] = mapped_column(CHAR(32), nullable=False, index=True)
    sha1_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False, index=True)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, index=True)

    # 备份状态
    is_backup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SourceFile(id={self.id}, name='{self.file_name}', backup={self.is_backup})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'md5_hash': self.md5_hash,
            'sha1_hash': self.sha1_hash,
            'sha256_hash': self.sha256_hash,
            'is_backup': self.is_backup,
            'backup_time': self.backup_time.isoformat() if self.backup_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
