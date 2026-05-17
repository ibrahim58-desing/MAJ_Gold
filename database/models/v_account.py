"""
V ACCOUNT — Virtual Account for faceting workers.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class VAccountEntry(Base):
    __tablename__ = "v_account_entries"

    id              = Column(Integer, primary_key=True, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    worker_id       = Column(Integer, ForeignKey("workers.id"), nullable=False)
    particular      = Column(String(100), nullable=False)
    debit_g         = Column(Float, default=0.0)
    debit_pcs       = Column(Integer, default=0)
    credit_g        = Column(Float, default=0.0)
    credit_pcs      = Column(Integer, default=0)
    balance_g       = Column(Float, default=0.0)
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    voucher_ref     = Column(String(20))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="v_account_entries")


class VAccountDailyBalance(Base):
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
