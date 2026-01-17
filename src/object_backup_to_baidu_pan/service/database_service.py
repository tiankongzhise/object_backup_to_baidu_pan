"""数据库服务

提供数据库连接、会话管理和表创建功能。
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from ..config import DatabasePoolConfig, DatabaseCredentials
from ..models import Base


class DatabaseService:
    """数据库服务类"""

    def __init__(
        self,
        credentials: DatabaseCredentials | None = None,
        pool_config: DatabasePoolConfig | None = None
    ):
        """初始化数据库服务

        Args:
            credentials: 数据库连接凭证（从环境变量读取）
            pool_config: 连接池配置（从config.toml读取）
        """
        self.credentials = credentials or DatabaseCredentials()
        self.pool_config = pool_config or DatabasePoolConfig()
        self._engine = None
        self._session_factory = None

    def _create_engine(self):
        """创建数据库引擎"""
        if self._engine is None:
            self._engine = create_engine(
                self.credentials.url,
                echo=self.pool_config.echo,
                pool_size=self.pool_config.pool_size,
                max_overflow=self.pool_config.max_overflow,
                pool_timeout=self.pool_config.pool_timeout,
                pool_recycle=self.pool_config.pool_recycle,
                pool_pre_ping=self.pool_config.pool_pre_ping,
            )
        return self._engine

    def _create_session_factory(self):
        """创建会话工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self._create_engine(),
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    @property
    def engine(self):
        """获取数据库引擎"""
        return self._create_engine()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话上下文

        Yields:
            Session: SQLAlchemy会话对象
        """
        session_factory = self._create_session_factory()
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(self.engine)

    def check_connection(self) -> bool:
        """检查数据库连接

        Returns:
            bool: 连接是否正常
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
