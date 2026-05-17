from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

class Base(DeclarativeBase):
    pass

# Database URL - SQLite local file
DB_PATH = os.environ.get("MAJ_GOLD_DB", "maj_gold.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + PyQt6
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency: yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables if they don't exist."""
    from . import (
        masters, daybook, stock, gold_box,
        process, stock_register, ledger, v_account
    )
    Base.metadata.create_all(bind=engine)
