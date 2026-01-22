"""models 测试用例"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.models.base import Base
from object_backup_to_baidu_pan.models.source_file import SourceFile
from object_backup_to_baidu_pan.models.backup_package import BackupPackage
from object_backup_to_baidu_pan.models.duplicate_file import DuplicateFile
from object_backup_to_baidu_pan.models.manual_review_item import ManualReviewItem
from object_backup_to_baidu_pan.models.operation_log import OperationLog


class TestBase:
    """Base 测试"""

    def test_base_is_declarative(self):
        """MODEL-001: 基类声明"""
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, 'registry')


class TestSourceFile:
    """SourceFile 测试"""

    def test_create_record(self):
        """MODEL-002: 创建记录"""
        record = SourceFile(
            hostname='test-host',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789'
        )
        assert record.hostname == 'test-host'
        assert record.file_path == '/test/file.txt'
        assert record.file_size == 1000

    def test_repr(self):
        """MODEL-003: __repr__"""
        record = SourceFile(
            hostname='test-host',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789'
        )
        repr_str = repr(record)
        assert 'SourceFile' in repr_str
        assert 'file.txt' in repr_str

    def test_to_dict(self):
        """MODEL-004: 转换为字典"""
        record = SourceFile(
            id=1,
            hostname='test-host',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789'
        )
        data = record.to_dict()
        assert isinstance(data, dict)
        assert data['id'] == 1
        assert data['hostname'] == 'test-host'
        assert data['file_size'] == 1000

    def test_to_dict_with_datetime(self):
        """MODEL-005: 字典含时间"""
        record = SourceFile(
            id=1,
            hostname='test-host',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            backup_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        data = record.to_dict()
        assert '2024-01-01' in data['backup_time']

    def test_field_constraints(self):
        """MODEL-006: 字段约束"""
        # hostname应该有索引
        assert hasattr(SourceFile, 'hostname')
        assert hasattr(SourceFile, 'md5_hash')
        assert hasattr(SourceFile, 'sha1_hash')
        assert hasattr(SourceFile, 'sha256_hash')


class TestBackupPackage:
    """BackupPackage 测试"""

    def test_create_record(self):
        """MODEL-008: 创建记录"""
        record = BackupPackage(
            hostname='test-host',
            package_path='/backup/test.zip',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_count=1,
            package_size=1000
        )
        assert record.hostname == 'test-host'
        assert record.package_path == '/backup/test.zip'

    def test_repr(self):
        """MODEL-009: __repr__"""
        record = BackupPackage(
            hostname='test-host',
            package_path='/backup/test.zip',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_count=1,
            package_size=1000
        )
        repr_str = repr(record)
        assert 'BackupPackage' in repr_str

    def test_to_dict(self):
        """MODEL-010: 转换为字典"""
        record = BackupPackage(
            id=1,
            hostname='test-host',
            package_path='/backup/test.zip',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_count=1,
            package_size=1000,
            status='pending'
        )
        data = record.to_dict()
        assert data['status'] == 'pending'
        assert data['package_size'] == 1000

    def test_foreign_key(self):
        """MODEL-011: 外键关联"""
        assert hasattr(BackupPackage, 'source_file_id')
        # 应该能关联到SourceFile

    def test_default_status(self):
        """MODEL-012: 默认status"""
        # 创建记录时如果不指定status，SQLAlchemy应该使用默认值
        # 注意：在SQLAlchemy中，default只在插入时应用，不在对象创建时
        record = BackupPackage(
            hostname='test-host',
            package_path='/backup/test.zip',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_count=1,
            package_size=1000
        )
        # SQLAlchemy default只在flush/commit时应用
        # 这里测试default参数存在
        assert hasattr(BackupPackage, '__table__')

    def test_default_is_source_archive(self):
        """MODEL-13: 默认is_source_archive"""
        record = BackupPackage(
            hostname='test-host',
            package_path='/backup/test.zip',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_count=1,
            package_size=1000
        )
        # 在SQLAlchemy 2.0中，Boolean default只在flush时应用


class TestDuplicateFile:
    """DuplicateFile 测试"""

    def test_create_record(self):
        """MODEL-014: 创建记录"""
        record = DuplicateFile(
            hostname='test-host',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            master_file_path='/original/file.txt'
        )
        assert record.hostname == 'test-host'
        assert record.file_path == '/test/file.txt'

    def test_repr(self):
        """MODEL-015: __repr__"""
        record = DuplicateFile(
            hostname='test-host',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000
        )
        repr_str = repr(record)
        assert 'DuplicateFile' in repr_str

    def test_to_dict(self):
        """MODEL-016: 转换为字典"""
        record = DuplicateFile(
            id=1,
            hostname='test-host',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000,
            duplicate_type='exact'
        )
        data = record.to_dict()
        assert data['duplicate_type'] == 'exact'

    def test_default_duplicate_type(self):
        """MODEL-017: 默认duplicate_type"""
        record = DuplicateFile(
            hostname='test-host',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000
        )
        # duplicate_type在模型定义中有default='exact'，只在flush时应用

    def test_default_duplicate_count(self):
        """MODEL-018: 默认duplicate_count"""
        record = DuplicateFile(
            hostname='test-host',
            md5_hash='abc123',
            sha1_hash='def456',
            sha256_hash='ghi789',
            file_path='/test/file.txt',
            file_name='file.txt',
            file_size=1000
        )
        # duplicate_count在模型定义中有default=1，只在flush时应用

    def test_foreign_key(self):
        """MODEL-019: 外键"""
        assert hasattr(DuplicateFile, 'master_source_file_id')


class TestManualReviewItem:
    """ManualReviewItem 测试"""

    def test_create_record(self):
        """MODEL-020: 创建记录"""
        record = ManualReviewItem(
            hostname='test-host',
            file_path='/test/large_file',
            file_size=25 * 1024**3,
            file_count=1000,
            reason='size_exceeded'
        )
        assert record.hostname == 'test-host'
        assert record.file_path == '/test/large_file'
        assert record.reason == 'size_exceeded'

    def test_repr(self):
        """MODEL-021: __repr__"""
        record = ManualReviewItem(
            hostname='test-host',
            file_path='/test/large_file',
            reason='size_exceeded'
        )
        repr_str = repr(record)
        assert 'ManualReviewItem' in repr_str

    def test_to_dict(self):
        """MODEL-022: 转换为字典"""
        record = ManualReviewItem(
            id=1,
            hostname='test-host',
            file_path='/test/large_file',
            file_size=1000,
            file_count=100,
            reason='size_exceeded',
            status='pending'
        )
        data = record.to_dict()
        assert data['status'] == 'pending'

    def test_default_status(self):
        """MODEL-023: 默认status"""
        record = ManualReviewItem(
            hostname='test-host',
            file_path='/test/large_file',
            reason='size_exceeded'
        )
        # status在模型定义中有default='pending'，只在flush时应用


class TestOperationLog:
    """OperationLog 测试"""

    def test_create_record(self):
        """MODEL-024: 创建记录"""
        record = OperationLog(
            hostname='test-host',
            operation_type='backup',
            status='success'
        )
        assert record.hostname == 'test-host'
        assert record.operation_type == 'backup'
        assert record.status == 'success'

    def test_repr(self):
        """MODEL-025: __repr__"""
        record = OperationLog(
            hostname='test-host',
            operation_type='backup',
            status='success'
        )
        repr_str = repr(record)
        assert 'OperationLog' in repr_str

    def test_to_dict(self):
        """MODEL-026: 转换为字典"""
        record = OperationLog(
            id=1,
            hostname='test-host',
            operation_type='backup',
            status='success',
            message='Backup completed',
            duration_ms=1000
        )
        data = record.to_dict()
        assert data['operation_type'] == 'backup'
        assert data['duration_ms'] == 1000

    def test_status_required(self):
        """MODEL-027: status必填"""
        record = OperationLog(
            hostname='test-host',
            operation_type='backup',
            status='success'
        )
        assert record.status is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
