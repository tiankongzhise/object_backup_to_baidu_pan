"""配置模块

提供应用程序的所有配置管理，包括：
- 应用配置 (config.toml)：非敏感配置
- 环境变量 (.env)：敏感信息（密码、Token等）
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal, Callable
import os


@dataclass
class HashConfig:
    """Hash算法配置"""
    required_hash_algorithms: list[str] = field(default_factory=lambda: ['md5', 'sha1', 'sha256'])


@dataclass
class ClassifyConfig:
    """文件分类配置"""
    file_oversize: int = 20 * 1024**3  # 20GB
    folder_oversize: int = 20 * 1024**3  # 20GB
    overcount: int = 200  # 直接子文件数限制
    unzip_folder: Path = Path('/tmp/unzip')


@dataclass
class ZipConfig:
    """ZIP压缩配置"""
    salt: dict[int, bytes] = field(default_factory=lambda: {
        8: b"\xaa%\xec\xec[\x94\xbex",
        12: b"}y\xd5\x19A\xa2\xf6\x1b\xce\x86\x7f\x85",
        16: b"\xd1\x12_\xd7\xd7\n\x92\xfdC\x84\re\xcdxD\x0b",
    })
    salt_length: int = 16
    compress_level: int = 0  # 存储模式，不压缩
    default_password: str = 'backup123'


@dataclass
class DatabasePoolConfig:
    """数据库连接池配置（非敏感）"""
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True  # 连接前检测连接有效性
    echo: bool = False

    def get_url(self, host: str, port: int, username: str, password: str, name: str) -> str:
        """构建数据库URL

        Args:
            host: 数据库主机
            port: 端口
            username: 用户名
            password: 密码
            name: 数据库名

        Returns:
            str: SQLAlchemy数据库URL
        """
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{name}"


@dataclass
class UploadConfig:
    """上传配置"""
    chunk_size_mb: int = 20
    retry_times: int = 5
    baidu_pan_dir: str = '/item_backup'
    default_password: str = 'backup123'


@dataclass
class SpaceConfig:
    """空间管理配置"""
    disk_limit_gb: int = 80


@dataclass
class SourceConfig:
    """源文件夹配置（非敏感）"""
    path: Path = Path('')
    password: str = ''  # ZIP加密密码，从环境变量读取更安全


@dataclass
class StorageConfig:
    """存储路径配置（非敏感）"""
    compress_dir: Path = Path('/tmp/compress')
    extract_dir: Path = Path('/tmp/extract')


@dataclass
class Config:
    """主配置类（非敏感配置部分）"""
    source: SourceConfig = field(default_factory=SourceConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    database: DatabasePoolConfig = field(default_factory=DatabasePoolConfig)
    hash: HashConfig = field(default_factory=HashConfig)
    classify: ClassifyConfig = field(default_factory=ClassifyConfig)
    zip: ZipConfig = field(default_factory=ZipConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    space: SpaceConfig = field(default_factory=SpaceConfig)
    # 回调函数（不持久化）
    on_progress: Callable = None
    on_log: Callable = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """从字典创建配置（仅处理非敏感配置）"""
        config = cls()

        if 'source' in data:
            config.source = SourceConfig(
                path=Path(data['source'].get('path', '')),
                password=data['source'].get('password', ''),
            )

        if 'storage' in data:
            config.storage = StorageConfig(
                compress_dir=Path(data['storage'].get('compress_dir', '/tmp/compress')),
                extract_dir=Path(data['storage'].get('extract_dir', '/tmp/extract'))
            )

        if 'database' in data:
            db_data = data['database']
            config.database = DatabasePoolConfig(
                pool_size=db_data.get('pool_size', 5),
                max_overflow=db_data.get('max_overflow', 10),
                pool_timeout=db_data.get('pool_timeout', 30),
                pool_recycle=db_data.get('pool_recycle', 3600),
                echo=db_data.get('echo', False),
            )

        if 'limits' in data:
            config.classify = ClassifyConfig(
                file_oversize=data['limits'].get('max_file_size_gb', 20) * 1024**3,
                folder_oversize=data['limits'].get('max_file_size_gb', 20) * 1024**3,
                overcount=data['limits'].get('max_files_per_folder', 200)
            )

        if 'compression' in data:
            config.zip.compress_level = data['compression'].get('level', 0)

        if 'upload' in data:
            config.upload.chunk_size_mb = data['upload'].get('chunk_size_mb', 20)
            config.upload.retry_times = data['upload'].get('retry_times', 5)

        if 'storage' in data:
            config.space.disk_limit_gb = data['storage'].get('disk_limit_gb', 80)

        return config


def load_config(config_path: str | Path = 'config.toml') -> Config:
    """从TOML文件加载非敏感配置

    Args:
        config_path: 配置文件路径

    Returns:
        Config: 配置对象
    """
    import tomllib

    if isinstance(config_path, str):
        config_path = Path(config_path)

    if not config_path.exists():
        return Config()

    with open(config_path, 'rb') as f:
        data = tomllib.load(f)

    return Config.from_dict(data)


def get_env(key: str, default: str = '') -> str:
    """获取环境变量

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        str: 环境变量值
    """
    return os.environ.get(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """获取整数环境变量"""
    return int(os.environ.get(key, str(default)))


def get_env_bool(key: str, default: bool = False) -> bool:
    """获取布尔环境变量"""
    value = os.environ.get(key, '').lower()
    if value in ('true', '1', 'yes'):
        return True
    if value in ('false', '0', 'no'):
        return False
    return default


class DatabaseCredentials:
    """数据库连接凭证（从环境变量读取）"""

    def __init__(self):
        self.host = get_env('MYSQL_HOST', 'localhost')
        self.port = get_env_int('MYSQL_PORT', 3306)
        self.username = get_env('MYSQL_USER', 'root')
        self.password = get_env('MYSQL_PASSWORD', '')
        self.name = get_env('MYSQL_DATABASE', 'backup_db')

    @property
    def url(self) -> str:
        """返回数据库URL"""
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class BaiduPanCredentials:
    """百度网盘凭证（从环境变量读取）"""

    def __init__(self):
        self.access_token = get_env('BAIDU_PAN_ACCESS_TOKEN', '')
        self.refresh_token = get_env('BAIDU_PAN_REFRESH_TOKEN', '')
        self.app_key = get_env('BAIDU_PAN_APP_KEY', '')
        self.secret_key = get_env('BAIDU_PAN_SECRET_KEY', '')


class SMTPCredentials:
    """SMTP邮件凭证（从环境变量读取）"""

    def __init__(self):
        self.host = get_env('SMTP_HOST', '')
        self.port = get_env_int('SMTP_PORT', 465)
        self.username = get_env('SMTP_USER', '')
        self.password = get_env('SMTP_PASSWORD', '')


__all__ = [
    # 配置类
    'Config',
    'HashConfig',
    'ClassifyConfig',
    'ZipConfig',
    'DatabasePoolConfig',
    'UploadConfig',
    'SpaceConfig',
    'SourceConfig',
    'StorageConfig',
    # 凭证类
    'DatabaseCredentials',
    'BaiduPanCredentials',
    'SMTPCredentials',
    # 工具函数
    'load_config',
    'get_env',
    'get_env_int',
    'get_env_bool',
]
