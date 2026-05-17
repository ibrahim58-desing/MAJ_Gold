"""
LEDGER — Ledger Account sheet.

Sheet seen: 'LEDGER ACCOUNT' — a running account per entity.
Header: LEDGER ACCOUNT | DATE | PARTICULAR | DEBIT | PCS D | CREDIT | PCS C | BALANCE

Accounts seen:
  V ACCOUNT (virtual account for faceting workers)
  GS-MUSTHAFA, GS-CHANDRU, GS-MARILAL, GS-ISRAIL (goldsmiths)
  FAC-MUMTAJ, FAC-ATHAUL (faceting)
  KAMBI
  CHAIN STOCK
  HALLMARKING
  SCRAP MELTING

V ACCOUNT Totals seen (01-01-23 to 16-05-26):
  DR: 3,45,939.22 | CR: 3,44,764.79 | PCS: 17066 | BALANCE: 1,174.43

GS-MUSTHAFA running total:
  DR: 171201.323 | CR: 170275.21 | CL: 926.11

Particulars seen within V ACCOUNT ledger:
  OPENING, GOLD BOX, CHAIN STOCK (debit & credit), KAMBI,
  FAC-MUMTAJ, FAC-ATHAUL, GS-MARILAL, GS-CHANDRU etc.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class LedgerAccount(Base):
    """
    A ledger account — one per entity (worker, process, stock type).
    Opening balance is set once; running balance maintained via LedgerEntry.

    Seen account codes: V_ACCOUNT, GS_MUSTHAFA, FAC_MUMTAJ, KAMBI, CHAIN_STOCK,
    HALLMARKING, SCRAP_MELTING, 24K_GOLD_999 etc.
    """
    __tablename__ = "ledger_accounts"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(String(50), unique=True, nullable=False, index=True)
    # V_ACCOUNT, GS_MUSTHAFA, FAC_MUMTAJ etc
    name            = Column(String(100), nullable=False)
    account_type    = Column(String(30), nullable=False)
    # WORKER / PROCESS / STOCK / VIRTUAL
    linked_worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    opening_balance_g = Column(Float, default=0.0)
    opening_balance_date = Column(Date)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())

    entries = relationship("LedgerEntry", back_populates="account", order_by="LedgerEntry.entry_date")


class LedgerEntry(Base):
    """
    One row in the ledger for an account — debit or credit with running balance.

    Matches LEDGER sheet columns:
      LEDGER ACCOUNT | DATE | PARTICULAR | DEBIT | PCS D | CREDIT | PCS C | BALANCE

    Example rows (V ACCOUNT):
      01-Jun-24 | OPENING      | Dr: 1815.48 |         | bal: 1815.48
      01-Jun-24 | GOLD BOX     | Dr: 13.30   |         | bal: ...
      01-Jun-24 | CHAIN STOCK  |             | Cr: 801.13 | 21 pcs
      01-Jun-24 | KAMBI        | Dr: 65.39   |         |
      01-Jun-24 | FAC-MUMTAJ   | Dr: 235.99  | 22 pcs  |
    """
    __tablename__ = "ledger_entries"

    id              = Column(Integer, primary_key=True, index=True)
    account_id      = Column(Integer, ForeignKey("ledger_accounts.id"), nullable=False, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    particular      = Column(String(100), nullable=False)
    # the contra account name / description

    debit_g         = Column(Float, default=0.0)
    debit_pcs       = Column(Integer, default=0)
    credit_g        = Column(Float, default=0.0)
    credit_pcs      = Column(Integer, default=0)
    balance_g       = Column(Float, default=0.0)    # running balance after this entry
    # positive = debit-heavy, negative = credit-heavy

    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    voucher_ref     = Column(String(20))
    source_process  = Column(String(30))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    account = relationship("LedgerAccount", back_populates="entries")
