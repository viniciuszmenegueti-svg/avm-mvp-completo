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
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass
