"""object_backup_to_baidu_pan

百度网盘备份工具 - 将本地文件加密打包后备份到百度网盘。

功能:
- 文件夹扫描和分类
- Hash去重比对
- AES加密压缩
- 解压验证
- 百度网盘分片上传
- 断点续传
- 磁盘空间管理
"""

__version__ = "0.2.0"
__author__ = ""

from .main import main

__all__ = ['main']
