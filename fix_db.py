"""
fix_db.py -- One-time database column migration.
Uses raw sqlite3 -- no SQLAlchemy dependency.
Run once from project root: python fix_db.py
"""
import sqlite3
import os
import sys

DB_PATH = os.environ.get("MAJ_GOLD_DB", "maj_gold.db")
script_dir = os.path.dirname(os.path.abspath(__file__))
db_full_path = os.path.join(script_dir, DB_PATH)

if not os.path.exists(db_full_path):
    print("[ERROR] Database not found: " + db_full_path)
    sys.exit(1)

print("[INFO] Connecting to: " + db_full_path)

conn = sqlite3.connect(db_full_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(melt_batches)")
rows = cur.fetchall()
existing = [r[1] for r in rows]

print("[INFO] Current melt_batches columns: " + str(existing))

def add_col(name, col_type):
    if name in existing:
        print("  [SKIP] " + name + " already exists")
        return
    cur.execute("ALTER TABLE melt_batches ADD COLUMN " + name + " " + col_type)
    existing.append(name)
    print("  [ADD]  " + name + " " + col_type)

def copy_data(src, dst):
    if src not in existing:
        print("  [SKIP] copy " + src + " (not in DB)")
        return
    cur.execute(
        "UPDATE melt_batches SET " + dst + " = " + src +
        " WHERE " + src + " IS NOT NULL AND (" + dst + " IS NULL OR " + dst + " = 0.0)"
    )
    print("  [COPY] " + src + " -> " + dst + " (" + str(cur.rowcount) + " rows)")

print("")
print("[STEP 1] Adding missing columns...")

# Old name was weight_in_g -- new model name is input_weight_g
add_col("input_weight_g",   "REAL DEFAULT 0.0")
add_col("subtype",          "TEXT DEFAULT 'ornaments'")
add_col("lot_id",           "INTEGER")
add_col("purity_value",     "REAL DEFAULT 0.0")
add_col("metal_a_g",        "REAL DEFAULT 0.0")
add_col("metal_b_g",        "REAL DEFAULT 0.0")
add_col("extra_alloy_g",    "REAL DEFAULT 0.0")
add_col("total_alloy_g",    "REAL DEFAULT 0.0")
add_col("gross_weight_g",   "REAL DEFAULT 0.0")
add_col("final_916_g",      "REAL DEFAULT 0.0")
add_col("weight_out_916_g", "REAL DEFAULT 0.0")
add_col("ng_weight_g",      "REAL DEFAULT 0.0")
add_col("kambi_weight_g",   "REAL DEFAULT 0.0")
add_col("loss_g",           "REAL DEFAULT 0.0")
add_col("supplier_id",      "INTEGER")

print("")
print("[STEP 2] Copying data from renamed columns...")

# weight_in_g -> input_weight_g
copy_data("weight_in_g",       "input_weight_g")
# silver_g -> metal_a_g  (in case old DB had those names)
copy_data("silver_g",          "metal_a_g")
# copper_g -> metal_b_g
copy_data("copper_g",          "metal_b_g")
# weight_out_916_g -> final_916_g  (fill if final_916_g is empty)
copy_data("weight_out_916_g",  "final_916_g")

conn.commit()
conn.close()

print("")
print("[DONE] Migration complete. Restart the application.")
