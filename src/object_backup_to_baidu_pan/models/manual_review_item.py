"""人工审核项目模型

记录需要人工处理的特殊文件/文件夹。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import BigInteger, String, DateTime
from .base import Base


class ManualReviewItem(Base):
    """人工审核项目表"""
    __tablename__ = 'manual_review_items'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称（用于区分不同主机）
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 文件路径信息
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # 原因: size_exceeded/overcount
    reason: Mapped[str] = mapped_column(String(100), nullable=False)

    # 状态: pending/processed
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ManualReviewItem(id={self.id}, reason='{self.reason}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_count': self.file_count,
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }
