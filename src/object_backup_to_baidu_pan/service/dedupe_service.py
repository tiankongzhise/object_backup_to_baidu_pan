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
from ..config import HashConfig, get_hostname
from ..models import SourceFile, BackupPackage, DuplicateFile


# 去重结果
DedupeResultItem = Union[FileInfo, FolderInfo]


@dataclass
class DedupeResult:
    """去重结果"""
    to_backup: list[DedupeResultItem]  # 需要备份（新增文件）
    already_backup: list[DedupeResultItem]  # 已备份，直接删除
    highly_likely_duplicate: list[DedupeResultItem]  # 高度可能重复（主机+路径+大小完全一致）
    not_found_in_db: list[DedupeResultItem]  # 数据库无记录


class DedupeService:
    """去重服务"""

    def __init__(self, hash_config: HashConfig | None = None, logger = None):
        """初始化去重服务

        Args:
            hash_config: Hash配置，如果为None则使用默认配置
            logger: 日志器，如果为None则使用默认日志器
        """
        self.hash_config = hash_config or HashConfig()
        self.hostname = get_hostname()
        self._logger = logger

    def _log(self, message: str, level: str = 'info'):
        """记录日志

        Args:
            message: 日志消息
            level: 日志级别 ('debug', 'info', 'warning', 'error')
        """
        if self._logger:
            getattr(self._logger, level)(message)
        else:
            import logging
            logger = logging.getLogger(__name__)
            getattr(logger, level)(message)

    def compare_and_dedupe(
        self,
        items: list[ScanResult],
        session: Session
    ) -> DedupeResult:
        """与数据库比对，进行去重处理

        流程：
        1. 预处理：检查主机+路径+大小是否与数据库已备份文件完全一致
           - 完全一致 → 高度可能重复对象，延后处理
           - 不一致 → 继续正常去重流程
        2. 正常去重：计算hash，与数据库比对

        注意：计算出的hash会立即保存到数据库，供后续阶段使用
        重复文件会记录到 duplicate_files 表

        Args:
            items: 分类后的项目列表
            session: 数据库会话

        Returns:
            DedupeResult: 去重结果
        """
        to_backup: list[DedupeResultItem] = []
        already_backup: list[DedupeResultItem] = []
        highly_likely_duplicate: list[DedupeResultItem] = []
        not_found_in_db: list[DedupeResultItem] = []

        # 过滤出正常文件/文件夹
        normal_items = [
            item for item in items
            if isinstance(item, (FileInfo, FolderInfo))
        ]

        # 预处理：识别高度可能重复的对象
        # 检查主机+路径+大小是否与数据库已备份的源文件完全一致
        prechecked_items = self._precheck_highly_likely_duplicates(normal_items, session)

        for item in normal_items:
            # 检查是否在预处理列表中（高度可能重复）
            if id(item) in prechecked_items:
                # 高度可能重复，添加到待处理列表，延后处理
                highly_likely_duplicate.append(item)
                continue

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

            # 同时查询 source_files 和 backup_packages（已完成上传的）
            existing_source = self._query_source_by_hashes(session, hashes)
            existing_package = self._query_completed_package_by_hashes(session, hashes)

            if existing_source or existing_package:
                # 任意一个存在相同Hash的记录，标记为已备份
                already_backup.append(item)

                # 更新 source_files 中的文件路径（如果不同）
                if existing_source and existing_source.file_path != str(item.source_path):
                    existing_source.file_path = str(item.source_path)

                # 记录重复文件信息
                self._record_duplicate(session, item, hashes, existing_source)
            else:
                # 数据库中不存在，添加到待备份列表
                # 同时将源文件信息保存到数据库（供后续阶段从数据库获取hash）
                self._save_source_file(session, item, hashes)
                not_found_in_db.append(item)

        return DedupeResult(
            to_backup=not_found_in_db,
            already_backup=already_backup,
            highly_likely_duplicate=highly_likely_duplicate,
            not_found_in_db=not_found_in_db,
        )

    def _precheck_highly_likely_duplicates(
        self,
        items: list[DedupeResultItem],
        session: Session
    ) -> set[int]:
        """预处理：识别高度可能重复的对象

        检查主机+路径+大小是否与数据库已备份的源文件完全一致
        如果完全一致，说明这个文件之前已经备份过（可能是同一次任务中断后的重试）

        Args:
            items: 文件/文件夹列表
            session: 数据库会话

        Returns:
            set[int]: 高度可能重复对象的id集合
        """
        likely_dup_ids: set[int] = set()

        for item in items:
            file_size = item.file_size if isinstance(item, FileInfo) else item.total_size

            # 查询是否已有相同主机+路径+大小的已备份记录
            existing = session.query(SourceFile).filter(
                and_(
                    SourceFile.hostname == self.hostname,
                    SourceFile.file_path == str(item.source_path),
                    SourceFile.file_size == file_size,
                    SourceFile.is_backup == True
                )
            ).first()

            if existing:
                # 主机+路径+大小完全一致，高度可能重复
                likely_dup_ids.add(id(item))
                self._log(f"预处理识别高度可能重复对象: {item.source_path}")

        return likely_dup_ids

    def _save_source_file(self, session: Session, item: DedupeResultItem, hashes: dict):
        """保存源文件信息到数据库

        Args:
            session: 数据库会话
            item: 文件/文件夹信息
            hashes: 已计算的hash值
        """
        # 检查是否已存在
        existing = session.query(SourceFile).filter(
            and_(
                SourceFile.hostname == self.hostname,
                SourceFile.md5_hash == hashes['md5'],
                SourceFile.sha1_hash == hashes['sha1'],
                SourceFile.sha256_hash == hashes['sha256']
            )
        ).first()

        if existing:
            # 更新路径信息
            existing.file_path = str(item.source_path)
            existing.file_name = item.source_path.name
        else:
            # 新建记录
            source_file = SourceFile(
                hostname=self.hostname,
                file_path=str(item.source_path),
                file_name=item.source_path.name,
                file_size=item.file_size if isinstance(item, FileInfo) else item.total_size,
                md5_hash=hashes['md5'],
                sha1_hash=hashes['sha1'],
                sha256_hash=hashes['sha256'],
                is_backup=False,
            )
            session.add(source_file)

    def _record_duplicate(self, session: Session, item: DedupeResultItem, hashes: dict, existing_source: Optional[SourceFile]):
        """记录重复文件信息到数据库

        Args:
            session: 数据库会话
            item: 当前扫描到的文件/文件夹
            hashes: 当前文件的hash值
            existing_source: 数据库中已存在的相同hash记录

        Returns:
            bool: 是否成功记录了重复文件
        """
        # 检查当前文件的路径是否已在重复表中（防止同一文件重复插入）
        existing_by_path = session.query(DuplicateFile).filter(
            and_(
                DuplicateFile.hostname == self.hostname,
                DuplicateFile.file_path == str(item.source_path)
            )
        ).first()

        if existing_by_path:
            # 该文件已经在重复表中记录过了，跳过
            return False

        # 查找该hash是否已有重复记录（用于判断主文件）
        existing_dup_by_hash = session.query(DuplicateFile).filter(
            and_(
                DuplicateFile.hostname == self.hostname,
                DuplicateFile.md5_hash == hashes['md5'],
                DuplicateFile.sha1_hash == hashes['sha1'],
                DuplicateFile.sha256_hash == hashes['sha256']
            )
        ).first()

        if existing_dup_by_hash:
            # 已存在该hash的重复记录，只更新计数
            existing_dup_by_hash.duplicate_count += 1
            return True

        # 新建重复记录
        master_path = existing_source.file_path if existing_source else str(item.source_path)
        master_source_file_id = existing_source.id if existing_source else None

        duplicate_file = DuplicateFile(
            hostname=self.hostname,
            md5_hash=hashes['md5'],
            sha1_hash=hashes['sha1'],
            sha256_hash=hashes['sha256'],
            master_source_file_id=master_source_file_id,
            file_path=str(item.source_path),
            file_name=item.source_path.name,
            file_size=item.file_size if isinstance(item, FileInfo) else item.total_size,
            master_file_path=master_path,
            duplicate_count=1,
            duplicate_type='exact',
            reason=f"与文件 {master_path} 内容完全相同（Hash一致）"
        )
        session.add(duplicate_file)
        return True

    def _query_source_by_hashes(
        self,
        session: Session,
        hashes: dict
    ) -> Optional[SourceFile]:
        """根据Hash值查询 source_files 表

        Args:
            session: 数据库会话
            hashes: Hash值字典

        Returns:
            SourceFile | None: 匹配的记录，不存在返回None
        """
        return session.query(SourceFile).filter(
            and_(
                SourceFile.hostname == self.hostname,
                SourceFile.md5_hash == hashes['md5'],
                SourceFile.sha1_hash == hashes['sha1'],
                SourceFile.sha256_hash == hashes['sha256']
            )
        ).first()

    def _query_completed_package_by_hashes(
        self,
        session: Session,
        hashes: dict
    ) -> Optional[BackupPackage]:
        """根据Hash值查询 backup_packages 表（仅已完成的）

        Args:
            session: 数据库会话
            hashes: Hash值字典

        Returns:
            BackupPackage | None: 匹配的已上传完成的记录，不存在返回None
        """
        return session.query(BackupPackage).filter(
            and_(
                BackupPackage.hostname == self.hostname,
                BackupPackage.status == 'completed',
                BackupPackage.md5_hash == hashes['md5'],
                BackupPackage.sha1_hash == hashes['sha1'],
                BackupPackage.sha256_hash == hashes['sha256']
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
                hostname=self.hostname,
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
        existing = self._query_source_by_hashes(session, hashes)
        if existing:
            existing.is_backup = True
            from datetime import datetime
            existing.backup_time = datetime.utcnow()

