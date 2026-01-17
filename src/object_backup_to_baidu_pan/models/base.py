"""SQLAlchemy基类

定义所有数据库模型的基类。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有SQLAlchemy模型的基类"""
    pass
