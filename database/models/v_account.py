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

    # source_type: MANUAL | FACETING | WIRE | COMPLAINT_SEND | COMPLAINT_RETURN
    source_type     = Column(String(20), default="MANUAL")
    source_id       = Column(Integer, nullable=True)
    status          = Column(String(20), default="closed")  # "open" only for unreturned wire draws
    qty_baby        = Column(Integer, default=0)
    qty_normal      = Column(Integer, default=0)
    qty_30inch      = Column(Integer, default=0)
    loss_g          = Column(Float, default=0.0)
    loss_pct        = Column(Float, default=0.0)
    linked_entry_id = Column(Integer, ForeignKey("v_account_entries.id"), nullable=True)

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


class Complaint(Base):
    """A small gold-quality issue on a worker's V Account item, routed to
    Goldsmith for rework. status: open -> sent_to_goldsmith -> resolved."""
    __tablename__ = "complaints"

    id                       = Column(Integer, primary_key=True, index=True)
    complaint_date           = Column(Date, nullable=False, index=True)
    worker_id                = Column(Integer, ForeignKey("workers.id"), nullable=False)
    v_account_entry_id       = Column(Integer, ForeignKey("v_account_entries.id"), nullable=True)
    description              = Column(Text)
    weight_sent_g            = Column(Float, default=0.0)
    qty_baby                 = Column(Integer, default=0)
    qty_normal                = Column(Integer, default=0)
    qty_30inch                = Column(Integer, default=0)
    goldsmith_issue_id       = Column(Integer, ForeignKey("goldsmith_issues.id"), nullable=True)
    debit_vaccount_entry_id  = Column(Integer, ForeignKey("v_account_entries.id"), nullable=True)
    credit_vaccount_entry_id = Column(Integer, ForeignKey("v_account_entries.id"), nullable=True)
    status                   = Column(String(20), default="open")
    loss_g                   = Column(Float, default=0.0)
    loss_pct                 = Column(Float, default=0.0)
    notes                    = Column(Text)
    created_at                = Column(DateTime, server_default=func.now())

    worker = relationship("Worker")
