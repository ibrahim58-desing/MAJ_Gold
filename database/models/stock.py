"""
Stock / raw material intake and melting.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class GoldReceipt(Base):
    __tablename__ = "gold_receipts"

    id              = Column(Integer, primary_key=True, index=True)
    receipt_date    = Column(Date, nullable=False, index=True)
    dealer_id       = Column(Integer, ForeignKey("dealers.id"), nullable=False)
    purity          = Column(String(10), nullable=False)
    weight_g        = Column(Float, nullable=False)
    net_weight_g    = Column(Float)
    receipt_no      = Column(String(30))
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    dealer      = relationship("Dealer", back_populates="receipts")
    melt_inputs = relationship("MeltBatchInput", back_populates="receipt")


class MeltBatch(Base):
    __tablename__ = "melt_batches"

    id               = Column(Integer, primary_key=True, index=True)
    batch_date       = Column(Date, nullable=False, index=True)
    melt_type        = Column(String(20), nullable=False)
    worker_id        = Column(Integer, ForeignKey("workers.id"))
    weight_in_g      = Column(Float, nullable=False)
    total_alloy_g    = Column(Float, default=0.0)
    gross_weight_g   = Column(Float)
    weight_out_916_g = Column(Float, nullable=False)
    ng_weight_g      = Column(Float, default=0.0)
    kambi_weight_g   = Column(Float, default=0.0)
    loss_g           = Column(Float, default=0.0)
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())

    alloy_additions  = relationship("MeltBatchAlloy", back_populates="melt_batch", cascade="all, delete-orphan")
    inputs           = relationship("MeltBatchInput", back_populates="melt_batch")
    solder_sources   = relationship("SolderReturn", back_populates="sent_to_melt")


class MeltBatchInput(Base):
    __tablename__ = "melt_batch_inputs"

    id            = Column(Integer, primary_key=True, index=True)
    melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=False)
    receipt_id    = Column(Integer, ForeignKey("gold_receipts.id"), nullable=True)
    weight_used_g = Column(Float, nullable=False)

    melt_batch = relationship("MeltBatch", back_populates="inputs")
    receipt    = relationship("GoldReceipt", back_populates="melt_inputs")


class MeltBatchAlloy(Base):
    __tablename__ = "melt_batch_alloys"

    id            = Column(Integer, primary_key=True, index=True)
    melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=False)
    alloy_type_id = Column(Integer, ForeignKey("alloy_types.id"), nullable=False)
    weight_g      = Column(Float, nullable=False)
    daybook_sno   = Column(Integer, ForeignKey("daybook_entries.serial_no"))

    melt_batch = relationship("MeltBatch", back_populates="alloy_additions")
    alloy_type = relationship("AlloyType", back_populates="alloy_additions")


class SolderReturn(Base):
    __tablename__ = "solder_returns"

    id                    = Column(Integer, primary_key=True, index=True)
    returned_date         = Column(Date, nullable=False, index=True)
    source_process        = Column(String(30), nullable=False)
    source_batch_id       = Column(Integer)
    weight_g              = Column(Float, nullable=False)
    product_type_id       = Column(Integer, ForeignKey("product_types.id"))
    sent_to_melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=True)
    daybook_sno           = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes                 = Column(Text)
    created_at            = Column(DateTime, server_default=func.now())

    sent_to_melt = relationship("MeltBatch", back_populates="solder_sources")
