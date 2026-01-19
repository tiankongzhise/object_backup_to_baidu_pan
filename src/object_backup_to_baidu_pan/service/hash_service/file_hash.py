"""
文件Hash计算模块

提供单个文件的Hash值计算功能，支持多种Hash算法并行计算。

主要功能:
- 验证文件是否符合计算条件（大小、类型）
- 支持多种Hash算法(md5, sha1, sha256)并行计算
- 返回所有算法的Hash值字典
"""

from typing import Union
from pathlib import Path

from .core import calculate_file_hash_base
from ...config import HashConfig, ClassifyConfig


def _is_oversize(file_info: Union[str, Path, dict]) -> bool:
    """检查文件是否超过大小限制

    Args:
        file_info: 文件信息，可以是路径字符串、Path对象或包含classify_result的字典

    Returns:
        bool: 如果文件大小超过ClassifyConfig中定义的文件大小限制则返回True

    Note:
        分类结果为'oversize_file'的字典直接返回True
    """
    match file_info:
        case dict():
            return file_info.get('classify_result') == 'oversize_file'
        case _:
            file_info = Path(file_info)
            return file_info.stat().st_size > ClassifyConfig.file_oversize


def _is_file(file_info: Union[str, Path, dict]) -> bool:
    """检查输入是否为有效文件路径

    Args:
        file_info: 文件信息，可以是Path对象、字符串路径或包含source_path的字典

    Returns:
        bool: 如果是有效文件路径则返回True

    Raises:
        ValueError: 输入类型不支持
    """
    match file_info:
        case Path():
            return file_info.is_file()
        case dict():
            return Path(file_info['source_path']).is_file()
        case str():
            return Path(file_info).is_file()
        case _:
            raise ValueError(f"Invalid file_info type: {type(file_info)}")


def _verify_file_for_hashing(file_info: Union[str, Path, dict]) -> Path:
    """验证文件是否符合Hash计算条件

    执行以下检查:
    1. 文件大小是否超过限制
    2. 路径是否指向有效文件

    Args:
        file_info: 文件信息，可以是路径字符串、Path对象或字典

    Returns:
        Path: 验证通过的文件的Path对象

    Raises:
        ValueError: 文件超过大小限制或不是有效文件
    """
    if _is_oversize(file_info):
        raise ValueError(f"File exceeds size limit: {file_info}")
    if not _is_file(file_info):
        raise ValueError(f"Not a valid file: {file_info}")
    return Path(file_info['source_path']) if isinstance(file_info, dict) else Path(file_info)


def calculate_file_hash(
    file_info: Union[str, Path, dict],
    algorithm: Union[list, None] = None
) -> dict[str, str]:
    """计算文件的Hash值

    计算指定文件的所有指定算法的Hash值，返回字典形式的Hash结果。

    Args:
        file_info: 文件路径或包含文件信息的字典
            - str/Path: 文件系统路径
            - dict: 需包含'source_path'键，可选包含'classify_result'
        algorithm: Hash算法列表，默认为None使用HashConfig.required_hash_algorithms
            常用算法: 'md5', 'sha1', 'sha256'

    Returns:
        dict[str, str]: Hash值字典，键为算法名称，值为对应的大写十六进制Hash值
            Example: {'md5': 'D41D8CD98F00B204E9800998ECF8427E', 'sha1': '...', 'sha256': '...'}

    Raises:
        ValueError: 文件不符合Hash计算条件
        FileNotFoundError: 文件不存在
        IOError: 读取文件出错

    Example:
        >>> result = calculate_file_hash('/path/to/file.txt')
        >>> print(result['md5'])
        D41D8CD98F00B204E9800998ECF8427E
    """
    file_path = _verify_file_for_hashing(file_info)
    hash_result: dict[str, str] = {}
    algorithms = algorithm or HashConfig.required_hash_algorithms

    for alg in algorithms:
        hash_result[alg] = calculate_file_hash_base(file_path, alg).hexdigest().upper()

    return hash_result

