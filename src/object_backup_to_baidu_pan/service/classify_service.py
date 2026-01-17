"""分类服务

扫描源文件夹，获取一级子文件和文件夹，并进行分类检查。
"""

from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from typing import Union
from ..config import ClassifyConfig


class ItemType(Enum):
    """项目类型"""
    FILE = "file"
    FOLDER = "folder"


class ClassifyResult(Enum):
    """分类结果"""
    NORMAL_FILE = "normal_file"
    NORMAL_FOLDER = "normal_folder"
    OVERSIZE_FILE = "oversize_file"
    OVERSIZE_FOLDER = "oversize_folder"
    OVERCOUNT = "overcount"
    EMPTY_FOLDER = "empty_folder"


@dataclass
class FileInfo:
    """文件信息"""
    source_path: Path
    file_name: str
    file_size: int
    classify_result: ClassifyResult = ClassifyResult.NORMAL_FILE

    def __post_init__(self):
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)

    @property
    def item_type(self) -> ItemType:
        return ItemType.FILE


@dataclass
class FolderInfo:
    """文件夹信息"""
    source_path: Path
    folder_name: str
    file_count: int  # 直接子文件数
    total_size: int
    classify_result: ClassifyResult = ClassifyResult.NORMAL_FOLDER

    def __post_init__(self):
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)

    @property
    def item_type(self) -> ItemType:
        return ItemType.FOLDER


@dataclass
class ManualReviewItem:
    """需要人工审核的项目"""
    source_path: Path
    reason: str  # size_exceeded / overcount
    file_size: int | None = None
    file_count: int | None = None
    classify_result: ClassifyResult = ClassifyResult.OVERSIZE_FOLDER

    def __post_init__(self):
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)
        if self.classify_result == ClassifyResult.OVERCOUNT:
            self.reason = "overcount"
        else:
            self.reason = "size_exceeded"


# 联合类型
ScanResult = Union[FileInfo, FolderInfo, ManualReviewItem]


class ClassifyService:
    """分类服务"""

    def __init__(self, config: ClassifyConfig | None = None):
        """初始化分类服务

        Args:
            config: 分类配置，如果为None则使用默认配置
        """
        self.config = config or ClassifyConfig()

    def scan_source_folder(self, source_path: str | Path) -> list[ScanResult]:
        """扫描源文件夹，获取一级子项并进行分类

        Args:
            source_path: 源文件夹路径

        Returns:
            list[ScanResult]: 分类后的项目列表
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"源文件夹不存在: {source_path}")
        if not source_path.is_dir():
            raise NotADirectoryError(f"路径不是文件夹: {source_path}")

        results: list[ScanResult] = []
        items = sorted(source_path.iterdir())

        for item in items:
            try:
                if item.is_file():
                    result = self._classify_file(item)
                else:
                    result = self._classify_folder(item)
                results.append(result)
            except Exception as e:
                # 如果分类失败，标记为需要人工处理
                review_item = ManualReviewItem(
                    source_path=item,
                    reason="classification_error",
                    classify_result=ClassifyResult.OVERSIZE_FOLDER,
                )
                results.append(review_item)

        return results

    def _classify_file(self, file_path: Path) -> FileInfo | ManualReviewItem:
        """分类单个文件

        Args:
            file_path: 文件路径

        Returns:
            FileInfo | ManualReviewItem: 文件信息或人工审核项目
        """
        file_size = file_path.stat().st_size

        if file_size > self.config.file_oversize:
            return ManualReviewItem(
                source_path=file_path,
                file_size=file_size,
                reason="size_exceeded",
                classify_result=ClassifyResult.OVERSIZE_FILE,
            )

        return FileInfo(
            source_path=file_path,
            file_name=file_path.name,
            file_size=file_size,
            classify_result=ClassifyResult.NORMAL_FILE,
        )

    def _classify_folder(self, folder_path: Path) -> FolderInfo | ManualReviewItem:
        """分类单个文件夹

        Args:
            folder_path: 文件夹路径

        Returns:
            FolderInfo | ManualReviewItem: 文件夹信息或人工审核项目
        """
        # 计算直接子文件数和总大小
        file_count = 0
        total_size = 0

        for child in folder_path.iterdir():
            if child.is_file():
                file_count += 1
                try:
                    total_size += child.stat().st_size
                except OSError:
                    pass

        # 检查是否为空文件夹
        if file_count == 0:
            return ManualReviewItem(
                source_path=folder_path,
                file_count=0,
                reason="empty_folder",
                classify_result=ClassifyResult.EMPTY_FOLDER,
            )

        # 检查文件数是否超限
        if file_count > self.config.overcount:
            return ManualReviewItem(
                source_path=folder_path,
                file_count=file_count,
                reason="overcount",
                classify_result=ClassifyResult.OVERCOUNT,
            )

        # 检查总大小是否超限
        if total_size > self.config.folder_oversize:
            return ManualReviewItem(
                source_path=folder_path,
                file_size=total_size,
                file_count=file_count,
                reason="size_exceeded",
                classify_result=ClassifyResult.OVERSIZE_FOLDER,
            )

        return FolderInfo(
            source_path=folder_path,
            folder_name=folder_path.name,
            file_count=file_count,
            total_size=total_size,
            classify_result=ClassifyResult.NORMAL_FOLDER,
        )
