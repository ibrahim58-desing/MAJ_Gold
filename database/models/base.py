from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, create_engine, text
from sqlalchemy.orm import sessionmaker
import os

class Base(DeclarativeBase):
    pass

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(50), primary_key=True)
    value = Column(String(255))

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

def migrate_wire_sheet_batches(eng):
    """
    Add new columns needed by the redesigned WireSheetBatch model.
    Old columns (weight_in_g, weight_out_g, chains_count, solder_weight_g,
    product_type_id) are left in place — SQLite cannot DROP columns in older
    versions and SQLAlchemy simply ignores them.
    Safe to run on every launch.
    """
    required = {
        "batch_type":      "TEXT DEFAULT 'wire'",
        "rod_weight_g":    "REAL DEFAULT 0.0",
        "output_weight_g": "REAL DEFAULT 0.0",
        "dye_weight_g":    "REAL DEFAULT 0.0",
        "wire_weight_g":   "REAL DEFAULT 0.0",
        "strips_weight_g": "REAL DEFAULT 0.0",
        "total_output_g":  "REAL DEFAULT 0.0",
        "loss_pct":        "REAL DEFAULT 0.0",
        "status":          "TEXT DEFAULT 'pending'",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "wire_sheet_batches")
        if not existing:          # table doesn't exist yet; create_all handles it
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE wire_sheet_batches ADD COLUMN {col} {col_type}"
                ))
        # Seed rod_weight_g from old weight_in_g where available
        if "weight_in_g" in existing:
            conn.execute(text(
                "UPDATE wire_sheet_batches SET rod_weight_g = weight_in_g "
                "WHERE weight_in_g IS NOT NULL AND "
                "(rod_weight_g IS NULL OR rod_weight_g = 0.0)"
            ))
        conn.commit()


def migrate_faceting_batches(eng):
    """
    Add the loss-split columns needed to route Faceting weight loss between
    Melting (recycled scrap) and Gold Box (physical storage).
    Safe to run on every launch.
    """
    required = {
        "loss_to_melting_g":  "REAL DEFAULT 0.0",
        "loss_to_gold_box_g": "REAL DEFAULT 0.0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "faceting_batches")
        if not existing:          # table doesn't exist yet; create_all handles it
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE faceting_batches ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_wire_sheet_worker_columns(eng):
    """Add Team/Individual assignment columns to wire_sheet_batches."""
    required = {
        "assigned_to_type": "TEXT DEFAULT 'INDIVIDUAL'",
        "team_id":          "INTEGER",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "wire_sheet_batches")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE wire_sheet_batches ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_polish_tally_columns(eng):
    """Add Baby/Normal/30-Inch tally columns to polish_batches (input + output)."""
    required = {
        "input_qty_baby":    "INTEGER DEFAULT 0",
        "input_qty_normal":  "INTEGER DEFAULT 0",
        "input_qty_30inch":  "INTEGER DEFAULT 0",
        "output_qty_baby":   "INTEGER DEFAULT 0",
        "output_qty_normal": "INTEGER DEFAULT 0",
        "output_qty_30inch": "INTEGER DEFAULT 0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "polish_batches")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE polish_batches ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_goldsmith_return_tally_columns(eng):
    """Upgrade the Goldsmith return's Baby/Normal/30-Inch tally from notes text to real columns."""
    required = {
        "qty_baby":   "INTEGER DEFAULT 0",
        "qty_normal": "INTEGER DEFAULT 0",
        "qty_30inch": "INTEGER DEFAULT 0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "goldsmith_returns")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE goldsmith_returns ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_goldsmith_issue_misc_column(eng):
    """Add a misc/complaint gold bucket to goldsmith_issues, distinct from dye/wire/strips."""
    required = {
        "misc_issued_g": "REAL DEFAULT 0.0",
        "complaint_id":  "INTEGER",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "goldsmith_issues")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE goldsmith_issues ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_faceting_v2_columns(eng):
    """Add the create->update two-step columns to faceting_batches: status,
    Team/Individual assignment, and input/output Baby/Normal/30-Inch tallies."""
    required = {
        "status":            "TEXT DEFAULT 'pending'",
        "assigned_to_type":  "TEXT DEFAULT 'INDIVIDUAL'",
        "in_qty_baby":       "INTEGER DEFAULT 0",
        "in_qty_normal":     "INTEGER DEFAULT 0",
        "in_qty_30inch":     "INTEGER DEFAULT 0",
        "out_qty_baby":      "INTEGER DEFAULT 0",
        "out_qty_normal":    "INTEGER DEFAULT 0",
        "out_qty_30inch":    "INTEGER DEFAULT 0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "faceting_batches")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE faceting_batches ADD COLUMN {col} {col_type}"
                ))
        # Existing rows predate the two-step flow — treat them as already completed
        # so they don't suddenly show an "Update" action with a stale pending status.
        if "status" not in existing:
            conn.execute(text(
                "UPDATE faceting_batches SET status = 'completed' WHERE weight_out_g > 0"
            ))
        conn.commit()


def migrate_faceting_loss_routed_column(eng):
    """Add loss_routed to faceting_batches: the Update step now only records
    output weight/tally — the operator decides the Melting vs Gold Box split
    later, on the separate Faceting Loss page, once they actually know it.
    Pre-existing completed batches already had their loss routed under the
    old single-step logic, so backfill them as already-routed."""
    with eng.connect() as conn:
        existing = _get_columns(conn, "faceting_batches")
        if not existing:
            return
        if "loss_routed" not in existing:
            conn.execute(text(
                "ALTER TABLE faceting_batches ADD COLUMN loss_routed INTEGER DEFAULT 0"
            ))
            conn.execute(text(
                "UPDATE faceting_batches SET loss_routed = 1 WHERE status = 'completed'"
            ))
        conn.commit()


def migrate_complaint_tally_columns(eng):
    """Add the Baby/Normal/30-Inch tally to complaints, captured at creation
    time (mirrors the tally already captured on the Goldsmith return step)."""
    required = {
        "qty_baby":   "INTEGER DEFAULT 0",
        "qty_normal": "INTEGER DEFAULT 0",
        "qty_30inch": "INTEGER DEFAULT 0",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "complaints")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE complaints ADD COLUMN {col} {col_type}"
                ))
        conn.commit()


def migrate_v_account_columns(eng):
    """Add source-tracking, tally, and loss columns to v_account_entries."""
    required = {
        "source_type":     "TEXT DEFAULT 'MANUAL'",
        "source_id":       "INTEGER",
        "status":          "TEXT DEFAULT 'closed'",
        "qty_baby":        "INTEGER DEFAULT 0",
        "qty_normal":      "INTEGER DEFAULT 0",
        "qty_30inch":      "INTEGER DEFAULT 0",
        "loss_g":          "REAL DEFAULT 0.0",
        "loss_pct":        "REAL DEFAULT 0.0",
        "linked_entry_id": "INTEGER",
    }
    with eng.connect() as conn:
        existing = _get_columns(conn, "v_account_entries")
        if not existing:
            return
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE v_account_entries ADD COLUMN {col} {col_type}"
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
    migrate_wire_sheet_batches(engine)
    migrate_faceting_batches(engine)
    migrate_wire_sheet_worker_columns(engine)
    migrate_polish_tally_columns(engine)
    migrate_goldsmith_return_tally_columns(engine)
    migrate_goldsmith_issue_misc_column(engine)
    migrate_faceting_v2_columns(engine)
    migrate_v_account_columns(engine)
    migrate_faceting_loss_routed_column(engine)
    migrate_complaint_tally_columns(engine)
