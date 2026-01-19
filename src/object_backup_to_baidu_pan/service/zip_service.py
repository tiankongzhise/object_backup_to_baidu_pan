"""
ZIP压缩和解压服务模块

提供AES加密压缩和解压功能，支持文件和文件夹的加密打包。

主要功能:
- AES-256加密压缩（使用pyzipper）
- 文件夹递归压缩，保持目录结构
- 解压验证，支持密码验证
- 文件按路径排序确保压缩包一致性

加密说明:
- 使用WinZip AES-256加密算法
- 压缩级别0-9，0为存储模式（不压缩）
- 支持自定义盐值增强安全性
"""

from dowhen import when
import pyzipper
from os import PathLike
import pathlib
import datetime
from typing import Optional

from ..config import ZipConfig


def _add_self_salt(self) -> None:
    """为AES加密ZIP添加随机盐值（内部使用）

    通过dowhen库动态修改AESZipEncrypter类的pwd_verify_length属性，
    以支持任意长度的密码。

    Note:
        这是pyzipper库的特定hack，用于支持短密码
    """
    zip_config = ZipConfig()
    self.salt = zip_config.salt[self.salt_length]


def _add_file_to_zip(zipf: pyzipper.AESZipFile, file_path: pathlib.Path, arcname: str) -> None:
    """添加单个文件到ZIP压缩包

    Args:
        zipf: AESZipFile对象
        file_path: 源文件路径
        arcname: 在ZIP中的文件名（相对路径）
    """
    zipf.write(file_path, arcname)


def _add_directory_to_zip(zipf: pyzipper.AESZipFile, directory_path: pathlib.Path) -> None:
    """添加整个目录到ZIP压缩包

    递归遍历目录，收集所有文件并按路径排序后添加。
    排序确保相同内容的目录在不同环境下产生相同的压缩包。

    Args:
        zipf: AESZipFile对象
        directory_path: 源目录路径

    Note:
        - 使用rglob('*')递归获取所有项
        - 按小写路径名排序确保跨平台一致性
        - 相对路径计算考虑父目录不同的情况
    """
    all_files: list[tuple[pathlib.Path, str]] = []

    # 递归收集所有文件路径
    for file_path in directory_path.rglob('*'):
        if file_path.is_file():
            # 计算在ZIP中的相对路径
            # 如果directory_path.parent != directory_path，说明directory_path不是根目录
            parent = directory_path.parent if directory_path.parent != directory_path else directory_path
            relative_path = file_path.relative_to(parent)
            all_files.append((file_path, str(relative_path)))

    # 按路径排序确保一致性（跨平台、跨文件系统）
    all_files.sort(key=lambda x: x[1].lower())

    # 按排序后的顺序添加文件
    for file_path, arcname in all_files:
        _add_file_to_zip(zipf, file_path, arcname)


class ZipService:
    """ZIP压缩和解压服务类

    提供完整的AES加密压缩和解压功能。

    路径格式约定:
        - 本地ZIP路径: {target_dir}/YYYYMMDD/解压密码_{password}/{source_name}.zip
        - 无密码路径: {target_dir}/YYYYMMDD/{source_name}.zip

    Attributes:
        无类属性，所有方法均为静态方法
    """

    @staticmethod
    def zip_item(
        source_item: PathLike,
        target_dir: PathLike,
        password: Optional[str] = None,
        compress_level: int = 6
    ) -> pathlib.Path:
        """压缩文件或文件夹为AES加密ZIP

        使用WinZip AES-256加密算法对文件进行压缩。

        Args:
            source_item: 源文件或文件夹路径（PathLike类型，支持str、Path等）
            target_dir: 目标目录路径，ZIP文件将创建在此目录下
            password: 压缩密码（可选）
                - 为None时不加密
                - 设置时使用AES-256加密
            compress_level: 压缩级别（0-9）
                - 0: 存储模式，不压缩（推荐用于已压缩文件如zip、mp4）
                - 1: 最快压缩，速度最快但压缩比最低
                - 9: 最优压缩，速度最慢但压缩比最高
                - 默认值: 6（平衡速度与压缩比）

        Returns:
            pathlib.Path: 生成的ZIP文件绝对路径

        Raises:
            FileNotFoundError: 源路径不存在
            IsADirectoryError: 目标路径是文件而非目录
            TypeError: 压缩级别不是整数
            RuntimeError: 压缩过程发生错误

        Example:
            >>> from service.zip_service import ZipService
            >>> # 压缩文件夹（带密码）
            >>> zip_path = ZipService.zip_item(
            ...     source_item='/path/to/folder',
            ...     target_dir='/tmp/compress',
            ...     password='my_secure_password',
            ...     compress_level=0
            ... )
            >>> print(zip_path)
            /tmp/compress/20260118/folder/解压密码_my_secure_password/folder.zip
        """
        source_item = pathlib.Path(source_item)
        target_dir = pathlib.Path(target_dir)

        # 验证输入参数
        if not source_item.exists():
            raise FileNotFoundError(f"源路径不存在: {source_item}")
        if target_dir.is_file():
            raise IsADirectoryError(f"目标路径是文件，应为目录: {target_dir}")
        if not isinstance(compress_level, int):
            raise TypeError(f"压缩级别应为整数，实际为: {type(compress_level)}")

        # 构建输出路径
        # 路径格式: {target_dir}/YYYYMMDD/{source_name}/解压密码_{password}/{source_name}.zip
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        source_parent_name = source_item.parent.name

        # 获取源文件夹名（父目录名）
        # 如果源是文件，直接用文件名
        # 如果源是文件夹，也用文件夹名
        if password:
            # 带密码: {target_dir}/YYYYMMDD/{source_name}/解压密码_{password}/{source_name}.zip
            ziped_item = target_dir / date_str / source_parent_name / f'解压密码_{password}' / f'{source_item.name}.zip'
        else:
            # 无密码: {target_dir}/YYYYMMDD/{source_name}/{source_name}.zip
            ziped_item = target_dir / date_str / source_parent_name / f'{source_item.name}.zip'

        # 确保父目录存在
        ziped_item.parent.mkdir(parents=True, exist_ok=True)

        # 限制压缩级别在有效范围[0, 9]
        compress_level = max(0, min(9, compress_level))

        try:
            # 使用dowhen库动态修改AESZipEncrypter以支持短密码
            with when(pyzipper.zipfile_aes.AESZipEncrypter, 'pwd_verify_length = 2').do(_add_self_salt):
                with pyzipper.AESZipFile(
                    ziped_item,
                    'w',
                    compression=pyzipper.ZIP_DEFLATED,
                    compresslevel=compress_level,
                ) as zipf:
                    # 设置加密密码
                    if password:
                        zipf.setpassword(password.encode('utf-8'))
                        # 设置加密方法为AES（WinZip兼容）
                        zipf.encryption = pyzipper.WZ_AES

                    # 根据源类型添加文件或目录
                    if source_item.is_file():
                        _add_file_to_zip(zipf, source_item, source_item.name)
                    elif source_item.is_dir():
                        _add_directory_to_zip(zipf, source_item)
                    else:
                        raise ValueError(f"不支持的源路径类型: {source_item}")

                    return ziped_item

        except Exception as e:
            # 失败时清理已创建的不完整文件
            if ziped_item.exists():
                ziped_item.unlink()
            raise

    @staticmethod
    def unzip_item(
        zip_path: PathLike,
        target_dir: Optional[PathLike] = None,
        password: Optional[str] = None
    ) -> pathlib.Path:
        """解压ZIP文件到目标目录

        解压使用WinZip AES加密的ZIP文件，支持密码验证。
        路径格式遵循PRD规范:
        {extract_dir}/YYYYMMDD/{源文件夹名}/解压密码_{password}/{源文件夹名}

        Args:
            zip_path: ZIP文件路径
            target_dir: 目标目录路径
                - 为None时使用ZipConfig.unzip_folder
                - 默认值: None
            password: 解压密码（可选）
                - 为None时假设ZIP无密码
                - 密码错误会抛出异常

        Returns:
            pathlib.Path: 解压后的根目录绝对路径

        Raises:
            FileNotFoundError: ZIP文件不存在
            RuntimeError: 解压过程发生错误（如密码错误）

        Example:
            >>> from service.zip_service import ZipService
            >>> extract_path = ZipService.unzip_item(
            ...     zip_path='/tmp/compress/20260118/folder/解压密码_pass/folder.zip',
            ...     target_dir='/tmp/extract',
            ...     password='pass'
            ... )
            >>> print(extract_path)
            /tmp/extract/20260118/folder/解压密码_pass/folder
        """
        import re as re_module
        zip_path = pathlib.Path(zip_path)
        print(f"解压ZIP文件: {zip_path}")

        if target_dir is None:
            target_dir = pathlib.Path(ZipConfig.unzip_folder)
        else:
            target_dir = pathlib.Path(target_dir)

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP文件不存在: {zip_path}")

        # 从ZIP路径提取源文件夹名
        # 路径格式: {xxx}/YYYYMMDD/{source_folder}/解压密码_xxx/{source_name}.zip
        path_parts = zip_path.parent.parts
        source_folder = None
        date_str = None
        for i, part in enumerate(path_parts):
            # 检查是否是日期
            if re_module.match(r'^\d{8}$', part):
                date_str = part
                # 源文件夹名在日期后面
                if i + 1 < len(path_parts):
                    source_folder = path_parts[i + 1]
                break

        if not source_folder:
            # 回退: 使用ZIP文件名（不含扩展名）
            source_folder = zip_path.stem
            if source_folder.endswith('.zip'):
                source_folder = source_folder[:-4]

        # 构建目标路径: {target_dir}/YYYYMMDD/{source_name}/解压密码_{password}/{source_name}
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y%m%d")

        if password:
            extract_base = target_dir / date_str / source_folder / f'解压密码_{password}'
        else:
            extract_base = target_dir / date_str / source_folder

        extract_to = extract_base / zip_path.stem


        # 确保目标目录存在
        extract_base.mkdir(parents=True, exist_ok=True)

        try:
            with pyzipper.AESZipFile(zip_path, 'r') as zipf:
                if password:
                    zipf.setpassword(password.encode('utf-8'))

                # 解压到目标目录
                zipf.extractall(extract_base)
                print(f"解压完成: {extract_to}")
                return extract_to

        except Exception as e:
            # 失败时清理目标目录
            if extract_base.exists():
                import shutil
                shutil.rmtree(extract_base, ignore_errors=True)
            raise RuntimeError(f"解压失败: {e}")
