"""备份压缩包模型

记录ZIP压缩包的信息和上传状态。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, CHAR, Boolean
from .base import Base


class BackupPackage(Base):
    """备份压缩包信息表"""
    __tablename__ = 'backup_packages'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 主机名称（用于区分不同主机）
    hostname: Mapped[str] = mapped_column(String(64), nullable=False, default="localhost", index=True)

    # 文件路径
    package_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    baidu_pan_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 关联源文件
    source_file_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('source_files.id'), nullable=True)

    # 压缩包Hash值
    md5_hash: Mapped[str] = mapped_column(CHAR(32), nullable=False)
    sha1_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    # 压缩包信息
    password: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    package_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 上传状态: pending/uploading/completed/failed
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)

    # 是否是已压缩文件直接上传（不经过压缩环节）
    is_source_archive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<BackupPackage(id={self.id}, status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'package_path': self.package_path,
            'baidu_pan_path': self.baidu_pan_path,
            'source_file_id': self.source_file_id,
            'md5_hash': self.md5_hash,
            'sha1_hash': self.sha1_hash,
            'sha256_hash': self.sha256_hash,
            'password': self.password,
            'file_count': self.file_count,
            'package_size': self.package_size,
            'status': self.status,
            'is_source_archive': self.is_source_archive,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
