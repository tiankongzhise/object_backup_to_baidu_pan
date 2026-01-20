"""重复文件模型

记录重复文件的信息和重复原因。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import BigInteger, String, Integer, DateTime, CHAR, Text, ForeignKey
from .base import Base


class DuplicateFile(Base):
    """重复文件记录表

    记录hash值相同的多个文件之间的关系。
    """
    __tablename__ = 'duplicate_files'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称（用于区分不同主机）
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 文件Hash值（所有重复文件的hash都相同）
    md5_hash: Mapped[str] = mapped_column(CHAR(32), nullable=False, index=True)
    sha1_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False, index=True)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, index=True)

    # 关联的主文件（source_files表的记录）
    master_source_file_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey('source_files.id'),
        nullable=True,
        comment='主文件的source_files记录ID'
    )

    # 当前记录的文件信息
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 重复关系信息
    # master_file_path: 主文件路径（第一次出现的文件）
    master_file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 重复类型
    duplicate_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='exact',
        comment='重复类型: exact=完全相同, same_content=内容相同但名称/位置不同'
    )

    # 原因说明
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<DuplicateFile(id={self.id}, file='{self.file_name}', type='{self.duplicate_type}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'md5_hash': self.md5_hash,
            'sha1_hash': self.sha1_hash,
            'sha256_hash': self.sha256_hash,
            'master_source_file_id': self.master_source_file_id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'master_file_path': self.master_file_path,
            'duplicate_count': self.duplicate_count,
            'duplicate_type': self.duplicate_type,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
