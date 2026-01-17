"""人工审核项目模型

记录需要人工处理的特殊文件/文件夹。
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime
from .base import Base


class ManualReviewItem(Base):
    """人工审核项目表"""
    __tablename__ = 'manual_review_items'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 文件路径信息
    file_path = Column(String(1024), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=True)
    file_count = Column(BigInteger, nullable=True)

    # 原因: size_exceeded/overcount
    reason = Column(String(100), nullable=False)

    # 状态: pending/processed
    status = Column(String(20), default='pending', nullable=False)

    # 备注
    notes = Column(String(1024), nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ManualReviewItem(id={self.id}, reason='{self.reason}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_count': self.file_count,
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }
