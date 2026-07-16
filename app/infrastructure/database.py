import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_DIRECTORY = PROJECT_ROOT / "data" / "database"
DATABASE_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_FILE = DATABASE_DIRECTORY / "avm.db"

DEFAULT_DATABASE_URL = (
    f"sqlite:///{DATABASE_FILE.as_posix()}"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL,
)

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass
