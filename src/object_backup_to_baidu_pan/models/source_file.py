"""源文件模型

记录需要备份的文件信息，包括Hash值用于去重比对。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, CHAR
from .base import Base


class SourceFile(Base):
    """源文件信息表"""
    __tablename__ = 'source_files'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_path = Column(String(1024), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)

    # 三种Hash值
    md5_hash = Column(CHAR(32), nullable=False, index=True)
    sha1_hash = Column(CHAR(40), nullable=False, index=True)
    sha256_hash = Column(CHAR(64), nullable=False, index=True)

    # 备份状态
    is_backup = Column(Boolean, default=False, nullable=False)
    backup_time = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SourceFile(id={self.id}, name='{self.file_name}', backup={self.is_backup})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
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
