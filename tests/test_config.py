"""config.py 测试用例"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.config import (
    HashConfig, ClassifyConfig, ZipConfig, DatabasePoolConfig, UploadConfig,
    SpaceConfig, SourceConfig, StorageConfig, Config,
    load_config, get_env, get_env_int, get_env_bool, get_hostname,
    is_archive_file, ARCHIVE_EXTENSIONS,
    DatabaseCredentials, BaiduPanCredentials, SMTPCredentials,
)


class TestHashConfig:
    """HashConfig测试"""

    def test_default_hash_algorithms(self):
        """CONFIG-001: 默认Hash算法"""
        config = HashConfig()
        assert config.required_hash_algorithms == ['md5', 'sha1', 'sha256']

    def test_custom_hash_algorithms(self):
        """CONFIG-002: 自定义Hash算法"""
        config = HashConfig(required_hash_algorithms=['md5'])
        assert config.required_hash_algorithms == ['md5']

    def test_hash_config_immutable_default(self):
        """验证默认列表不会意外共享"""
        config1 = HashConfig()
        config2 = HashConfig()
        config1.required_hash_algorithms.append('sha512')
        assert 'sha512' not in config2.required_hash_algorithms


class TestClassifyConfig:
    """ClassifyConfig测试"""

    def test_default_values(self):
        """CONFIG-003: 默认分类配置"""
        config = ClassifyConfig()
        assert config.file_oversize == 20 * 1024**3
        assert config.folder_oversize == 20 * 1024**3
        assert config.overcount == 200

    def test_custom_values(self):
        """CONFIG-004: 自定义分类配置"""
        config = ClassifyConfig(file_oversize=1 * 1024**3)
        assert config.file_oversize == 1 * 1024**3


class TestZipConfig:
    """ZipConfig测试"""

    def test_default_values(self):
        """CONFIG-005: 默认ZIP配置"""
        config = ZipConfig()
        assert config.compress_level == 0
        assert config.default_password == 'backup123'
        assert config.salt_length == 16

    def test_salt_config(self):
        """CONFIG-006: ZIP盐值配置"""
        config = ZipConfig()
        assert 8 in config.salt
        assert 12 in config.salt
        assert 16 in config.salt
        assert len(config.salt[16]) == 16


class TestDatabasePoolConfig:
    """DatabasePoolConfig测试"""

    def test_default_values(self):
        """CONFIG-007: 默认数据库池配置"""
        config = DatabasePoolConfig()
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30

    def test_get_url(self):
        """CONFIG-008: 生成数据库URL"""
        config = DatabasePoolConfig()
        url = config.get_url('localhost', 3306, 'user', 'pass', 'mydb')
        assert url == 'mysql+pymysql://user:pass@localhost:3306/mydb'

    def test_get_url_with_special_chars(self):
        """CONFIG-009: URL包含特殊字符密码"""
        config = DatabasePoolConfig()
        # 注意: 这个测试验证基本URL生成，特殊字符编码在连接时处理
        url = config.get_url('localhost', 3306, 'user', 'p@ss:word', 'mydb')
        assert 'p@ss:word' in url


class TestUploadConfig:
    """UploadConfig测试"""

    def test_default_values(self):
        """CONFIG-010: 默认上传配置"""
        config = UploadConfig()
        assert config.chunk_size_mb == 20
        assert config.retry_times == 5
        assert config.baidu_pan_dir == '/item_backup'

    def test_custom_chunk_size(self):
        """自定义分片大小"""
        config = UploadConfig(chunk_size_mb=50)
        assert config.chunk_size_mb == 50


class TestSpaceConfig:
    """SpaceConfig测试"""

    def test_default_value(self):
        """CONFIG-011: 默认空间配置"""
        config = SpaceConfig()
        assert config.disk_limit_gb == 80


class TestSourceConfig:
    """SourceConfig测试"""

    def test_default_values(self):
        """CONFIG-012: 默认源配置"""
        config = SourceConfig()
        assert config.paths == []
        assert config.path == Path('')
        assert config.password == ''


class TestStorageConfig:
    """StorageConfig测试"""

    def test_default_values(self):
        """CONFIG-013: 默认存储配置"""
        config = StorageConfig()
        assert config.compress_dir == Path('/tmp/compress')
        assert config.extract_dir == Path('/tmp/extract')


class TestConfig:
    """Config测试"""

    def test_default_config(self):
        """CONFIG-014: 默认完整配置"""
        config = Config()
        assert isinstance(config.source, SourceConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.hash, HashConfig)
        assert isinstance(config.classify, ClassifyConfig)
        assert isinstance(config.zip, ZipConfig)
        assert isinstance(config.upload, UploadConfig)
        assert isinstance(config.space, SpaceConfig)

    def test_from_dict_full_config(self):
        """CONFIG-015: 解析完整配置"""
        data = {
            'source': {'paths': ['/test1', '/test2']},
            'storage': {'compress_dir': '/custom/compress', 'extract_dir': '/custom/extract'},
            'database': {'pool_size': 10},
            'limits': {'max_file_size_gb': 15},
            'compression': {'level': 5},
            'upload': {'chunk_size_mb': 30},
        }
        config = Config.from_dict(data)

        assert len(config.source.paths) == 2
        assert config.storage.compress_dir == Path('/custom/compress')
        assert config.storage.extract_dir == Path('/custom/extract')
        assert config.database.pool_size == 10
        assert config.classify.file_oversize == 15 * 1024**3
        assert config.zip.compress_level == 5
        assert config.upload.chunk_size_mb == 30

    def test_from_dict_with_disk_limit(self):
        """测试disk_limit配置"""
        data = {
            'storage': {'disk_limit_gb': 100},
        }
        config = Config.from_dict(data)
        assert config.space.disk_limit_gb == 100

    def test_from_dict_string_path(self):
        """CONFIG-016: 解析字符串路径"""
        data = {'source': {'path': '/test'}}
        config = Config.from_dict(data)
        assert config.source.path == Path('/test')

    def test_from_dict_paths_list(self):
        """CONFIG-017: 解析路径列表"""
        data = {'source': {'paths': ['/a', '/b']}}
        config = Config.from_dict(data)
        assert len(config.source.paths) == 2
        assert all(isinstance(p, Path) for p in config.source.paths)

    def test_from_dict_empty_config(self):
        """CONFIG-019: 解析空配置使用默认值"""
        config = Config.from_dict({})
        assert config.source.paths == []
        assert config.database.pool_size == 5

    def test_from_dict_limits_config(self):
        """CONFIG-020: 解析限制配置"""
        data = {'limits': {'max_file_size_gb': 10, 'max_files_per_folder': 100}}
        config = Config.from_dict(data)
        assert config.classify.file_oversize == 10 * 1024**3
        assert config.classify.overcount == 100

    def test_from_dict_compression_config(self):
        """CONFIG-021: 解析压缩配置"""
        data = {'compression': {'level': 9}}
        config = Config.from_dict(data)
        assert config.zip.compress_level == 9

    def test_from_dict_upload_config(self):
        """CONFIG-022: 解析上传配置"""
        data = {'upload': {'chunk_size_mb': 100, 'retry_times': 10}}
        config = Config.from_dict(data)
        assert config.upload.chunk_size_mb == 100
        assert config.upload.retry_times == 10


class TestLoadConfig:
    """load_config函数测试"""

    def test_load_config_exists(self, test_temp_dir):
        """加载存在的配置文件"""
        config_file = test_temp_dir / "config.toml"
        config_file.write_text("""
[source]
paths = ["/test"]

[storage]
compress_dir = "/tmp/compress"
extract_dir = "/tmp/extract"

[limits]
max_file_size_gb = 10
max_files_per_folder = 100
""")
        config = load_config(config_file)
        assert len(config.source.paths) == 1
        assert config.classify.file_oversize == 10 * 1024**3

    def test_load_config_not_exists(self):
        """CONFIG-184: 加载不存在的配置文件返回默认"""
        config = load_config('/nonexistent/path/config.toml')
        assert isinstance(config, Config)
        assert config.source.paths == []


class TestEnvironmentFunctions:
    """环境变量函数测试"""

    def test_get_env_exists(self, patch_env_variables):
        """CONFIG-024: 获取存在的环境变量"""
        result = get_env('MYSQL_HOST')
        assert result == 'localhost'

    def test_get_env_not_exists(self, patch_env_variables):
        """CONFIG-025: 获取不存在的环境变量返回默认值"""
        result = get_env('NONEXISTENT_KEY', 'default_value')
        assert result == 'default_value'

    def test_get_env_int_valid(self, patch_env_variables):
        """CONFIG-026: 获取有效的整数环境变量"""
        result = get_env_int('MYSQL_PORT', 3306)
        assert result == 3306

    def test_get_env_int_invalid(self, patch_env_variables):
        """CONFIG-027: 获取无效的整数环境变量会抛出异常"""
        import os
        os.environ['INVALID_PORT'] = 'abc'
        # get_env_int对于无效值会抛出ValueError
        with pytest.raises(ValueError):
            get_env_int('INVALID_PORT', 0)
        del os.environ['INVALID_PORT']

    def test_get_env_bool_true(self, patch_env_variables):
        """CONFIG-028, CONFIG-029: 获取布尔true值"""
        import os
        os.environ['TRUE_VAR'] = 'true'
        os.environ['TRUE_VAR2'] = '1'
        os.environ['TRUE_VAR3'] = 'yes'
        assert get_env_bool('TRUE_VAR', False) is True
        assert get_env_bool('TRUE_VAR2', False) is True
        assert get_env_bool('TRUE_VAR3', False) is True
        del os.environ['TRUE_VAR']
        del os.environ['TRUE_VAR2']
        del os.environ['TRUE_VAR3']

    def test_get_env_bool_false(self, patch_env_variables):
        """CONFIG-030, CONFIG-031: 获取布尔false值"""
        import os
        os.environ['FALSE_VAR'] = 'false'
        os.environ['FALSE_VAR2'] = '0'
        os.environ['FALSE_VAR3'] = 'no'
        assert get_env_bool('FALSE_VAR', True) is False
        assert get_env_bool('FALSE_VAR2', True) is False
        assert get_env_bool('FALSE_VAR3', True) is False
        del os.environ['FALSE_VAR']
        del os.environ['FALSE_VAR2']
        del os.environ['FALSE_VAR3']

    def test_get_env_bool_default(self, patch_env_variables):
        """CONFIG-032: 无效布尔值返回默认值"""
        import os
        os.environ['INVALID_BOOL'] = 'invalid'
        assert get_env_bool('INVALID_BOOL', False) is False
        del os.environ['INVALID_BOOL']

    @patch('socket.gethostname')
    def test_get_hostname_success(self, mock_gethostname):
        """CONFIG-033: 获取主机名成功"""
        mock_gethostname.return_value = 'test-host'
        result = get_hostname()
        assert result == 'test-host'

    @patch('socket.gethostname')
    def test_get_hostname_failure(self, mock_gethostname):
        """CONFIG-034: 获取主机名失败返回localhost"""
        mock_gethostname.side_effect = Exception('Network error')
        result = get_hostname()
        assert result == 'localhost'


class TestIsArchiveFile:
    """is_archive_file函数测试"""

    def test_archive_zip(self):
        """CONFIG-035: ZIP文件"""
        assert is_archive_file("file.zip") is True

    def test_archive_7z(self):
        """CONFIG-036: 7Z文件"""
        assert is_archive_file("file.7z") is True

    def test_archive_tar(self):
        """CONFIG-037: TAR文件"""
        assert is_archive_file("file.tar") is True

    def test_archive_gz(self):
        """CONFIG-037: GZ文件"""
        assert is_archive_file("file.gz") is True

    def test_not_archive(self):
        """CONFIG-038: 非压缩文件"""
        assert is_archive_file("file.txt") is False
        assert is_archive_file("file.mp4") is False
        assert is_archive_file("document.pdf") is False

    def test_archive_apk(self):
        """CONFIG-039: APK文件"""
        assert is_archive_file("app.apk") is True

    def test_archive_case_insensitive(self):
        """CONFIG-040: 大小写不敏感"""
        assert is_archive_file("file.ZIP") is True
        assert is_archive_file("file.Tar") is True

    def test_archive_extensions_complete(self):
        """CONFIG-041: 验证所有扩展名"""
        expected = {
            '.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz',
            '.tgz', '.tbz2', '.txz', '.tar.gz', '.tar.bz2', '.tar.xz',
            '.zipx', '.apk', '.jar', '.war', '.ear'
        }
        assert ARCHIVE_EXTENSIONS == expected


class TestCredentials:
    """凭证类测试"""

    def test_database_credentials_default(self, patch_env_variables):
        """CONFIG-042: 默认数据库凭证"""
        creds = DatabaseCredentials()
        assert creds.host == 'localhost'
        assert creds.port == 3306
        assert creds.username == 'test_user'
        assert creds.password == 'test_password'
        assert creds.name == 'test_db'

    def test_database_credentials_url(self, patch_env_variables):
        """CONFIG-043: 数据库凭证URL"""
        creds = DatabaseCredentials()
        assert 'mysql+pymysql://' in creds.url
        assert 'test_user' in creds.url

    def test_baidu_pan_credentials_default(self, patch_env_variables):
        """CONFIG-044: 默认百度网盘凭证"""
        creds = BaiduPanCredentials()
        assert creds.access_token == 'test_token'
        assert creds.refresh_token == 'test_refresh'

    def test_smtp_credentials_default(self, patch_env_variables):
        """CONFIG-045: 默认SMTP凭证"""
        creds = SMTPCredentials()
        assert creds.host == 'smtp.test.com'
        assert creds.port == 465

    def test_smtp_credentials_admin_emails(self, patch_env_variables):
        """CONFIG-046: SMTP多管理员邮箱"""
        creds = SMTPCredentials()
        assert len(creds.admin_emails) == 2
        assert 'admin@test.com' in creds.admin_emails
        assert 'test@test.com' in creds.admin_emails

    def test_smtp_credentials_fallback_vars(self):
        """CONFIG-047: SMTP备用变量名"""
        # 使用SMTP_SERVER替代SMTP_HOST，且不设置SMTP_HOST
        env = {
            'SMTP_SERVER': 'fallback.host.com',
            'SMTP_PORT': '465',
            'SMTP_USER': 'test@test.com',
            'SMTP_PASSWORD': 'password',
            'ADMIN_EMAILS': 'admin@test.com',
        }
        with patch.dict(os.environ, env, clear=True):
            creds = SMTPCredentials()
            assert creds.host == 'fallback.host.com'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
