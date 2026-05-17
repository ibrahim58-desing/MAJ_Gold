"""
Stock Register models — matches TOT STOCK and STOCK_SUM sheets.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class FinishedStock(Base):
    __tablename__ = "finished_stock"

    id               = Column(Integer, primary_key=True, index=True)
    stocked_date     = Column(Date, nullable=False, index=True)
    kambi_batch_id   = Column(Integer, ForeignKey("kambi_batches.id"), nullable=True)
    stock_category   = Column(String(30), nullable=False)
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    design_type_id   = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    pcs_in           = Column(Integer, default=0)
    weight_in_g      = Column(Float, default=0.0)
    pcs_out          = Column(Integer, default=0)
    weight_out_g     = Column(Float, default=0.0)
    pcs_balance      = Column(Integer, default=0)
    weight_balance_g = Column(Float, default=0.0)
    location         = Column(String(20), default="MUM")
    purity           = Column(String(10), default="916")
    barcode          = Column(String(50), unique=True, nullable=True)
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())


class ChainStock(Base):
    __tablename__ = "chain_stock"

    id              = Column(Integer, primary_key=True, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    design_type_id  = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"))
    weight_g        = Column(Float, nullable=False)
    pcs             = Column(Integer, default=0)
    transaction     = Column(String(10), default="CREDIT")
    reference       = Column(String(50))
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())


class TagStock(Base):
    __tablename__ = "tag_stock"

    id              = Column(Integer, primary_key=True, index=True)
    tag_no          = Column(Integer, nullable=False, index=True)
    tag_date        = Column(Date, nullable=False)
    location        = Column(String(20))
    stock_category  = Column(String(30))
    product_type_id = Column(Integer, ForeignKey("product_types.id"))
    design_type_id  = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    tagged_weight_g = Column(Float, nullable=False)
    tagged_pcs      = Column(Integer, default=0)
    status          = Column(String(20), default="TAGGED")
    sale_date       = Column(Date, nullable=True)
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())


class StockSummaryDaily(Base):
    __tablename__ = "stock_summary_daily"

    id                    = Column(Integer, primary_key=True, index=True)
    summary_date          = Column(Date, nullable=False, unique=True, index=True)

    gb_opening_g          = Column(Float, default=0.0)
    gb_in_g               = Column(Float, default=0.0)
    gb_out_g              = Column(Float, default=0.0)
    gb_closing_g          = Column(Float, default=0.0)
    gb_physical_g         = Column(Float, nullable=True)
    gb_sys_diff_g         = Column(Float, nullable=True)
    gb_phy_diff_g         = Column(Float, nullable=True)

    gold_opening_g        = Column(Float, default=0.0)
    gold_in_g             = Column(Float, default=0.0)
    gold_out_g            = Column(Float, default=0.0)
    gold_closing_g        = Column(Float, default=0.0)
    gold_physical_g       = Column(Float, nullable=True)

    va_opening_g          = Column(Float, default=0.0)
    va_in_g               = Column(Float, default=0.0)
    va_out_g              = Column(Float, default=0.0)
    va_closing_g          = Column(Float, default=0.0)
    va_physical_g         = Column(Float, nullable=True)
    va_sys_diff_g         = Column(Float, nullable=True)

    notes                 = Column(Text)
    updated_at            = Column(DateTime, server_default=func.now(), onupdate=func.now())
