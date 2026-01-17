"""备份压缩包模型

记录ZIP压缩包的信息和上传状态。
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, CHAR
from .base import Base


class BackupPackage(Base):
    """备份压缩包信息表"""
    __tablename__ = 'backup_packages'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 文件路径
    package_path = Column(String(500), nullable=False, unique=True)
    baidu_pan_path = Column(String(500), nullable=True)

    # 关联源文件
    source_file_id = Column(BigInteger, ForeignKey('source_files.id'), nullable=True)

    # 压缩包Hash值
    md5_hash = Column(CHAR(32), nullable=False)
    sha1_hash = Column(CHAR(40), nullable=False)
    sha256_hash = Column(CHAR(64), nullable=False)

    # 压缩包信息
    password = Column(String(64), nullable=True)
    file_count = Column(Integer, nullable=False)
    package_size = Column(BigInteger, nullable=False)

    # 上传状态: pending/uploading/completed/failed
    status = Column(String(20), default='pending', nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<BackupPackage(id={self.id}, status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
