from sqlmodel import create_engine, SQLModel, Session
from neomodel import config
from typing import Generator
import os

sqlite_file_name = "polymath_server.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

NEO4J_URL = os.getenv("NEO4J_BOLT_URL", "bolt://neo4j:password@localhost:7687")

def init_dbs():
    config.DATABASE_URL = NEO4J_URL
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """
    Dependency that yields a SQLModel Session object.
    """
    with Session(engine) as session:
        yield session