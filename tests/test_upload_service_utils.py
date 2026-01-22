"""upload_service/utils.py 测试用例"""

import pytest
import sys
from pathlib import Path
import re

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.upload_service.utils import (
    extract_date_and_password_from_path,
    extract_date_and_password_from_path_strict
)


class TestExtractDateAndPasswordFromPath:
    """extract_date_and_password_from_path 测试"""

    def test_standard_path(self):
        """UTL-001: 标准路径提取"""
        path = r"D:\压缩测试\20260115\解压密码_H_x123456789"
        date, password = extract_date_and_password_from_path(path)
        assert date == '20260115'
        assert password == 'H_x123456789'

    def test_no_password(self):
        """UTL-002: 无密码路径"""
        path = r"D:\压缩测试\20260115\folder"
        date, password = extract_date_and_password_from_path(path)
        assert date == '20260115'
        assert password is None

    def test_no_date(self):
        """UTL-003: 无日期路径"""
        path = r"D:\压缩测试\folder\解压密码_test"
        date, password = extract_date_and_password_from_path(path)
        assert date is None
        assert password == 'test'

    def test_multiple_dates_first(self):
        """UTL-004: 多个日期取第一个"""
        path = r"D:\20250101\20250202"
        date, password = extract_date_and_password_from_path(path)
        # 取第一个有效的8位数字
        assert date == '20250101'

    def test_valid_date_format(self):
        """UTL-005: 日期格式验证-有效"""
        path = r"D:\20260115\test"
        date, password = extract_date_and_password_from_path(path)
        assert date == '20260115'

    def test_invalid_date_format(self):
        """UTL-006: 日期格式验证-无效"""
        path = r"D:\20261345\test"  # 13月45日，无效日期
        date, password = extract_date_and_password_from_path(path)
        assert date is None

    def test_password_extract_jiekou(self):
        """UTL-007: 密码提取-解压密码_"""
        path = r"D:\test\解压密码_abc"
        date, password = extract_date_and_password_from_path(path)
        assert password == 'abc'

    def test_password_extract_mima(self):
        """UTL-008: 密码提取-密码-"""
        path = r"D:\test\密码-xyz"
        date, password = extract_date_and_password_from_path(path)
        assert password == 'xyz'

    def test_password_alphanumeric(self):
        """UTL-009: 密码含数字字母"""
        path = r"D:\test\解压密码_123abc"
        date, password = extract_date_and_password_from_path(path)
        assert password == '123abc'

    def test_strict_mode_same_as_standard(self):
        """UTL-010: 严格模式与标准模式一致"""
        path = r"D:\压缩测试\20260115\解压密码_test"
        date1, password1 = extract_date_and_password_from_path(path)
        date2, password2 = extract_date_and_password_from_path_strict(path)
        assert date1 == date2
        assert password1 == password2

    def test_windows_path(self):
        """UTL-011: Windows路径"""
        path = r"D:\folder\20260115\解压密码_test"
        date, password = extract_date_and_password_from_path(path)
        assert date == '20260115'
        assert password == 'test'

    def test_linux_path(self):
        """UTL-012: Linux路径"""
        path = "/home/user/20260115/解压密码_test"
        date, password = extract_date_and_password_from_path(path)
        assert date == '20260115'
        assert password == 'test'

    def test_empty_string(self):
        """UTL-013: 空字符串"""
        date, password = extract_date_and_password_from_path("")
        assert date is None
        assert password is None


class TestExtractDateAndPasswordFromPathStrict:
    """extract_date_and_password_from_path_strict 测试"""

    def test_strict_date_extraction(self):
        """严格日期提取"""
        path = r"D:\20260115\folder"
        date, password = extract_date_and_password_from_path_strict(path)
        assert date == '20260115'

    def test_strict_password_extraction(self):
        """严格密码提取"""
        path = r"D:\folder\解压密码_test"
        date, password = extract_date_and_password_from_path_strict(path)
        assert password == 'test'

    def test_strict_combined(self):
        """严格模式组合"""
        path = r"D:\20260115\解压密码_abc123"
        date, password = extract_date_and_password_from_path_strict(path)
        assert date == '20260115'
        assert password == 'abc123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
