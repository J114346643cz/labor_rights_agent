from sqlmodel import Session as DBsession
from sqlmodel import SQLModel,create_engine


from app.utils.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread":False}, #关闭这个线程安全检查，允许不同线程共用数据库连接。
)

def init_db()->None:
    SQLModel.metadata.create_all(engine)

def get_db():
    with DBsession(engine) as session:
        yield session