"""
Database initialization — creates all tables and seeds master data.
Run this once when setting up the application for the first time.

Usage:
    python -m database.init_db
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.models.base import engine, SessionLocal, init_db
from database.models.masters import (
    Dealer, Worker, Team, ProductType, DesignType, AlloyType
)
from database.models.ledger import LedgerAccount


def seed_alloy_types(db):
    alloys = [
        {"code": "SILVER",       "name": "Added Alloy - Silver"},
        {"code": "COPPER",       "name": "Added Alloy - Copper"},
        {"code": "EXTRA_COPPER", "name": "Added Alloy - Extra Copper"},
        {"code": "ZINC",         "name": "Added Alloy - Zinc"},
        {"code": "EXTRA_ZINC",   "name": "Added Alloy - Extra Zinc"},
    ]
    for a in alloys:
        if not db.query(AlloyType).filter_by(code=a["code"]).first():
            db.add(AlloyType(**a))


def seed_product_types(db):
    products = [
        {"code": "CHAIN",       "name": "Chain 22K"},
        {"code": "BOX",         "name": "Box 22K"},
        {"code": "FACTORY",     "name": "Factory 22K"},
        {"code": "PURSE",       "name": "Purse"},
        {"code": "999",         "name": "24K Gold 999"},
        {"code": "995",         "name": "Gold 995"},
    ]
    for p in products:
        if not db.query(ProductType).filter_by(code=p["code"]).first():
            db.add(ProductType(**p))


def seed_design_types(db):
    """Design types seen in GS-PCS sheet."""
    designs = [
        {"code": "KCN",   "name": "KCN Design"},
        {"code": "SEEMA", "name": "Seema Design"},
        {"code": "BABY",  "name": "Baby Design"},
        {"code": "4S",    "name": "4S Design"},
        {"code": "FS30",  "name": "FS30 Design"},
        {"code": "30INC", "name": "30 Inch Design"},
    ]
    for d in designs:
        if not db.query(DesignType).filter_by(code=d["code"]).first():
            db.add(DesignType(**d))


def seed_teams(db):
    """Teams seen in GS-CLOSING: goldsmith teams + faceting teams."""
    teams = [
        {"name": "Goldsmith Team",  "process_type": "GOLDSMITH"},
        {"name": "Faceting Team 1", "process_type": "FACETING"},
        {"name": "Faceting Team 2", "process_type": "FACETING"},
    ]
    for t in teams:
        if not db.query(Team).filter_by(name=t["name"]).first():
            db.add(Team(**t))
    db.flush()


def seed_workers(db):
    """
    Workers seen across sheets.
    GS-* = Goldsmith, FAC-* = Faceting, KAMBI = linking worker.
    """
    gs_team  = db.query(Team).filter_by(name="Goldsmith Team").first()
    fac_team = db.query(Team).filter_by(name="Faceting Team 1").first()
    fac_team2= db.query(Team).filter_by(name="Faceting Team 2").first()

    workers = [
        # Goldsmiths (per-chain pay)
        {"code": "GS-MUSTHAFA", "name": "Musthafa",  "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-BALLS",    "name": "Balls",      "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-MOKTHAR",  "name": "Mokthar",    "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-CHANDRU",  "name": "Chandru",    "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-SHAIJU",   "name": "Shaiju",     "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-MARILAL",  "name": "Marilal",    "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-ISRAIL",   "name": "Israil",     "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-RAJU",     "name": "Raju",       "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        {"code": "GS-SATHEESH", "name": "Satheesh",   "process_type": "GOLDSMITH", "pay_type": "PER_CHAIN", "team_id": gs_team.id},
        # Faceting workers
        {"code": "FAC-MUMTAJ",  "name": "Mumtaj",     "process_type": "FACETING",  "pay_type": "PER_CHAIN", "team_id": fac_team.id},
        {"code": "FAC-ATHAUL",  "name": "Athaul",     "process_type": "FACETING",  "pay_type": "PER_CHAIN", "team_id": fac_team.id},
        {"code": "FAC-RAJDIP",  "name": "Rajdip",     "process_type": "FACETING",  "pay_type": "PER_CHAIN", "team_id": fac_team2.id},
        {"code": "FAC-SUJA",    "name": "Suja",       "process_type": "FACETING",  "pay_type": "PER_CHAIN", "team_id": fac_team2.id},
        # Kambi / linking
        {"code": "KAMBI",       "name": "Kambi Worker","process_type": "KAMBI",    "pay_type": "MONTHLY"},
    ]
    for w in workers:
        if not db.query(Worker).filter_by(code=w["code"]).first():
            db.add(Worker(**w))


def seed_ledger_accounts(db):
    """Pre-create ledger accounts matching the LEDGER sheet."""
    accounts = [
        {"code": "V_ACCOUNT",    "name": "V Account",         "account_type": "VIRTUAL"},
        {"code": "CHAIN_STOCK",  "name": "Chain Stock",        "account_type": "STOCK"},
        {"code": "GOLD_BOX",     "name": "Gold Box",           "account_type": "STOCK"},
        {"code": "NG_MELTING",   "name": "NG Melting",         "account_type": "PROCESS"},
        {"code": "SCRAP_MELTING","name": "Scrap Melting",      "account_type": "PROCESS"},
        {"code": "KAMBI",        "name": "Kambi",              "account_type": "PROCESS"},
        {"code": "HALLMARKING",  "name": "Hallmarking",        "account_type": "PROCESS"},
        {"code": "WEIGHT_LOSS",  "name": "Weight Loss",        "account_type": "PROCESS"},
        {"code": "24K_GOLD_999", "name": "24K Gold 999",       "account_type": "STOCK"},
        {"code": "ALLOY",        "name": "Alloy",              "account_type": "STOCK"},
        # Worker ledger accounts (one per worker)
        {"code": "GS-MUSTHAFA",  "name": "GS Musthafa",        "account_type": "WORKER"},
        {"code": "GS-CHANDRU",   "name": "GS Chandru",         "account_type": "WORKER"},
        {"code": "GS-SHAIJU",    "name": "GS Shaiju",          "account_type": "WORKER"},
        {"code": "GS-MARILAL",   "name": "GS Marilal",         "account_type": "WORKER"},
        {"code": "GS-ISRAIL",    "name": "GS Israil",          "account_type": "WORKER"},
        {"code": "GS-RAJU",      "name": "GS Raju",            "account_type": "WORKER"},
        {"code": "GS-SATHEESH",  "name": "GS Satheesh",        "account_type": "WORKER"},
        {"code": "GS-BALLS",     "name": "GS Balls",           "account_type": "WORKER"},
        {"code": "GS-MOKTHAR",   "name": "GS Mokthar",         "account_type": "WORKER"},
        {"code": "FAC-MUMTAJ",   "name": "FAC Mumtaj",         "account_type": "WORKER"},
        {"code": "FAC-ATHAUL",   "name": "FAC Athaul",         "account_type": "WORKER"},
        {"code": "FAC-RAJDIP",   "name": "FAC Rajdip",         "account_type": "WORKER"},
        {"code": "FAC-SUJA",     "name": "FAC Suja",           "account_type": "WORKER"},
    ]
    for a in accounts:
        if not db.query(LedgerAccount).filter_by(code=a["code"]).first():
            db.add(LedgerAccount(**a))


def main():
    print("Creating all database tables...")
    init_db()
    print("Tables created.")

    db = SessionLocal()
    try:
        print("Seeding master data...")
        seed_alloy_types(db)
        seed_product_types(db)
        seed_design_types(db)
        seed_teams(db)
        seed_workers(db)
        seed_ledger_accounts(db)
        db.commit()
        print("Seed data inserted successfully.")
        print("\nDatabase ready: maj_gold.db")
        print("\nTables created:")
        from database.models.base import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        for table in sorted(inspector.get_table_names()):
            print(f"  ✓ {table}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
