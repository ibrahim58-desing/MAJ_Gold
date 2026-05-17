"""
GOLD BOX — the physical gold storage box in the factory.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class GoldBoxDailyBalance(Base):
    __tablename__ = "gold_box_daily_balance"

    id               = Column(Integer, primary_key=True, index=True)
    balance_date     = Column(Date, nullable=False, unique=True, index=True)
    opening_g        = Column(Float, default=0.0)
    total_in_g       = Column(Float, default=0.0)
    total_out_g      = Column(Float, default=0.0)
    closing_g        = Column(Float, default=0.0)
    physical_g       = Column(Float, nullable=True)
    system_diff_g    = Column(Float, nullable=True)
    notes            = Column(Text)
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GoldBoxStock(Base):
    __tablename__ = "gold_box_stock"

    id             = Column(Integer, primary_key=True, index=True)
    added_date     = Column(Date, nullable=False, index=True)
    source         = Column(String(30), nullable=False)
    source_id      = Column(Integer)
    weight_added_g = Column(Float, nullable=False)
    daybook_sno    = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes          = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())


class GoldBoxIssue(Base):
    __tablename__ = "gold_box_issues"

    id                = Column(Integer, primary_key=True, index=True)
    issued_date       = Column(Date, nullable=False, index=True)
    worker_id         = Column(Integer, ForeignKey("workers.id"), nullable=False)
    process           = Column(String(30), nullable=False)
    weight_issued_g   = Column(Float, nullable=False)
    weight_returned_g = Column(Float, default=0.0)
    net_used_g        = Column(Float)
    pcs_issued        = Column(Integer, default=0)
    daybook_sno       = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes             = Column(Text)
    created_at        = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="gold_box_issues")
