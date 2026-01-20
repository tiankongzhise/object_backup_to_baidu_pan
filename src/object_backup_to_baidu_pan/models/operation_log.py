"""操作日志模型

记录系统运行时的所有操作日志。
"""

from datetime import datetime
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import BigInteger, String, DateTime, Integer, Text
from .base import Base
from typing import Optional

class OperationLog(Base):
    """操作日志表"""
    __tablename__ = 'operation_logs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称（用于区分不同主机）
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 操作信息
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success/failed/running
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 性能信息
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, type='{self.operation_type}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'operation_type': self.operation_type,
            'file_path': self.file_path,
            'status': self.status,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
