from sqlalchemy import create_engine,select
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from time import time_ns



class OauthDbClient(object):
    def __init__(self):
        self.engine = self._create_engine()

    def _create_engine(self):
        load_dotenv()
        return create_engine(self._create_engine_url())

    def _create_engine_url(self):
        import os
        load_dotenv()
        mysql_host = os.getenv('MYSQL_HOST')
        mysql_port = os.getenv('MYSQL_PORT')
        mysql_user = os.getenv('MYSQL_USER')
        mysql_password = os.getenv('MYSQL_PASSWORD')
        mysql_db = os.getenv('MYSQL_DATABASE')
        return f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"

    def create_table(self):
        from .models import OauthBase
        OauthBase.metadata.create_all(self.engine)

    def drop_table(self):
        from .models import OauthBase
        OauthBase.metadata.drop_all(self.engine)

    def reset_table(self):
        self.drop_table()
        self.create_table()

    def add_token(self, data):
        from .models import BaiduPanOauth
        add_info = {
            **data,
            'expires_at': time_ns() / 1_000_000_000.0 + data['expires_in'],
        }
        with Session(self.engine) as session:
            session.add(BaiduPanOauth(**add_info))
            session.commit()
    def get_token(self):
        from .models import BaiduPanOauth
        with Session(self.engine) as session:
            return session.execute(select(BaiduPanOauth).order_by(BaiduPanOauth.id.desc()).limit(1)).scalar_one_or_none()
