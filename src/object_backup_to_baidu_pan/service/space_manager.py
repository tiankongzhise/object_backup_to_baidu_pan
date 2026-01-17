"""空间管理器

监控磁盘空间，动态控制处理流程。
"""

from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
import time
import shutil
from typing import Callable, Optional
from .hash_service import CalculateHashService
from .classify_service import FileInfo, FolderInfo
from ..config import SpaceConfig


@dataclass
class SpaceInfo:
    """磁盘空间信息"""
    total_bytes: int
    used_bytes: int
    available_bytes: int
    used_percent: float


class SpaceManager:
    """空间管理器"""

    def __init__(self, config: SpaceConfig | None = None):
        """初始化空间管理器

        Args:
            config: 空间配置，如果为None则使用默认配置
        """
        self.config = config or SpaceConfig()
        self._reserved_space = 0

    def get_disk_space(self, path: Path) -> SpaceInfo:
        """获取磁盘空间信息

        Args:
            path: 任意路径，用于确定磁盘

        Returns:
            SpaceInfo: 磁盘空间信息
        """
        drive = Path(path).anchor if str(path).startswith('/') else Path(path).drive
        if not drive:
            # Linux/macOS
            stat = shutil.disk_usage(str(path))
        else:
            # Windows
            stat = shutil.disk_usage(str(path))

        total = stat.total
        used = stat.used
        available = stat.free
        used_percent = (used / total) * 100 if total > 0 else 0

        return SpaceInfo(
            total_bytes=total,
            used_bytes=used,
            available_bytes=available,
            used_percent=used_percent,
        )

    def calculate_required_space(
        self,
        item: FileInfo | FolderInfo
    ) -> int:
        """计算处理文件所需空间

        Args:
            item: 文件/文件夹信息

        Returns:
            int: 所需空间（字节）
        """
        # 阶段2：压缩处理需要 压缩包大小
        # 阶段3：解压验证需要 压缩包大小 + 解压文件大小
        # 保守估计：压缩包大小 + 解压文件大小

        if isinstance(item, FileInfo):
            # 估算ZIP文件大小（略大于源文件）
            return int(item.file_size * 1.1) + item.file_size
        else:
            # 文件夹：总大小 + 压缩包大小
            return int(item.total_size * 1.1) + item.total_size

    def can_process(self, item: FileInfo | FolderInfo, path: Path) -> bool:
        """检查是否可以处理该文件

        Args:
            item: 文件/文件夹信息
            path: 存储路径（用于检查磁盘空间）

        Returns:
            bool: 是否可以处理
        """
        required = self.calculate_required_space(item)
        space = self.get_disk_space(path)

        # 可用空间 = 磁盘总空间 - (限制 + 已预留空间)
        limit_bytes = self.config.disk_limit_gb * 1024**3
        available_for_use = limit_bytes - self._reserved_space

        return space.available_bytes >= required and \
            space.used_bytes < limit_bytes - self._reserved_space

    def check_initial_space(self, path: Path) -> bool:
        """检查初始化时的磁盘空间

        Args:
            path: 存储路径

        Returns:
            bool: 空间是否足够
        """
        limit_bytes = self.config.disk_limit_gb * 1024**3
        space = self.get_disk_space(path)

        if space.used_bytes >= limit_bytes:
            raise ValueError(
                f"磁盘空间不足: 已使用 {space.used_bytes / 1024**3:.1f}GB, "
                f"限制 {self.config.disk_limit_gb}GB"
            )

        return True

    @contextmanager
    def reserve_space(self, item: FileInfo | FolderInfo, path: Path):
        """预留空间上下文管理器

        Args:
            item: 文件/文件夹信息
            path: 存储路径
        """
        required = self.calculate_required_space(item)

        # 等待空间释放
        while not self._check_space_available(required, path):
            time.sleep(1)

        # 预留空间
        self._reserved_space += required
        try:
            yield
        finally:
            self._reserved_space -= required

    def _check_space_available(self, required: int, path: Path) -> bool:
        """检查是否有足够的可用空间

        Args:
            required: 所需空间
            path: 存储路径

        Returns:
            bool: 空间是否足够
        """
        limit_bytes = self.config.disk_limit_gb * 1024**3
        space = self.get_disk_space(path)

        # 可用空间 = 总空间 - 已使用 - 已预留
        effective_available = space.available_bytes - self._reserved_space

        return effective_available >= required and \
            space.used_bytes < limit_bytes - self._reserved_space

    def wait_for_space(self, item: FileInfo | FolderInfo, path: Path, timeout: int = 300):
        """等待可用空间

        Args:
            item: 文件/文件夹信息
            path: 存储路径
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功获得空间
        """
        required = self.calculate_required_space(item)
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self._check_space_available(required, path):
                return True
            time.sleep(1)

        raise TimeoutError("等待磁盘空间超时")

    def release_space(self, item: FileInfo | FolderInfo):
        """释放预留空间

        Args:
            item: 文件/文件夹信息
        """
        required = self.calculate_required_space(item)
        self._reserved_space = max(0, self._reserved_space - required)
