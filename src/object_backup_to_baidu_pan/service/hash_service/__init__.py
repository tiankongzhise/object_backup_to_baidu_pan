"""
Hash计算服务模块

提供文件和文件夹的Hash值计算功能，支持多种Hash算法。

主要组件:
- CalculateHashService: Hash计算服务类（统一入口）
- calculate_file_hash: 计算单个文件的Hash
- calculate_folder_hash: 计算文件夹的Hash

支持的Hash算法:
- md5: 128位Hash，广泛用于文件完整性校验
- sha1: 160位Hash，比md5更安全
- sha256: 256位Hash，目前广泛使用的安全Hash算法

使用示例:
    >>> from service.hash_service import CalculateHashService
    >>> # 计算文件Hash
    >>> file_hash = CalculateHashService.calculate_file_hash('/path/to/file.txt')
    >>> print(file_hash['md5'])
    >>> # 计算文件夹Hash
    >>> folder_hash = CalculateHashService.calculate_folder_hash('/path/to/folder')
    >>> print(folder_hash['sha256'])
"""

from .folder_hash import calculate_folder_hash
from .file_hash import calculate_file_hash


class CalculateHashService:
    """Hash计算服务类

    提供文件和文件夹Hash计算的统一接口。

    特性:
    - 支持多种Hash算法并行计算
    - 自动验证输入文件/文件夹的有效性
    - 文件夹计算时自动递归遍历所有子文件
    - 文件夹内文件按路径排序确保Hash一致性
    """

    @staticmethod
    def calculate_folder_hash(
        folder_info: str | Path | dict,
        algorithm: list[str] | None = None,
        display_hash_progress: bool = True
    ) -> dict[str, str]:
        """计算文件夹的Hash值

        Args:
            folder_info: 文件夹路径或包含文件夹信息的字典
                - str: 文件夹路径字符串
                - Path: pathlib.Path对象
                - dict: 包含'source_path'键的字典，可选'classify_result'
            algorithm: Hash算法列表，默认使用HashConfig.required_hash_algorithms
            display_hash_progress: 是否显示计算进度条，默认True

        Returns:
            dict[str, str]: Hash值字典，键为算法名称，值为大写十六进制Hash值

        Raises:
            ValueError: 文件夹不符合Hash计算条件
            FileNotFoundError: 文件夹不存在
        """
        return calculate_folder_hash(folder_info, algorithm, display_hash_progress)

    @staticmethod
    def calculate_file_hash(
        file_info: str | Path | dict,
        algorithm: list[str] | None = None
    ) -> dict[str, str]:
        """计算文件的Hash值

        Args:
            file_info: 文件路径或包含文件信息的字典
                - str: 文件路径字符串
                - Path: pathlib.Path对象
                - dict: 包含'source_path'键的字典，可选'classify_result'
            algorithm: Hash算法列表，默认使用HashConfig.required_hash_algorithms

        Returns:
            dict[str, str]: Hash值字典，键为算法名称，值为大写十六进制Hash值

        Raises:
            ValueError: 文件不符合Hash计算条件
            FileNotFoundError: 文件不存在
        """
        return calculate_file_hash(file_info, algorithm)


__all__ = [
    'CalculateHashService',
    'calculate_file_hash',
    'calculate_folder_hash',
]
