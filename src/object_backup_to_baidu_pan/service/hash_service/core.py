"""
Hash计算核心模块

提供底层Hash计算功能，支持大文件分块读取以减少内存占用。

主要功能:
- 支持多种Hash算法(md5, sha1, sha256等)
- 大文件分块读取，每块500MB，内存占用低
"""

import hashlib
import pathlib


def calculate_file_hash_base(file_path: pathlib.Path | str, algorithm: str = 'sha256'):
    """计算单个文件的哈希值（底层实现）

    使用分块读取方式计算文件Hash，避免大文件导致内存溢出。

    Args:
        file_path: 文件路径，支持Path对象或字符串
        algorithm: Hash算法名称，如'md5', 'sha1', 'sha256'等

    Returns:
        hashlib.Hash: Hash对象，可通过.hexdigest()获取十六进制字符串

    Raises:
        FileNotFoundError: 文件不存在
        IOError: 读取文件出错

    Example:
        >>> hash_obj = calculate_file_hash_base('/path/to/file.txt', 'sha256')
        >>> print(hash_obj.hexdigest().upper())
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        # 大文件分块读取，每块500MB，有效降低内存占用
        # 适用于处理几十GB的大型文件
        for chunk in iter(lambda: f.read(500 * 1024 * 1024), b''):
            hash_obj.update(chunk)
    return hash_obj