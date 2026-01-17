"""操作日志模型

记录系统运行时的所有操作日志。
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Text
from .base import Base


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = 'operation_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 操作信息
    operation_type = Column(String(50), nullable=False, index=True)
    file_path = Column(String(1024), nullable=True)
    status = Column(String(20), nullable=False)  # success/failed/running
    message = Column(Text, nullable=True)

    # 性能信息
    duration_ms = Column(Integer, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, type='{self.operation_type}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'file_path': self.file_path,
            'status': self.status,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
