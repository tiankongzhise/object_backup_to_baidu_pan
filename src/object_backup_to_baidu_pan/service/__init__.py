"""服务模块

提供备份系统的所有服务模块。
"""

from .hash_service import CalculateHashService
from .zip_service import ZipService
from .upload_service import UploadService
from .classify_service import (
    ClassifyService, FileInfo, FolderInfo,
    ManualReviewItem, ClassifyResult, ScanResult
)
from .dedupe_service import DedupeService, DedupeResult
from .verify_service import VerifyService, VerifyResult
from .space_manager import SpaceManager, SpaceInfo
from .queue_manager import QueueManager, UploadTask, UploadResult
from .database_service import DatabaseService
from .orchestrator import MainOrchestrator, BackupProgress

__all__ = [
    # Hash服务
    'CalculateHashService',
    # ZIP服务
    'ZipService',
    # 上传服务
    'UploadService',
    # 分类服务
    'ClassifyService',
    'FileInfo',
    'FolderInfo',
    'ManualReviewItem',
    'ClassifyResult',
    'ScanResult',
    # 去重服务
    'DedupeService',
    'DedupeResult',
    # 验证服务
    'VerifyService',
    'VerifyResult',
    # 空间管理
    'SpaceManager',
    'SpaceInfo',
    # 队列管理
    'QueueManager',
    'UploadTask',
    'UploadResult',
    # 数据库
    'DatabaseService',
    # 协调器
    'MainOrchestrator',
    'BackupProgress',
]
