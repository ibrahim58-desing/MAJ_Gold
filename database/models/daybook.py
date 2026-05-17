"""
DAYBOOK — Inventory Day Book (central double-entry ledger)
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class DaybookEntry(Base):
    __tablename__ = "daybook_entries"

    id             = Column(Integer, primary_key=True, index=True)
    entry_date     = Column(Date, nullable=False, index=True)
    ledger_account = Column(String(50), nullable=False, index=True)
    particular     = Column(String(100), nullable=False)
    debit_wt       = Column(Float, default=0.0)
    debit_pcs      = Column(Integer, default=0)
    credit_wt      = Column(Float, default=0.0)
    credit_pcs     = Column(Integer, default=0)
    serial_no      = Column(Integer, unique=True, nullable=False, index=True)
    voucher_ref    = Column(String(20), index=True)
    group_type     = Column(String(30), index=True)
    source_process = Column(String(30))
    notes          = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    is_edited      = Column(Boolean, default=False)
    edited_at      = Column(DateTime)
