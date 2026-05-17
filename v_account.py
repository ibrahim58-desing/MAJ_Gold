"""
V ACCOUNT — Virtual Account.

Seen in multiple sheets:
  - STOCK_SUM: V ACCOUNT section with daily opening/closing
  - DAYBOOK: 'V ACCOUNT / GS-CHANDRU', 'V ACCOUNT / GS-SHAIJU' entries
  - LEDGER: 'V ACCOUNT' is its own ledger account (DR: 3,45,939 CR: 3,44,764)

V ACCOUNT = a tracking account for gold that is "in the hands of"
faceting workers (FAC-*). When a faceting worker gets gold from gold box
it goes into V ACCOUNT as debit. When they return finished pieces, it's credited.

This is separate from the Goldsmith (GS-*) accounts.

STOCK_SUM V ACCOUNT section values (May 2026):
  01-May-26: Opening 1775.94 | IN: 472.56 | OUT: 1245.50 | Closing: 503.00 ...
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class VAccountEntry(Base):
    """
    V Account transaction — tracks gold movement through the virtual account.
    Every gold issue to a faceting worker debits V Account.
    Every finished piece return credits V Account.

    Seen in DAYBOOK:
      V ACCOUNT / GS-CHANDRU  (credit 1.43)  → settling goldsmith vs V account
      V ACCOUNT / GS-SHAIJU   (credit 3.55)
      V ACCOUNT / FAC-MUMTAJ  (debit 19.62)  → issuing gold via V account
    """
    __tablename__ = "v_account_entries"

    id              = Column(Integer, primary_key=True, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    worker_id       = Column(Integer, ForeignKey("workers.id"), nullable=False)
    particular      = Column(String(100), nullable=False)
    # "GOLD BOX", "CHAIN STOCK", "FAC-MUMTAJ", "GS-CHANDRU" etc
    debit_g         = Column(Float, default=0.0)
    debit_pcs       = Column(Integer, default=0)
    credit_g        = Column(Float, default=0.0)
    credit_pcs      = Column(Integer, default=0)
    balance_g       = Column(Float, default=0.0)    # running balance
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    voucher_ref     = Column(String(20))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="v_account_entries")


class VAccountDailyBalance(Base):
    """
    Daily summary of V Account — mirrors STOCK_SUM V ACCOUNT section.
    DATE | OPENING | IN | OUT | CLOSING | PHYSICAL | DIF SYS
    """
    __tablename__ = "v_account_daily_balance"

    id            = Column(Integer, primary_key=True, index=True)
    balance_date  = Column(Date, nullable=False, unique=True, index=True)
    opening_g     = Column(Float, default=0.0)
    total_in_g    = Column(Float, default=0.0)
    total_out_g   = Column(Float, default=0.0)
    closing_g     = Column(Float, default=0.0)
    physical_g    = Column(Float, nullable=True)
    sys_diff_g    = Column(Float, nullable=True)
    notes         = Column(Text)
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
