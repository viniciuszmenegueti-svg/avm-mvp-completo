import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    dotenv_path=PROJECT_ROOT / ".env",
    override=False,
)

DATABASE_DIRECTORY = PROJECT_ROOT / "data" / "database"
DATABASE_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_FILE = DATABASE_DIRECTORY / "avm.db"

DEFAULT_DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL,
)

connect_args: dict = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
    }

elif DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://")):
    connect_args = {
        "connect_timeout": 3,
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass
