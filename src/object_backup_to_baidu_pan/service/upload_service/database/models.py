from sqlalchemy.orm import mapped_column, Mapped,DeclarativeBase
from sqlalchemy import BigInteger, String, Integer,MetaData
from datetime import datetime
from time import time_ns

class OauthBase(DeclarativeBase):
    metadata = MetaData()
    pass

class BaiduPanOauth(OauthBase):
    __tablename__ = 'baidu_pan_oauth'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(100))
    client_secret: Mapped[str] = mapped_column(String(100))
    access_token: Mapped[str] = mapped_column(String(100))   
    refresh_token: Mapped[str] = mapped_column(String(100))   
    expires_in: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(BigInteger)  
    created_at: Mapped[int] = mapped_column(BigInteger, default=time_ns)
    updated_at: Mapped[int] = mapped_column(BigInteger, onupdate=time_ns, nullable=True)



    @property
    def is_expired_in_day(self):
        return time_ns() / 1_000_000_000.0 > (self.expires_at - 24 * 60 * 60)
    @property
    def expires_at_local_time(self):
        return datetime.fromtimestamp(self.expires_at)
    @property
    def created_at_local_time(self):
        return datetime.fromtimestamp(self.created_at / 1_000_000_000.0)
    @property
    def updated_at_local_time(self):
        if self.updated_at is None:
            return None
        return datetime.fromtimestamp(self.updated_at / 1_000_000_000.0)

    def __repr__(self):
        return f"<BaiduPanOauth(access_token='{self.access_token}', refresh_token='{self.refresh_token}', expires_in='{self.expires_in}', expires_at_local_time = '{self.expires_at_local_time}', created_at_local_time = '{self.created_at_local_time}', updated_at_local_time = '{self.updated_at_local_time}', expires_at='{self.expires_at}', created_at='{self.created_at}', updated_at='{self.updated_at}')>"
