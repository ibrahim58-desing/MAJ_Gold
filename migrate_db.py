import sqlite3
import os

DB_PATH = os.environ.get("MAJ_GOLD_DB", "maj_gold.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def add_column_if_not_exists(table, column, col_def):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    if column not in columns:
        print(f"Adding {column} to {table}...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
    else:
        print(f"{column} already exists in {table}.")

try:
    # teams table
    add_column_if_not_exists("teams", "team_name", "VARCHAR(100)")
    add_column_if_not_exists("teams", "team_lead_id", "INTEGER")
    add_column_if_not_exists("teams", "is_active", "BOOLEAN DEFAULT 1")

    # wire_sheet_batches table
    add_column_if_not_exists("wire_sheet_batches", "dye_weight_g", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("wire_sheet_batches", "wire_weight_g", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("wire_sheet_batches", "strips_weight_g", "FLOAT DEFAULT 0.0")

    # polish_batches table (legacy table being extended)
    add_column_if_not_exists("polish_batches", "goldsmith_return_id", "INTEGER")
    add_column_if_not_exists("polish_batches", "input_pcs", "INTEGER DEFAULT 0")
    add_column_if_not_exists("polish_batches", "input_inches", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "input_weight_g", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "output_pcs", "INTEGER DEFAULT 0")
    add_column_if_not_exists("polish_batches", "output_inches", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "output_weight_g", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "polish_loss_g", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "polish_loss_pcs", "INTEGER DEFAULT 0")
    add_column_if_not_exists("polish_batches", "polish_loss_pct", "FLOAT DEFAULT 0.0")
    add_column_if_not_exists("polish_batches", "status", "VARCHAR(20) DEFAULT 'pending'")
    add_column_if_not_exists("polish_batches", "daybook_sno", "INTEGER")

    conn.commit()
    print("Migration successful.")
except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()

# Also create the new tables
from database.models.base import engine, Base
import database.models.process
import database.models.masters
Base.metadata.create_all(engine)
print("SQLAlchemy create_all completed.")
