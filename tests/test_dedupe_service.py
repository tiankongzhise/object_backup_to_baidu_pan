"""dedupe_service.py 测试用例"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.dedupe_service import DedupeService, DedupeResult
from object_backup_to_baidu_pan.service.classify_service import FileInfo, FolderInfo, ManualReviewItem
from object_backup_to_baidu_pan.config import HashConfig


class TestDedupeResult:
    """DedupeResult 测试"""

    def test_create_result(self):
        """DEDUPE-001: 创建结果"""
        result = DedupeResult(
            to_backup=[MagicMock()],
            already_backup=[MagicMock()],
            not_found_in_db=[MagicMock()]
        )
        assert len(result.to_backup) == 1
        assert len(result.already_backup) == 1
        assert len(result.not_found_in_db) == 1


class TestDedupeService:
    """DedupeService 测试"""

    def test_default_config(self):
        """DEDUPE-002: 默认配置"""
        service = DedupeService()
        assert isinstance(service.hash_config, HashConfig)
        assert service.hash_config.required_hash_algorithms == ['md5', 'sha1', 'sha256']

    def test_hostname_captured(self):
        """DEDUPE-003: 主机名获取"""
        service = DedupeService()
        assert service.hostname is not None


class TestCompareAndDedupe:
    """compare_and_dedupe 测试"""

    def test_all_new_files(self, test_temp_dir, mock_session):
        """DEDUPE-004: 全部是新文件"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        file2 = FileInfo(test_temp_dir / "file2.txt", "file2.txt", 200)
        items = [file1, file2]

        with patch.object(service, '_query_source_by_hashes', return_value=None):
            with patch.object(service, '_save_source_file'):
                with patch.object(service, '_record_duplicate'):
                    result = service.compare_and_dedupe(items, mock_session)

                    assert len(result.not_found_in_db) == 2
                    assert len(result.already_backup) == 0

    def test_all_duplicates(self, test_temp_dir, mock_session):
        """DEDUPE-005: 全部是重复文件"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        file2 = FileInfo(test_temp_dir / "file2.txt", "file2.txt", 200)
        items = [file1, file2]

        # Mock所有文件都找到重复
        with patch.object(service, '_query_source_by_hashes', return_value=MagicMock(is_backup=True)):
            with patch.object(service, '_record_duplicate'):
                result = service.compare_and_dedupe(items, mock_session)

                assert len(result.already_backup) == 2
                assert len(result.not_found_in_db) == 0

    def test_mixed_results(self, test_temp_dir, mock_session):
        """DEDUPE-006: 混合结果"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        file2 = FileInfo(test_temp_dir / "file2.txt", "file2.txt", 200)
        items = [file1, file2]

        query_results = [None, MagicMock(is_backup=True)]
        query_call = [0]

        def mock_query(session, hashes):
            result = query_results[query_call[0]]
            query_call[0] += 1
            return result

        with patch.object(service, '_query_source_by_hashes', mock_query):
            with patch.object(service, '_save_source_file'):
                with patch.object(service, '_record_duplicate'):
                    result = service.compare_and_dedupe(items, mock_session)

                    assert len(result.not_found_in_db) == 1
                    assert len(result.already_backup) == 1

    def test_skip_manual_review_items(self, test_temp_dir, mock_session):
        """DEDUPE-007: 跳过ManualReviewItem"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        manual = ManualReviewItem(test_temp_dir / "large", "size_exceeded")
        items = [file1, manual]

        with patch.object(service, '_query_source_by_hashes', return_value=None):
            with patch.object(service, '_save_source_file'):
                result = service.compare_and_dedupe(items, mock_session)

                assert len(result.not_found_in_db) == 1
                # manual不应在结果中

    def test_file_info_handling(self, test_temp_dir, mock_session):
        """DEDUPE-008: FileInfo处理"""
        service = DedupeService()
        service.hash_config = HashConfig(required_hash_algorithms=['md5'])

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        items = [file1]

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc'}):
            with patch.object(service, '_query_source_by_hashes', return_value=None):
                with patch.object(service, '_save_source_file'):
                    with patch.object(service, '_record_duplicate'):
                        result = service.compare_and_dedupe(items, mock_session)
                        assert len(result.not_found_in_db) == 1

    def test_folder_info_handling(self, test_temp_dir, mock_session):
        """DEDUPE-009: FolderInfo处理"""
        service = DedupeService()
        service.hash_config = HashConfig(required_hash_algorithms=['md5'])

        folder = FolderInfo(test_temp_dir / "folder", "folder", 10, 1000)
        items = [folder]

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_folder_hash', return_value={'md5': 'abc'}):
            with patch.object(service, '_query_source_by_hashes', return_value=None):
                with patch.object(service, '_save_source_file'):
                    with patch.object(service, '_record_duplicate'):
                        result = service.compare_and_dedupe(items, mock_session)
                        assert len(result.not_found_in_db) == 1

    def test_database_save(self, test_temp_dir, mock_session):
        """DEDUPE-010: 保存到数据库"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        items = [file1]

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}):
            with patch.object(service, '_query_source_by_hashes', return_value=None):
                with patch.object(service, '_save_source_file') as mock_save:
                    with patch.object(service, '_record_duplicate'):
                        service.compare_and_dedupe(items, mock_session)
                        mock_save.assert_called_once()

    def test_duplicate_record(self, test_temp_dir, mock_session):
        """DEDUPE-011: 记录重复"""
        service = DedupeService()

        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        file2 = FileInfo(test_temp_dir / "file2.txt", "file2.txt", 100)  # 同大小
        items = [file1, file2]

        query_results = [MagicMock(is_backup=True), MagicMock(is_backup=True)]
        query_call = [0]

        def mock_query(session, hashes):
            result = query_results[query_call[0]]
            query_call[0] += 1
            return result

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}):
            with patch.object(service, '_query_source_by_hashes', mock_query):
                with patch.object(service, '_save_source_file'):
                    with patch.object(service, '_record_duplicate') as mock_record:
                        service.compare_and_dedupe(items, mock_session)
                        assert mock_record.call_count == 2


class TestSaveSourceFile:
    """_save_source_file 测试"""

    def test_new_record(self, test_temp_dir, mock_session):
        """DEDUPE-014: 新记录"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        mock_session.query.return_value.filter.return_value.first.return_value = None

        service._save_source_file(mock_session, file1, hashes)

        mock_session.add.assert_called()

    def test_existing_record(self, test_temp_dir, mock_session):
        """DEDUPE-015: 存在记录"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        existing = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing

        service._save_source_file(mock_session, file1, hashes)

        # 不应调用add，因为是更新
        mock_session.add.assert_not_called()

    def test_file_info_size(self, test_temp_dir, mock_session):
        """DEDUPE-016: FileInfo使用file_size"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 1000)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        mock_session.query.return_value.filter.return_value.first.return_value = None

        service._save_source_file(mock_session, file1, hashes)

        # 验证file_size参数正确
        call_args = mock_session.add.call_args
        assert call_args[0][0].file_size == 1000

    def test_folder_info_size(self, test_temp_dir, mock_session):
        """DEDUPE-017: FolderInfo使用total_size"""
        service = DedupeService()
        folder = FolderInfo(test_temp_dir / "folder", "folder", 10, 5000)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        mock_session.query.return_value.filter.return_value.first.return_value = None

        service._save_source_file(mock_session, folder, hashes)

        call_args = mock_session.add.call_args
        assert call_args[0][0].file_size == 5000

    def test_is_backup_default(self, test_temp_dir, mock_session):
        """DEDUPE-018: is_backup默认值"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        mock_session.query.return_value.filter.return_value.first.return_value = None

        service._save_source_file(mock_session, file1, hashes)

        call_args = mock_session.add.call_args
        assert call_args[0][0].is_backup is False


class TestRecordDuplicate:
    """_record_duplicate 测试"""

    def test_new_duplicate_record(self, test_temp_dir, mock_session):
        """DEDUPE-019: 新重复记录"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}
        existing_source = None

        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = service._record_duplicate(mock_session, file1, hashes, existing_source)

        assert result is True
        mock_session.add.assert_called()

    def test_existing_duplicate_count(self, test_temp_dir, mock_session):
        """DEDUPE-020: 已存在重复计数"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        existing_dup = MagicMock()
        existing_dup.duplicate_count = 1
        mock_session.query.return_value.filter.return_value.first.side_effect = [None, existing_dup]

        result = service._record_duplicate(mock_session, file1, hashes, MagicMock())

        assert result is True
        assert existing_dup.duplicate_count == 2

    def test_same_path_skip(self, test_temp_dir, mock_session):
        """DEDUPE-021: 同路径跳过"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        existing_by_path = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_by_path

        result = service._record_duplicate(mock_session, file1, hashes, MagicMock())

        assert result is False
        mock_session.add.assert_not_called()


class TestQuerySourceByHashes:
    """_query_source_by_hashes 测试"""

    def test_find_backup(self, mock_session):
        """DEDUPE-024: 找到已备份"""
        service = DedupeService()
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        existing = MagicMock(is_backup=True)
        mock_session.query.return_value.filter.return_value.first.return_value = existing

        result = service._query_source_by_hashes(mock_session, hashes)

        assert result is existing

    def test_not_backup(self, mock_session):
        """DEDUPE-025: 找到未备份"""
        service = DedupeService()
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        existing = MagicMock(is_backup=False)
        mock_session.query.return_value.filter.return_value.first.return_value = existing

        result = service._query_source_by_hashes(mock_session, hashes)

        assert result is None

    def test_not_found(self, mock_session):
        """DEDUPE-026: 未找到"""
        service = DedupeService()
        hashes = {'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}

        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = service._query_source_by_hashes(mock_session, hashes)

        assert result is None


class TestSaveSourceFiles:
    """save_source_files 测试"""

    def test_save_multiple(self, test_temp_dir, mock_session):
        """DEDUPE-031: 保存多个文件"""
        service = DedupeService()
        files = [
            FileInfo(test_temp_dir / f"file{i}.txt", f"file{i}.txt", 100)
            for i in range(3)
        ]

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}):
            service.save_source_files(files, mock_session)

            assert mock_session.add.call_count == 3


class TestMarkAsBackup:
    """mark_as_backup 测试"""

    def test_mark_success(self, test_temp_dir, mock_session):
        """DEDUPE-033: 标记成功"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)

        existing = MagicMock(is_backup=False)
        mock_session.query.return_value.filter.return_value.first.return_value = existing

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}):
            service.mark_as_backup(file1, mock_session)

            assert existing.is_backup is True
            assert existing.backup_time is not None

    def test_not_found(self, test_temp_dir, mock_session):
        """DEDUPE-035: 记录不存在"""
        service = DedupeService()
        file1 = FileInfo(test_temp_dir / "file1.txt", "file1.txt", 100)

        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch('object_backup_to_baidu_pan.service.dedupe_service.CalculateHashService.calculate_file_hash', return_value={'md5': 'abc', 'sha1': 'def', 'sha256': 'ghi'}):
            service.mark_as_backup(file1, mock_session)
            # 不应报错


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
