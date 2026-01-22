"""verify_service.py 测试用例"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.verify_service import VerifyService, VerifyResult
from object_backup_to_baidu_pan.service.classify_service import FileInfo, FolderInfo
from object_backup_to_baidu_pan.config import HashConfig, ZipConfig, StorageConfig


class TestVerifyResult:
    """VerifyResult 测试"""

    def test_bool_true(self):
        """VERIFY-001: 验证成功时__bool__返回True"""
        result = VerifyResult(is_valid=True)
        assert bool(result) is True

    def test_bool_false(self):
        """VERIFY-002: 验证失败时__bool__返回False"""
        result = VerifyResult(is_valid=False)
        assert bool(result) is False

    def test_full_result(self):
        """VERIFY-003: 完整结果"""
        result = VerifyResult(
            is_valid=True,
            extracted_path=Path("/test"),
            extracted_hashes={'md5': 'abc'},
            source_hashes={'md5': 'abc'},
        )
        assert result.is_valid is True
        assert result.extracted_path == Path("/test")


class TestVerifyService:
    """VerifyService 测试"""

    def test_default_config(self):
        """VERIFY-004: 默认配置"""
        service = VerifyService()
        assert isinstance(service.hash_config, HashConfig)
        assert isinstance(service.zip_config, ZipConfig)
        assert isinstance(service.storage_config, StorageConfig)

    def test_custom_config(self):
        """VERIFY-005: 自定义配置"""
        hash_config = HashConfig(required_hash_algorithms=['md5'])
        service = VerifyService(hash_config=hash_config)
        assert service.hash_config.required_hash_algorithms == ['md5']


class TestVerifyPackage:
    """verify_package 测试"""

    def test_verify_success_file(self, test_temp_dir):
        """VERIFY-006: 验证成功-文件"""
        # 创建源文件
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test content")

        # 压缩
        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 创建FileInfo
        file_info = FileInfo(source, "source.txt", 12)

        # 验证
        service = VerifyService()
        result = service.verify_package(zip_path, file_info, password="test")

        assert result.is_valid is True

    def test_verify_success_folder(self, test_temp_dir):
        """VERIFY-007: 验证成功-文件夹"""
        # 创建源文件夹
        source = test_temp_dir / "source"
        source.mkdir()
        (source / "file1.txt").write_bytes(b"content1")
        (source / "file2.txt").write_bytes(b"content2")

        # 压缩
        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 创建FolderInfo
        folder_info = FolderInfo(source, "source", 2, 16)

        # 验证
        service = VerifyService()
        result = service.verify_package(zip_path, folder_info, password="test")

        assert result.is_valid is True

    def test_verify_failure_corrupt(self, test_temp_dir):
        """VERIFY-008: 验证失败-ZIP损坏"""
        # 创建文件
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"original content")

        # 压缩
        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 损坏ZIP
        content = zip_path.read_bytes()
        corrupted = bytearray(content)
        corrupted[100] = corrupted[100] ^ 0xFF
        zip_path.write_bytes(bytes(corrupted))

        file_info = FileInfo(source, "source.txt", 15)

        service = VerifyService()
        result = service.verify_package(zip_path, file_info, password="test")

        assert result.is_valid is False

    def test_verify_failure_wrong_password(self, test_temp_dir):
        """VERIFY-009: 验证失败-密码错误"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"secret")

        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="correct")

        file_info = FileInfo(source, "source.txt", 6)

        service = VerifyService()
        result = service.verify_package(zip_path, file_info, password="wrong")

        assert result.is_valid is False

    def test_verify_failure_hash_mismatch(self, test_temp_dir):
        """VERIFY-010: 验证失败-Hash不匹配"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"original content")

        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 修改源文件（不重新压缩）
        source.write_bytes(b"modified content")

        file_info = FileInfo(source, "source.txt", 15)

        service = VerifyService()
        result = service.verify_package(zip_path, file_info, password="test")

        assert result.is_valid is False

    def test_provide_source_hashes(self, test_temp_dir):
        """VERIFY-011: 传入已计算的source_hashes"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test content")

        from object_backup_to_baidu_pan.service.zip_service import ZipService
        from object_backup_to_baidu_pan.service.hash_service import CalculateHashService

        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 预先计算hash
        source_hashes = CalculateHashService.calculate_file_hash(source)

        file_info = FileInfo(source, "source.txt", 12)

        service = VerifyService()
        result = service.verify_package(
            zip_path, file_info, password="test",
            source_hashes=source_hashes
        )

        assert result.is_valid is True

    def test_cleanup_extracted_success(self, test_temp_dir):
        """VERIFY-013: 验证成功后清理解压目录"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test")

        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir)

        file_info = FileInfo(source, "source.txt", 4)

        service = VerifyService()
        result = service.verify_package(zip_path, file_info)

        # 验证解压目录已被清理
        if result.extracted_path:
            assert not result.extracted_path.exists()

    def test_cleanup_extracted_failure(self, test_temp_dir):
        """VERIFY-014: 验证失败后清理解压目录"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test")

        from object_backup_to_baidu_pan.service.zip_service import ZipService
        zip_path = ZipService.zip_item(source, test_temp_dir, password="test")

        # 损坏ZIP
        corrupted = bytearray(zip_path.read_bytes())
        corrupted[50] ^= 0xFF
        zip_path.write_bytes(bytes(corrupted))

        file_info = FileInfo(source, "source.txt", 4)

        service = VerifyService()
        result = service.verify_package(zip_path, file_info, password="test")

        # 即使验证失败也应该清理
        if result.extracted_path:
            assert not result.extracted_path.exists()


class TestCompareHashes:
    """_compare_hashes 测试"""

    def test_match_all(self):
        """VERIFY-018: 完全匹配"""
        service = VerifyService()
        extracted = {'md5': 'ABC', 'sha1': 'DEF', 'sha256': 'GHI'}
        source = {'md5': 'ABC', 'sha1': 'DEF', 'sha256': 'GHI'}
        assert service._compare_hashes(extracted, source) is True

    def test_partial_match(self):
        """VERIFY-019: 部分匹配（一个不匹配）"""
        service = VerifyService()
        extracted = {'md5': 'ABC', 'sha1': 'DEF', 'sha256': 'GHI'}
        source = {'md5': 'ABC', 'sha1': 'DIFFERENT', 'sha256': 'GHI'}
        assert service._compare_hashes(extracted, source) is False

    def test_missing_algorithm(self):
        """VERIFY-020: 缺失算法"""
        service = VerifyService()
        extracted = {'md5': 'ABC'}
        source = {'md5': 'ABC', 'sha1': 'DEF'}
        assert service._compare_hashes(extracted, source) is False


class TestCleanupExtracted:
    """cleanup_extracted 测试"""

    def test_cleanup_directory(self, test_temp_dir):
        """VERIFY-022: 清理目录"""
        extracted_dir = test_temp_dir / "extracted"
        extracted_dir.mkdir()
        (extracted_dir / "file.txt").write_bytes(b"test")

        service = VerifyService()
        service.cleanup_extracted(extracted_dir)

        assert not extracted_dir.exists()

    def test_cleanup_file(self, test_temp_dir):
        """VERIFY-023: 清理文件"""
        extracted_file = test_temp_dir / "extracted.txt"
        extracted_file.write_bytes(b"test")

        service = VerifyService()
        service.cleanup_extracted(extracted_file)

        assert not extracted_file.exists()

    def test_cleanup_not_exists(self, test_temp_dir):
        """VERIFY-024: 清理不存在的路径"""
        not_exists = test_temp_dir / "not_exists"

        service = VerifyService()
        # 不应抛出异常
        service.cleanup_extracted(not_exists)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
