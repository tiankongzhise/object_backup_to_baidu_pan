"""Pytest配置文件和共享fixtures"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import shutil

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 测试数据目录和临时文件目录
TEST_DATA_DIR = Path("D:/test_case_data")
TEST_TEMP_DIR = Path("D:/test_case_temp")


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录 fixture"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def test_temp_dir():
    """测试临时目录 fixture"""
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_TEMP_DIR


@pytest.fixture(autouse=True)
def cleanup_temp_files(test_temp_dir):
    """自动清理临时文件"""
    yield
    # 清理临时目录下的内容，但保留目录本身
    try:
        for item in test_temp_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture
def temp_file(test_temp_dir):
    """创建临时文件"""
    fd, path = tempfile.mkstemp(dir=test_temp_dir)
    os.close(fd)
    yield Path(path)
    if path.exists():
        os.unlink(path)


@pytest.fixture
def temp_dir(test_temp_dir):
    """创建临时目录"""
    path = test_temp_dir / f"temp_{os.getpid()}_{id(temp_dir)}"
    path.mkdir(parents=True, exist_ok=True)
    yield path
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def small_file(test_temp_dir):
    """创建小测试文件"""
    content = b"Hello, Test World!" * 100  # ~2KB
    path = test_temp_dir / "small_test.txt"
    path.write_bytes(content)
    return path


@pytest.fixture
def medium_file(test_temp_dir):
    """创建中等测试文件 (~1MB)"""
    content = b"X" * (1024 * 1024)
    path = test_temp_dir / "medium_test.bin"
    path.write_bytes(content)
    return path


@pytest.fixture
def empty_file(test_temp_dir):
    """创建空测试文件"""
    path = test_temp_dir / "empty_test.txt"
    path.write_bytes(b"")
    return path


@pytest.fixture
def sample_folder(test_temp_dir):
    """创建测试文件夹"""
    folder = test_temp_dir / "sample_folder"
    folder.mkdir(parents=True, exist_ok=True)

    # 创建子文件和文件夹
    (folder / "file1.txt").write_bytes(b"Content 1")
    (folder / "file2.txt").write_bytes(b"Content 2")
    (folder / "subdir").mkdir()
    (folder / "subdir" / "file3.txt").write_bytes(b"Content 3")

    return folder


@pytest.fixture
def large_folder(test_temp_dir):
    """创建包含多个文件的大测试文件夹"""
    folder = test_temp_dir / "large_folder"
    folder.mkdir(parents=True, exist_ok=True)

    # 创建多个文件
    for i in range(50):
        (folder / f"file_{i}.txt").write_bytes(f"Content {i}".encode() * 100)

    return folder


@pytest.fixture
def mock_hash_values():
    """模拟Hash值"""
    return {
        'md5': 'D41D8CD98F00B204E9800998ECF8427E',
        'sha1': 'DA39A3EE5E6B4B0D3255BFEF95601890AFD80709',
        'sha256': 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
    }


@pytest.fixture
def mock_session():
    """创建模拟的数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def mock_db_service():
    """创建模拟的数据库服务"""
    service = MagicMock()
    service.get_session.return_value.__enter__ = MagicMock(
        return_value=mock_session()
    )
    service.get_session.return_value.__exit__ = MagicMock(return_value=False)
    return service


@pytest.fixture
def patch_env_variables():
    """设置测试环境变量"""
    env_vars = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': '3306',
        'MYSQL_USER': 'test_user',
        'MYSQL_PASSWORD': 'test_password',
        'MYSQL_DATABASE': 'test_db',
        'BAIDU_PAN_ACCESS_TOKEN': 'test_token',
        'BAIDU_PAN_REFRESH_TOKEN': 'test_refresh',
        'BAIDU_PAN_APP_KEY': 'test_app_key',
        'BAIDU_PAN_SECRET_KEY': 'test_secret',
        'SMTP_HOST': 'smtp.test.com',
        'SMTP_PORT': '465',
        'SMTP_USER': 'test@test.com',
        'SMTP_PASSWORD': 'test_smtp_password',
        'ADMIN_EMAILS': 'admin@test.com,test@test.com',
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def reset_config_singletons():
    """重置配置单例"""
    from object_backup_to_baidu_pan.config import HashConfig, ClassifyConfig, ZipConfig, UploadConfig, SpaceConfig
    HashConfig.required_hash_algorithms = ['md5', 'sha1', 'sha256']
    ClassifyConfig.file_oversize = 20 * 1024**3
    ClassifyConfig.folder_oversize = 20 * 1024**3
    ClassifyConfig.overcount = 200
    ZipConfig.compress_level = 0
    UploadConfig.chunk_size_mb = 20
    UploadConfig.retry_times = 5
    SpaceConfig.disk_limit_gb = 80
    yield


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 根据文件路径标记集成测试
    for item in items:
        if "orchestrator" in str(item.fspath) or "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
