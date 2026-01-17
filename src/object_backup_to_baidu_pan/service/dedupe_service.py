"""去重服务

与数据库比对文件Hash，实现去重备份。
"""

from dataclasses import dataclass
from typing import Union, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .classify_service import FileInfo, FolderInfo, ManualReviewItem, ClassifyResult, ScanResult
from .hash_service import CalculateHashService
from ..config import HashConfig
from ..models import SourceFile


# 去重结果
DedupeResultItem = Union[FileInfo, FolderInfo]


@dataclass
class DedupeResult:
    """去重结果"""
    to_backup: list[DedupeResultItem]  # 需要备份
    already_backup: list[DedupeResultItem]  # 已备份，直接删除
    not_found_in_db: list[DedupeResultItem]  # 数据库无记录


class DedupeService:
    """去重服务"""

    def __init__(self, hash_config: HashConfig | None = None):
        """初始化去重服务

        Args:
            hash_config: Hash配置，如果为None则使用默认配置
        """
        self.hash_config = hash_config or HashConfig()

    def compare_and_dedupe(
        self,
        items: list[ScanResult],
        session: Session
    ) -> DedupeResult:
        """与数据库比对，进行去重处理

        Args:
            items: 分类后的项目列表
            session: 数据库会话

        Returns:
            DedupeResult: 去重结果
        """
        to_backup: list[DedupeResultItem] = []
        already_backup: list[DedupeResultItem] = []
        not_found_in_db: list[DedupeResultItem] = []

        # 过滤出正常文件/文件夹
        normal_items = [
            item for item in items
            if isinstance(item, (FileInfo, FolderInfo))
        ]

        for item in normal_items:
            # 计算Hash
            if isinstance(item, FileInfo):
                hashes = CalculateHashService.calculate_file_hash(
                    item.source_path,
                    self.hash_config.required_hash_algorithms
                )
            else:
                # 传递FolderInfo对象（字典形式），避免folder_hash重复检查分类条件
                hashes = CalculateHashService.calculate_folder_hash(
                    {
                        'source_path': str(item.source_path),
                        'classify_result': item.classify_result.value
                    },
                    self.hash_config.required_hash_algorithms
                )

            # 查询数据库
            existing = self._query_by_hashes(session, hashes)

            if existing:
                # 已存在相同Hash的记录，标记为已备份
                already_backup.append(item)

                # 更新数据库中的文件路径（如果不同）
                if existing.file_path != str(item.source_path):
                    existing.file_path = str(item.source_path)
            else:
                # 数据库中不存在，添加到待备份列表
                if isinstance(item, FolderInfo):
                    not_found_in_db.append(item)
                else:
                    not_found_in_db.append(item)

        # 合并 not_found_in_db 到 to_backup
        to_backup = not_found_in_db

        return DedupeResult(
            to_backup=to_backup,
            already_backup=already_backup,
            not_found_in_db=not_found_in_db,
        )

    def _query_by_hashes(
        self,
        session: Session,
        hashes: dict
    ) -> Optional[SourceFile]:
        """根据Hash值查询数据库

        Args:
            session: 数据库会话
            hashes: Hash值字典

        Returns:
            SourceFile | None: 匹配的记录，不存在返回None
        """
        return session.query(SourceFile).filter(
            and_(
                SourceFile.md5_hash == hashes['md5'],
                SourceFile.sha1_hash == hashes['sha1'],
                SourceFile.sha256_hash == hashes['sha256']
            )
        ).first()

    def save_source_files(
        self,
        items: list[DedupeResultItem],
        session: Session
    ):
        """保存源文件信息到数据库

        Args:
            items: 需要备份的文件/文件夹列表
            session: 数据库会话
        """
        for item in items:
            # 计算Hash
            if isinstance(item, FileInfo):
                hashes = CalculateHashService.calculate_file_hash(
                    item.source_path,
                    self.hash_config.required_hash_algorithms
                )
            else:
                hashes = CalculateHashService.calculate_folder_hash(
                    item.source_path,
                    self.hash_config.required_hash_algorithms
                )

            # 创建记录
            source_file = SourceFile(
                file_path=str(item.source_path),
                file_name=item.source_path.name,
                file_size=item.file_size if isinstance(item, FileInfo) else item.total_size,
                md5_hash=hashes['md5'],
                sha1_hash=hashes['sha1'],
                sha256_hash=hashes['sha256'],
                is_backup=False,
            )

            session.add(source_file)

    def mark_as_backup(
        self,
        item: DedupeResultItem,
        session: Session
    ):
        """标记文件为已备份

        Args:
            item: 已备份的文件/文件夹
            session: 数据库会话
        """
        # 计算Hash
        if isinstance(item, FileInfo):
            hashes = CalculateHashService.calculate_file_hash(
                item.source_path,
                self.hash_config.required_hash_algorithms
            )
        else:
            hashes = CalculateHashService.calculate_folder_hash(
                item.source_path,
                self.hash_config.required_hash_algorithms
            )

        # 查找并更新
        existing = self._query_by_hashes(session, hashes)
        if existing:
            existing.is_backup = True
            from datetime import datetime
            existing.backup_time = datetime.utcnow()

