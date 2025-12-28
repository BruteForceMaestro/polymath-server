from sqlmodel import create_engine, SQLModel, Session
from neomodel import config
from typing import Generator
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
# Use an environment variable if set (for Docker), otherwise use local project folder
DB_DIR = Path(os.getenv("DATABASE_DIR", BASE_DIR / "data"))
DB_DIR.mkdir(parents=True, exist_ok=True)

sqlite_file_path = DB_DIR / "polymath_server.db"
sqlite_url = f"sqlite:///{sqlite_file_path}"
connect_args = {"check_same_thread": False}

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


NEO4J_URL = os.getenv("NEO4J_URL")

def init_dbs():

    user = os.getenv("NEO4J_USER")  
    password = os.getenv("NEO4J_PASSWORD") 
    connection_string = f"bolt://{user}:{password}@{NEO4J_URL}"

    print(connection_string)

    config.DATABASE_URL = connection_string # type: ignore
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """
    Dependency that yields a SQLModel Session object.
    """
    with Session(engine) as session:
        yield session