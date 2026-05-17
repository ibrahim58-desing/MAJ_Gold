"""
GOLD BOX — the physical gold storage box in the factory.
Seen in STOCK_SUM sheet as a daily opening/closing balance.
Also seen in DAYBOOK: 'KAMBI / GOLD BOX', 'V ACCOUNT / GOLD BOX'

The Gold Box tracks:
  - Opening balance per day
  - Gold added (IN) — from melt output
  - Gold issued (OUT) — to workers for any process
  - Closing balance = Opening + IN - OUT
  - Physical count vs system count (DIF SYS column in STOCK_SUM)

From STOCK_SUM image (Gold Box section):
  DATE     | OPENING | IN    | OUT   | CLOSING | PHYSICAL | DIF SYS | PHY DIF
  01-May-26| 559.56  | 0.18  | 22.67 | 537.07  |          | -537.07
  04-May-26| 580.26  | 6.57  | 64.66 | 522.17  | 521.7    | -0.47   | -0.47
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class GoldBoxDailyBalance(Base):
    """
    Daily running balance of the gold box.
    Auto-computed from GoldBoxStock (IN) and GoldBoxIssue (OUT).
    Mirrors the GOLD BOX section of STOCK_SUM sheet.
    """
    __tablename__ = "gold_box_daily_balance"

    id               = Column(Integer, primary_key=True, index=True)
    balance_date     = Column(Date, nullable=False, unique=True, index=True)
    opening_g        = Column(Float, default=0.0)
    total_in_g       = Column(Float, default=0.0)
    total_out_g      = Column(Float, default=0.0)
    closing_g        = Column(Float, default=0.0)    # opening + in - out
    physical_g       = Column(Float, nullable=True)  # physical weigh-in
    system_diff_g    = Column(Float, nullable=True)  # closing - physical
    notes            = Column(Text)
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GoldBoxStock(Base):
    """
    Gold added INTO the gold box (IN transactions).
    Source can be a melt batch or a solder return being restocked.
    """
    __tablename__ = "gold_box_stock"

    id             = Column(Integer, primary_key=True, index=True)
    added_date     = Column(Date, nullable=False, index=True)
    source         = Column(String(30), nullable=False)
    # MELT_BATCH / SOLDER_RETURN / OPENING_BALANCE
    source_id      = Column(Integer)
    # FK to melt_batches.id or solder_returns.id
    weight_added_g = Column(Float, nullable=False)
    daybook_sno    = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes          = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())


class GoldBoxIssue(Base):
    """
    Gold issued OUT from the gold box to a worker for any process.
    Seen in DAYBOOK: 'KAMBI / GOLD BOX' — kambi worker drawing gold.
    Also: 'V ACCOUNT / GOLD BOX' — faceting worker drawing gold.

    Tracks:
      - issued weight
      - returned weight (if any returned unused)
      - net used = issued - returned
    """
    __tablename__ = "gold_box_issues"

    id                = Column(Integer, primary_key=True, index=True)
    issued_date       = Column(Date, nullable=False, index=True)
    worker_id         = Column(Integer, ForeignKey("workers.id"), nullable=False)
    process           = Column(String(30), nullable=False)
    # WIRE_SHEET / GOLDSMITH / FACETING / KAMBI / HALLMARKING
    weight_issued_g   = Column(Float, nullable=False)
    weight_returned_g = Column(Float, default=0.0)
    net_used_g        = Column(Float)
    # computed: weight_issued - weight_returned
    pcs_issued        = Column(Integer, default=0)
    daybook_sno       = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes             = Column(Text)
    created_at        = Column(DateTime, server_default=func.now())

    worker = relationship("Worker", back_populates="gold_box_issues")
