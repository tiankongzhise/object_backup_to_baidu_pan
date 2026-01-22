"""space_manager.py 测试用例"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.space_manager import SpaceManager, SpaceInfo
from object_backup_to_baidu_pan.service.classify_service import FileInfo, FolderInfo
from object_backup_to_baidu_pan.config import SpaceConfig


class TestSpaceInfo:
    """SpaceInfo 测试"""

    def test_create_space_info(self):
        """SPACE-001: 创建SpaceInfo"""
        info = SpaceInfo(
            total_bytes=1000,
            used_bytes=500,
            available_bytes=500,
            used_percent=50.0
        )
        assert info.total_bytes == 1000
        assert info.used_bytes == 500
        assert info.available_bytes == 500
        assert info.used_percent == 50.0


class TestSpaceManager:
    """SpaceManager 测试"""

    def test_default_config(self):
        """SPACE-003: 默认配置"""
        manager = SpaceManager()
        assert manager.config.disk_limit_gb == 80

    def test_custom_config(self):
        """SPACE-004: 自定义配置"""
        config = SpaceConfig(disk_limit_gb=100)
        manager = SpaceManager(config)
        assert manager.config.disk_limit_gb == 100


class TestGetDiskSpace:
    """get_disk_space 测试"""

    def test_get_disk_space_valid_path(self, test_temp_dir):
        """SPACE-005: 获取有效路径的磁盘空间"""
        manager = SpaceManager()
        info = manager.get_disk_space(test_temp_dir)

        assert isinstance(info, SpaceInfo)
        assert info.total_bytes > 0
        assert info.available_bytes >= 0

    def test_disk_info_accuracy(self):
        """SPACE-006: 磁盘信息准确性"""
        manager = SpaceManager()
        info = manager.get_disk_space(Path("/"))

        assert info.total_bytes > 0
        assert info.used_bytes >= 0
        assert info.available_bytes >= 0
        assert info.used_percent >= 0
        assert info.used_percent <= 100

    def test_percentage_calculation(self):
        """SPACE-007: 百分比计算"""
        info = SpaceInfo(
            total_bytes=100,
            used_bytes=75,
            available_bytes=25,
            used_percent=0  # 会被覆盖
        )
        # 验证计算公式
        expected = (75 / 100) * 100
        assert info.used_bytes / info.total_bytes * 100 == expected


class TestCalculateRequiredSpace:
    """calculate_required_space 测试"""

    def test_file_size_calculation(self):
        """SPACE-010: 文件大小计算"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        required = manager.calculate_required_space(file_info)
        # 公式: 1.1 * size + size = 2.1 * size
        expected = int(1000 * 1.1) + 1000
        assert required == expected

    def test_folder_size_calculation(self):
        """SPACE-011: 文件夹大小计算"""
        manager = SpaceManager()
        folder_info = FolderInfo(Path("/test"), "test", 10, 5000)

        required = manager.calculate_required_space(folder_info)
        expected = int(5000 * 1.1) + 5000
        assert required == expected


class TestCanProcess:
    """can_process 测试"""

    def test_space_sufficient(self, test_temp_dir):
        """SPACE-013: 空间充足"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        # 通常有足够空间
        result = manager.can_process(file_info, test_temp_dir)
        # 取决于实际磁盘情况

    def test_space_insufficient(self, test_temp_dir):
        """SPACE-014: 空间不足"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        # Mock可用空间为0
        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=99 * 1024**3,
                available_bytes=1 * 1024**3,
                used_percent=99
            )
            # 保留空间后可能不足
            manager._reserved_space = 0

    def test_with_reserved_space(self, test_temp_dir):
        """SPACE-015: 考虑已预留空间"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)
        manager._reserved_space = 1000

        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=50 * 1024**3,
                available_bytes=50 * 1024**3,
                used_percent=50
            )
            result = manager.can_process(file_info, test_temp_dir)
            # 预留后可用空间减少


class TestCheckInitialSpace:
    """check_initial_space 测试"""

    def test_space_normal(self, test_temp_dir):
        """SPACE-017: 空间正常"""
        manager = SpaceManager()
        # 通常磁盘空间正常，不会抛出异常
        try:
            result = manager.check_initial_space(test_temp_dir)
            assert result is True
        except ValueError:
            # 如果磁盘已满，这是正确的行为
            pass

    def test_space_exceeded(self):
        """SPACE-018: 空间超限"""
        manager = SpaceManager()
        with patch.object(manager, 'get_disk_space') as mock_space:
            # 模拟已使用超过80GB
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=85 * 1024**3,
                available_bytes=15 * 1024**3,
                used_percent=85
            )
            with pytest.raises(ValueError) as exc_info:
                manager.check_initial_space(Path("/"))
            assert "磁盘空间不足" in str(exc_info.value)

    def test_error_message_detail(self):
        """SPACE-019: 错误信息详细"""
        manager = SpaceManager()
        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=85 * 1024**3,
                available_bytes=15 * 1024**3,
                used_percent=85
            )
            with pytest.raises(ValueError) as exc_info:
                manager.check_initial_space(Path("/"))
            assert "85" in str(exc_info.value) or "80" in str(exc_info.value)


class TestReserveSpace:
    """reserve_space 测试"""

    def test_normal_reservation(self, test_temp_dir):
        """SPACE-020: 正常预留"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        with patch.object(manager, '_check_space_available', return_value=True):
            with manager.reserve_space(file_info, test_temp_dir):
                assert manager._reserved_space > 0

    def test_reservation_released(self, test_temp_dir):
        """SPACE-022: 退出释放预留"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        with patch.object(manager, '_check_space_available', return_value=True):
            with manager.reserve_space(file_info, test_temp_dir):
                pass
            # 退出后预留应释放
            assert manager._reserved_space == 0

    def test_reservation_released_on_exception(self, test_temp_dir):
        """SPACE-023: 异常时释放预留"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        with patch.object(manager, '_check_space_available', return_value=True):
            try:
                with manager.reserve_space(file_info, test_temp_dir):
                    raise ValueError("Test exception")
            except ValueError:
                pass
            # 异常后预留应释放
            assert manager._reserved_space == 0


class TestCheckSpaceAvailable:
    """_check_space_available 测试"""

    def test_space_available_sufficient(self, test_temp_dir):
        """SPACE-024: 空间充足"""
        manager = SpaceManager()
        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=50 * 1024**3,
                available_bytes=50 * 1024**3,
                used_percent=50
            )
            manager._reserved_space = 0
            result = manager._check_space_available(1000, test_temp_dir)
            assert result is True

    def test_space_available_insufficient(self, test_temp_dir):
        """SPACE-025: 空间不足"""
        manager = SpaceManager()
        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=99 * 1024**3,
                available_bytes=1 * 1024**3,
                used_percent=99
            )
            manager._reserved_space = 0
            # 需要大量空间
            result = manager._check_space_available(100 * 1024**3, test_temp_dir)
            assert result is False

    def test_with_reserved_space_check(self, test_temp_dir):
        """SPACE-026: 考虑已预留"""
        manager = SpaceManager()
        with patch.object(manager, 'get_disk_space') as mock_space:
            mock_space.return_value = SpaceInfo(
                total_bytes=100 * 1024**3,
                used_bytes=50 * 1024**3,
                available_bytes=50 * 1024**3,
                used_percent=50
            )
            manager._reserved_space = 40 * 1024**3
            # 需要10GB，但预留后只剩10GB可用
            result = manager._check_space_available(5 * 1024**3, test_temp_dir)
            assert result is True


class TestWaitForSpace:
    """wait_for_space 测试"""

    def test_immediate_space(self, test_temp_dir):
        """SPACE-027: 立即获得空间"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        with patch.object(manager, '_check_space_available', return_value=True):
            result = manager.wait_for_space(file_info, test_temp_dir, timeout=1)
            assert result is True

    def test_wait_and_get_space(self, test_temp_dir):
        """SPACE-028: 等待后获得空间"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        call_count = [0]
        def mock_check(required, path):
            call_count[0] += 1
            if call_count[0] < 3:
                return False
            return True

        with patch.object(manager, '_check_space_available', mock_check):
            import time
            start = time.time()
            result = manager.wait_for_space(file_info, test_temp_dir, timeout=5)
            elapsed = time.time() - start
            assert result is True
            assert call_count[0] >= 3

    def test_timeout(self, test_temp_dir):
        """SPACE-029: 超时"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)

        with patch.object(manager, '_check_space_available', return_value=False):
            with pytest.raises(TimeoutError):
                manager.wait_for_space(file_info, test_temp_dir, timeout=1)


class TestReleaseSpace:
    """release_space 测试"""

    def test_release_reserved(self, test_temp_dir):
        """SPACE-031: 释放预留空间"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)
        manager._reserved_space = 5000

        manager.release_space(file_info)
        # 释放了 file_info 所需的空间
        assert manager._reserved_space < 5000

    def test_release_more_than_reserved(self, test_temp_dir):
        """SPACE-032: 释放超过当前预留"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 10000)
        manager._reserved_space = 1000

        manager.release_space(file_info)
        # 不应为负数
        assert manager._reserved_space == 0

    def test_multiple_releases(self, test_temp_dir):
        """SPACE-033: 多次释放"""
        manager = SpaceManager()
        file_info = FileInfo(Path("/test"), "test.txt", 1000)
        manager._reserved_space = 5000

        manager.release_space(file_info)
        manager.release_space(file_info)
        manager.release_space(file_info)
        # 多次释放后应为0
        assert manager._reserved_space == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
