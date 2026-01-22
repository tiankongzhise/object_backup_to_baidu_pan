"""database_service.py 测试用例"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy import create_engine, text

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.database_service import DatabaseService
from object_backup_to_baidu_pan.config import DatabasePoolConfig, DatabaseCredentials


class TestDatabaseService:
    """DatabaseService 测试"""

    def test_default_credentials(self, patch_env_variables):
        """DB-001: 默认凭证"""
        service = DatabaseService()
        assert service.credentials.host == 'localhost'
        assert service.credentials.port == 3306

    def test_custom_credentials(self):
        """DB-002: 自定义凭证"""
        creds = DatabaseCredentials()
        creds.host = 'custom-host'
        creds.port = 3307

        service = DatabaseService(credentials=creds)
        assert service.credentials.host == 'custom-host'

    def test_default_pool_config(self):
        """DB-003: 默认池配置"""
        service = DatabaseService()
        assert service.pool_config.pool_size == 5
        assert service.pool_config.max_overflow == 10


class TestCreateEngine:
    """_create_engine 测试"""

    def test_create_engine(self):
        """DB-004: 创建引擎"""
        service = DatabaseService()
        engine = service._create_engine()
        assert engine is not None

    def test_reuse_engine(self):
        """DB-005: 重复创建返回同一引擎"""
        service = DatabaseService()
        engine1 = service._create_engine()
        engine2 = service._create_engine()
        assert engine1 is engine2


class TestCreateSessionFactory:
    """_create_session_factory 测试"""

    def test_create_factory(self):
        """DB-007: 创建会话工厂"""
        service = DatabaseService()
        factory = service._create_session_factory()
        assert factory is not None

    def test_reuse_factory(self):
        """DB-008: 重复创建返回同一工厂"""
        service = DatabaseService()
        factory1 = service._create_session_factory()
        factory2 = service._create_session_factory()
        assert factory1 is factory2


class TestGetSession:
    """get_session 测试"""

    def test_get_session(self):
        """DB-009: 获取会话"""
        service = DatabaseService()
        with service.get_session() as session:
            assert session is not None

    def test_commit_on_success(self):
        """DB-010: 成功时提交"""
        service = DatabaseService()
        with patch.object(service, '_create_session_factory') as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = MagicMock(return_value=mock_session)

            with service.get_session() as session:
                pass

            mock_session.commit.assert_called_once()

    def test_rollback_on_exception(self):
        """DB-011: 异常时回滚"""
        service = DatabaseService()
        with patch.object(service, '_create_session_factory') as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = MagicMock(return_value=mock_session)

            with pytest.raises(ValueError):
                with service.get_session() as session:
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()

    def test_close_session(self):
        """DB-012: 关闭会话"""
        service = DatabaseService()
        with patch.object(service, '_create_session_factory') as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = MagicMock(return_value=mock_session)

            with service.get_session() as session:
                pass

            mock_session.close.assert_called_once()


class TestCreateTables:
    """create_tables 测试"""

    def test_create_all_tables(self, test_temp_dir):
        """DB-013: 创建所有表"""
        # 使用SQLite进行测试
        service = DatabaseService()
        service._engine = create_engine('sqlite:///:memory:')

        # Mock Base.metadata.create_all
        with patch('object_backup_to_baidu_pan.service.database_service.Base.metadata.create_all') as mock_create:
            mock_create.return_value = None
            service.create_tables()
            mock_create.assert_called_once()


class TestDropTables:
    """drop_tables 测试"""

    def test_drop_all_tables(self):
        """DB-015: 删除所有表"""
        service = DatabaseService()
        service._engine = create_engine('sqlite:///:memory:')

        with patch('object_backup_to_baidu_pan.service.database_service.Base.metadata.drop_all') as mock_drop:
            mock_drop.return_value = None
            service.drop_tables()
            mock_drop.assert_called_once()


class TestCheckConnection:
    """check_connection 测试"""

    def test_connection_success(self):
        """DB-017: 连接成功"""
        service = DatabaseService()
        # 使用内存SQLite测试
        service._engine = create_engine('sqlite:///:memory:')

        result = service.check_connection()
        assert result is True

    def test_connection_failure(self):
        """DB-018: 连接失败"""
        service = DatabaseService()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(
            side_effect=Exception("Connection failed")
        )
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        service._engine = mock_engine

        result = service.check_connection()
        assert result is False

    def test_exception_handling(self):
        """DB-019: 异常处理"""
        service = DatabaseService()
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Test error")
        service._engine = mock_engine

        result = service.check_connection()
        assert result is False


class TestClose:
    """close 测试"""

    def test_close_connection(self):
        """DB-020: 关闭连接"""
        service = DatabaseService()
        service._engine = MagicMock()
        service._session_factory = MagicMock()

        service.close()

        service._engine.dispose.assert_called_once()
        assert service._engine is None
        assert service._session_factory is None

    def test_close_multiple_times(self):
        """DB-021: 多次关闭"""
        service = DatabaseService()
        service._engine = MagicMock()
        service._session_factory = MagicMock()

        service.close()
        service.close()  # 不应报错

    def test_close_and_recreate(self):
        """DB-022: 关闭后重新创建"""
        service = DatabaseService()
        engine1 = service._create_engine()

        service.close()

        engine2 = service._create_engine()
        assert engine1 is not engine2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
