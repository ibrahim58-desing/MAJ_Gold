"""
LEDGER — Ledger Account sheet.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id                   = Column(Integer, primary_key=True, index=True)
    code                 = Column(String(50), unique=True, nullable=False, index=True)
    name                 = Column(String(100), nullable=False)
    account_type         = Column(String(30), nullable=False)
    linked_worker_id     = Column(Integer, ForeignKey("workers.id"), nullable=True)
    opening_balance_g    = Column(Float, default=0.0)
    opening_balance_date = Column(Date)
    is_active            = Column(Boolean, default=True)
    created_at           = Column(DateTime, server_default=func.now())

    entries = relationship("LedgerEntry", back_populates="account", order_by="LedgerEntry.entry_date")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id              = Column(Integer, primary_key=True, index=True)
    account_id      = Column(Integer, ForeignKey("ledger_accounts.id"), nullable=False, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    particular      = Column(String(100), nullable=False)
    debit_g         = Column(Float, default=0.0)
    debit_pcs       = Column(Integer, default=0)
    credit_g        = Column(Float, default=0.0)
    credit_pcs      = Column(Integer, default=0)
    balance_g       = Column(Float, default=0.0)
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    voucher_ref     = Column(String(20))
    source_process  = Column(String(30))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    account = relationship("LedgerAccount", back_populates="entries")
