from sqlmodel import create_engine, SQLModel, Session
from neomodel import config
from typing import Generator
from pathlib import Path
import os

# Since WORKDIR is /app, this is relative to your running process
DB_DIR = Path("/app/data") 
DB_DIR.mkdir(parents=True, exist_ok=True)

sqlite_file_path = DB_DIR / "polymath_server.db"
sqlite_url = f"sqlite:///{sqlite_file_path}"
connect_args = {"check_same_thread": False}

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

NEO4J_URL = os.getenv("NEO4J_BOLT_URL", "bolt://neo4j:password@localhost:7687")

def init_dbs():
    config.DATABASE_URL = NEO4J_URL # type: ignore
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """
    Dependency that yields a SQLModel Session object.
    """
    with Session(engine) as session:
        yield session