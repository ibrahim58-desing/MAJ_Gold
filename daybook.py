"""
DAYBOOK — Inventory Day Book (central double-entry ledger)
Matches 'MAJ GOLD - INVENTORY DAY BOOK' sheet exactly.

Columns seen: DATE | LEDGER ACCOUNT | PARTICULAR | DEBIT | PCS | CREDIT | PCS | S NO | VOUCHER | GROUP

Entry types seen:
  - GS-MUSTHAFA / FAC-FACETING       (goldsmith → faceting handoff)
  - FAC-MUMTAJ / FAC-FACETING        (faceting worker entry)
  - 24K GOLD 999 / NG MELTING        (raw gold going into melt)
  - NG MELTING / 24K GOLD 999        (credit side of same)
  - NG MELTING / KAMBI               (melt output to kambi/link)
  - KAMBI / GOLD BOX                 (kambi drawing from gold box)
  - KAMBI / RETURN                   (returned gold)
  - KAMBI / WEIGHT LOSS              (process loss)
  - ALLOY / NG MELTING/SILVER etc    (alloy additions)
  - V ACCOUNT / GS-CHANDRU           (virtual account settlement)
  - WEIGHT LOSS / KAMBI              (loss entry)
  - CHAIN STOCK                      (finished chain stock)
  - HALLMARKING                      (hallmarking process)
  - SCRAP MELTING                    (solder/scrap remelted)

Every transaction creates TWO rows (double-entry):
  row 1: ledger_account=X, particular=Y, debit=amount
  row 2: ledger_account=Y, particular=X, credit=amount
Linked by voucher_ref (same number both rows).
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class DaybookEntry(Base):
    """
    One row in the INVENTORY DAY BOOK.
    Two rows per transaction (double-entry), linked by voucher_ref.
    """
    __tablename__ = "daybook_entries"

    id             = Column(Integer, primary_key=True, index=True)

    # --- Core fields matching the sheet columns ---
    entry_date     = Column(Date, nullable=False, index=True)
    ledger_account = Column(String(50), nullable=False, index=True)
    # e.g. "GS-MUSTHAFA", "FAC-MUMTAJ", "NG MELTING", "KAMBI", "24K GOLD 999"

    particular     = Column(String(100), nullable=False)
    # e.g. "FAC-FACETING", "GOLD BOX", "KAMBI", "NG MELTING / SILVER"

    debit_wt       = Column(Float, default=0.0)    # debit weight in grams
    debit_pcs      = Column(Integer, default=0)    # debit piece count
    credit_wt      = Column(Float, default=0.0)   # credit weight in grams
    credit_pcs     = Column(Integer, default=0)   # credit piece count

    # --- Linking & classification ---
    serial_no      = Column(Integer, unique=True, nullable=False, index=True)
    # sequential S NO seen in sheet (55420, 55421 etc)

    voucher_ref    = Column(String(20), index=True)
    # links the debit and credit row of one transaction

    group_type     = Column(String(30), index=True)
    # GROUP column seen: "GOLD SMITH", "FACETING" — classifies the entry type

    # --- Optional FK to source process for traceability ---
    source_process = Column(String(30))
    # MELTING / WIRE_SHEET / GOLDSMITH / FACETING / KAMBI / GOLD_BOX / HALLMARKING

    notes          = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    is_edited      = Column(Boolean, default=False)
    edited_at      = Column(DateTime)
