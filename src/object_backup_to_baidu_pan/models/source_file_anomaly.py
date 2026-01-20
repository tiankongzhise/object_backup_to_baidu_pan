"""源文件异常记录表

记录不应该发生但发生了的异常情况，如：
- 数据库标记is_backup=True但文件内容hash不一致
- 其他需要管理员人工核验的情况
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import BigInteger, String, Integer, DateTime, CHAR, Text, ForeignKey
from .base import Base


class SourceFileAnomaly(Base):
    """源文件异常记录表

    记录数据不一致等异常情况，供管理员人工核验。
    """
    __tablename__ = 'source_file_anomalies'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 关联的源文件ID（如果有）
    source_file_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey('source_files.id'),
        nullable=True
    )

    # 文件信息
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 数据库中记录的hash值
    db_md5_hash: Mapped[str] = mapped_column(CHAR(32), nullable=False)
    db_sha1_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    db_sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    # 实际计算的文件hash值
    actual_md5_hash: Mapped[str] = mapped_column(CHAR(32), nullable=False)
    actual_sha1_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    actual_sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    # 异常类型
    anomaly_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='异常类型: hash_mismatch=hash不一致, backup_flag_inconsistent=备份标志不一致'
    )

    # 异常详情
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 处理状态: pending/reviewed/resolved
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)

    # 处理人
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 处理备注
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 是否已发送通知邮件
    notification_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<SourceFileAnomaly(id={self.id}, type='{self.anomaly_type}', file='{self.file_name}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'source_file_id': self.source_file_id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'db_md5_hash': self.db_md5_hash,
            'db_sha1_hash': self.db_sha1_hash,
            'db_sha256_hash': self.db_sha256_hash,
            'actual_md5_hash': self.actual_md5_hash,
            'actual_sha1_hash': self.actual_sha1_hash,
            'actual_sha256_hash': self.actual_sha256_hash,
            'anomaly_type': self.anomaly_type,
            'description': self.description,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'review_note': self.review_note,
            'notification_sent': self.notification_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
