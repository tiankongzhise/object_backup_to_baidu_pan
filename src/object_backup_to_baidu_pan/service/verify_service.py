"""验证服务

解压ZIP压缩包，验证解压后的文件Hash与源文件一致。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from .zip_service import ZipService
from .hash_service import CalculateHashService
from .classify_service import FileInfo, FolderInfo
from ..config import HashConfig, ZipConfig
import shutil


@dataclass
class VerifyResult:
    """验证结果"""
    is_valid: bool
    extracted_path: Optional[Path] = None
    extracted_hashes: Optional[dict] = None
    source_hashes: Optional[dict] = None
    error_message: Optional[str] = None

    def __bool__(self) -> bool:
        return self.is_valid


class VerifyService:
    """验证服务"""

    def __init__(
        self,
        hash_config: HashConfig | None = None,
        zip_config: ZipConfig | None = None
    ):
        """初始化验证服务

        Args:
            hash_config: Hash配置，如果为None则使用默认配置
            zip_config: ZIP配置，如果为None则使用默认配置
        """
        self.hash_config = hash_config or HashConfig()
        self.zip_config = zip_config or ZipConfig()

    def verify_package(
        self,
        zip_path: Path,
        source_info: FileInfo | FolderInfo,
        password: str | None = None
    ) -> VerifyResult:
        """验证ZIP压缩包

        Args:
            zip_path: ZIP文件路径
            source_info: 源文件/文件夹信息
            password: ZIP解压密码

        Returns:
            VerifyResult: 验证结果
        """
        extracted_path = None

        try:
            # 1. 解压ZIP
            extracted_path = ZipService.unzip_item(
                zip_path,
                password=password
            )

            # 2. 计算解压后的Hash
            if isinstance(source_info, FileInfo):
                extracted_hashes = CalculateHashService.calculate_file_hash(
                    extracted_path,
                    self.hash_config.required_hash_algorithms
                )
                source_hashes = CalculateHashService.calculate_file_hash(
                    source_info.source_path,
                    self.hash_config.required_hash_algorithms
                )
            else:
                extracted_hashes = CalculateHashService.calculate_folder_hash(
                    extracted_path,
                    self.hash_config.required_hash_algorithms
                )
                source_hashes = CalculateHashService.calculate_folder_hash(
                    source_info.source_path,
                    self.hash_config.required_hash_algorithms
                )

            # 3. 比对Hash
            is_valid = self._compare_hashes(extracted_hashes, source_hashes)

            return VerifyResult(
                is_valid=is_valid,
                extracted_path=extracted_path,
                extracted_hashes=extracted_hashes,
                source_hashes=source_hashes,
            )

        except Exception as e:
            # 清理解压目录
            if extracted_path and extracted_path.exists():
                shutil.rmtree(extracted_path, ignore_errors=True)

            return VerifyResult(
                is_valid=False,
                error_message=str(e),
            )

    def _compare_hashes(self, extracted: dict, source: dict) -> bool:
        """比较两组Hash值

        Args:
            extracted: 解压后的Hash值
            source: 源文件的Hash值

        Returns:
            bool: 是否一致
        """
        for alg in self.hash_config.required_hash_algorithms:
            if alg not in extracted or alg not in source:
                return False
            if extracted[alg] != source[alg]:
                return False
        return True

    def cleanup_extracted(self, extracted_path: Path):
        """清理解压目录

        Args:
            extracted_path: 解压目录路径
        """
        if extracted_path and extracted_path.exists():
            shutil.rmtree(extracted_path, ignore_errors=True)
