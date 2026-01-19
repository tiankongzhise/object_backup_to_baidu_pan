"""
文件夹Hash计算模块

提供文件夹的Hash值计算功能，通过递归遍历文件夹内所有文件来计算整体Hash。

主要功能:
- 验证文件夹是否符合Hash计算条件（大小、文件数、空文件夹等）
- 支持多种Hash算法(md5, sha1, sha256)并行计算
- 可选择是否显示计算进度条
- 对文件夹内文件按路径排序确保Hash一致性
"""

from typing import Union, Optional
from pathlib import Path
from tqdm import tqdm
import hashlib

from .core import calculate_file_hash_base
from ...config import HashConfig, ClassifyConfig


def _is_empty_folder(folder_info: Union[Path, dict]) -> bool:
    """检查文件夹是否为空

    Args:
        folder_info: 文件夹路径(Path对象)或包含classify_result的字典

    Returns:
        bool: 如果文件夹为空则返回True

    Raises:
        TypeError: 输入类型不支持
    """
    match folder_info:
        case Path():
            return not any(folder_info.iterdir())
        case dict():
            return folder_info.get('classify_result') == 'empty_folder'
        case _:
            raise TypeError("folder_info must be Path or dict")


def _is_overcount(folder_info: Union[list[Path], dict]) -> bool:
    """检查文件夹内文件数量是否超过限制

    Args:
        folder_info: 文件路径列表或包含classify_result的字典

    Returns:
        bool: 如果文件数超过ClassifyConfig.overcount限制则返回True

    Raises:
        TypeError: 输入类型不支持
    """
    match folder_info:
        case list():
            return len(folder_info) > ClassifyConfig.overcount
        case dict():
            return folder_info.get('classify_result') == 'overcount'
        case _:
            raise TypeError("folder_info must be Path, list or dict")


def _is_oversize(folder_info: Union[list[Path], dict]) -> bool:
    """检查文件夹总大小是否超过限制

    Args:
        folder_info: 文件路径列表或包含classify_result的字典

    Returns:
        bool: 如果文件夹总大小超过ClassifyConfig.folder_oversize限制则返回True

    Raises:
        TypeError: 输入类型不支持
    """
    match folder_info:
        case list():
            return sum(item.stat().st_size for item in folder_info) > ClassifyConfig.folder_oversize
        case dict():
            return folder_info.get('classify_result') == 'oversize'
        case _:
            raise TypeError("folder_info must be Path, list or dict")


def _verify_folder_for_hashing(folder_info: Union[Path, dict, str]) -> list[Path]:
    """验证文件夹是否符合Hash计算条件

    执行以下检查:
    1. 文件夹是否为空
    2. 文件数量是否超过限制
    3. 总大小是否超过限制

    通过验证后，递归收集文件夹内所有文件的路径，并按路径排序返回。

    Args:
        folder_info: 文件夹路径或文件夹信息字典

    Returns:
        list[Path]: 排序后的文件路径列表

    Raises:
        ValueError: 文件夹不符合Hash计算条件（空文件夹、文件数超限、大小超限）
    """
    file_list: list[Path] = []
    match folder_info:
        case dict():
            # 从字典提取文件夹信息
            if _is_empty_folder(folder_info):
                raise ValueError("Folder is empty")
            if _is_overcount(folder_info):
                raise ValueError("Folder file count exceeds limit")
            if _is_oversize(folder_info):
                raise ValueError("Folder size exceeds limit")
            folder_path = Path(folder_info['source_path'])
            file_list = [item for item in folder_path.rglob("*") if item.is_file()]
        case _:
            # 从Path或字符串提取文件夹路径
            folder_path = Path(folder_info)
            if _is_empty_folder(folder_path):
                raise ValueError("Folder is empty")
            file_list = [item for item in folder_path.rglob("*") if item.is_file()]
            if _is_overcount(file_list):
                raise ValueError("Folder file count exceeds limit")
            if _is_oversize(file_list):
                raise ValueError("Folder size exceeds limit")

    # 按路径排序确保Hash一致性（跨平台、跨环境）
    sorted_file_list = sorted(file_list)
    return sorted_file_list


def _display_hash_progress(file_list: list[Path], alg: str) -> str:
    """计算Hash并显示进度条

    Args:
        file_list: 待计算Hash的文件路径列表
        alg: Hash算法名称

    Returns:
        str: 大写十六进制Hash值
    """
    hash_obj = hashlib.new(alg)
    for file in tqdm(file_list, desc=f"Calculating {alg} hash", unit="file"):
        hash_obj.update(calculate_file_hash_base(file, alg).digest())
    return hash_obj.hexdigest().upper()


def _not_display_hash_progress(file_list: list[Path], alg: str) -> str:
    """计算Hash（不显示进度条）

    Args:
        file_list: 待计算Hash的文件路径列表
        alg: Hash算法名称

    Returns:
        str: 大写十六进制Hash值
    """
    hash_obj = hashlib.new(alg)
    for file in file_list:
        hash_obj.update(calculate_file_hash_base(file, alg).digest())
    return hash_obj.hexdigest().upper()


def calculate_folder_hash(
    folder_info: Union[str, Path, dict],
    algorithm: Optional[list[str]] = None,
    display_hash_progress: bool = True
) -> dict[str, str]:
    """计算文件夹的Hash值

    递归遍历文件夹内所有文件，计算所有指定算法的Hash值。

    注意：文件夹的Hash值是通过按顺序拼接所有文件的Hash计算得出的，
    这确保了相同内容的文件夹在不同环境下产生相同的Hash值。

    Args:
        folder_info: 文件夹路径或包含文件夹信息的字典
            - str/Path: 文件系统路径
            - dict: 需包含'source_path'键，可选包含'classify_result'
        algorithm: Hash算法列表，默认为None使用HashConfig.required_hash_algorithms
            常用算法: 'md5', 'sha1', 'sha256'
        display_hash_progress: 是否显示计算进度条，默认True

    Returns:
        dict[str, str]: Hash值字典，键为算法名称，值为对应的大写十六进制Hash值
            Example: {'md5': '...', 'sha1': '...', 'sha256': '...'}

    Raises:
        ValueError: 文件夹不符合Hash计算条件
        FileNotFoundError: 文件夹不存在
        IOError: 读取文件出错

    Example:
        >>> result = calculate_folder_hash('/path/to/folder')
        >>> print(result['sha256'])
        E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
    """
    file_list = _verify_folder_for_hashing(folder_info)
    algorithms = algorithm or HashConfig.required_hash_algorithms
    hash_result: dict[str, str] = {}

    for alg in algorithms:
        if display_hash_progress:
            hash_result[alg] = _display_hash_progress(file_list, alg)
        else:
            hash_result[alg] = _not_display_hash_progress(file_list, alg)

    return hash_result
