from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine, text
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


def _get_columns(conn, table):
    """Return a list of column names for the given table."""
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    return [row[1] for row in result]


def migrate_melt_batches(eng):
    """
    Migrate old column names to new ones WITHOUT using RENAME COLUMN
    (RENAME COLUMN is only safe in SQLite >= 3.25 and can fail silently).

    Strategy: ADD new column → copy data from old column → leave old
    column in place (SQLite cannot DROP columns in older versions either).
    SQLAlchemy model no longer references old columns, so they are
    harmlessly ignored.

    Safe to run on every launch — all operations check existence first.
    """
    with eng.connect() as conn:
        columns = _get_columns(conn, "melt_batches")

        # silver_g → metal_a_g
        if "silver_g" in columns:
            if "metal_a_g" not in columns:
                conn.execute(text(
                    "ALTER TABLE melt_batches ADD COLUMN metal_a_g REAL DEFAULT 0.0"
                ))
            conn.execute(text(
                "UPDATE melt_batches SET metal_a_g = silver_g "
                "WHERE silver_g IS NOT NULL AND "
                "(metal_a_g IS NULL OR metal_a_g = 0.0)"
            ))

        # copper_g → metal_b_g
        if "copper_g" in columns:
            if "metal_b_g" not in columns:
                conn.execute(text(
                    "ALTER TABLE melt_batches ADD COLUMN metal_b_g REAL DEFAULT 0.0"
                ))
            conn.execute(text(
                "UPDATE melt_batches SET metal_b_g = copper_g "
                "WHERE copper_g IS NOT NULL AND "
                "(metal_b_g IS NULL OR metal_b_g = 0.0)"
            ))

        conn.commit()


def migrate_add_missing_columns(eng):
    """
    Add any columns that may be missing from older versions of the
    melt_batches table. Safe to run on every launch.
    """
    required = {
        "subtype":          "TEXT NOT NULL DEFAULT 'ornaments'",
        "lot_id":           "INTEGER",
        "purity_value":     "REAL",
        "metal_a_g":        "REAL DEFAULT 0.0",
        "metal_b_g":        "REAL DEFAULT 0.0",
        "extra_alloy_g":    "REAL DEFAULT 0.0",
        "total_alloy_g":    "REAL DEFAULT 0.0",
        "gross_weight_g":   "REAL",
        "final_916_g":      "REAL DEFAULT 0.0",
        "weight_out_916_g": "REAL",
        "ng_weight_g":      "REAL DEFAULT 0.0",
        "kambi_weight_g":   "REAL DEFAULT 0.0",
        "loss_g":           "REAL DEFAULT 0.0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "melt_batches")
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE melt_batches ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def init_db():
    """Create all tables if they don't exist, then run migrations."""
    from . import (
        masters, daybook, stock, gold_box,
        process, stock_register, ledger, v_account
    )
    Base.metadata.create_all(bind=engine)
    # Run in order: rename-style migration first, then add missing columns
    migrate_melt_batches(engine)
    migrate_add_missing_columns(engine)
