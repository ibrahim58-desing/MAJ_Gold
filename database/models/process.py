"""
Manufacturing process models.
Flow: MeltBatch → WireSheetBatch → GoldsmithBatch → PolishBatch → FacetingBatch → KambiBatch → FinishedStock
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class WireSheetBatch(Base):
    __tablename__ = 'wire_sheet_batches'

    id              = Column(Integer, primary_key=True, index=True)
    batch_date      = Column(Date, nullable=False, index=True)
    batch_type      = Column(String(20), default='wire')       # dye | wire | strip
    rod_weight_g    = Column(Float, default=0.0)               # CREDIT — gold input
    output_weight_g = Column(Float, default=0.0)               # DEBIT  — gold output (updated on completion)
    loss_g          = Column(Float, default=0.0)
    loss_pct        = Column(Float, default=0.0)
    status          = Column(String(20), default='pending')    # pending | completed
    daybook_sno     = Column(Integer, ForeignKey('daybook_entries.serial_no'), nullable=True)
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    # ── Legacy columns — kept to satisfy old DB NOT-NULL constraints ──
    weight_in_g     = Column(Float, default=0.0)
    weight_out_g    = Column(Float, default=0.0)
    melt_batch_id   = Column(Integer, ForeignKey('melt_batches.id'), default=0)
    worker_id       = Column(Integer, ForeignKey('workers.id'), nullable=True)

    melt_batch        = relationship("MeltBatch", foreign_keys=[melt_batch_id])
    goldsmith_batches = relationship("GoldsmithBatch", back_populates="wire_sheet_batch")


class GoldsmithBatch(Base):
    __tablename__ = "goldsmith_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    from_date           = Column(Date, nullable=False, index=True)
    to_date             = Column(Date, nullable=False, index=True)
    wire_sheet_batch_id = Column(Integer, ForeignKey("wire_sheet_batches.id"))
    weight_in_g         = Column(Float, nullable=False)
    weight_out_g        = Column(Float, nullable=False)
    weight_loss_g       = Column(Float, default=0.0)
    fin_pcs             = Column(Integer, default=0)
    per_pc_wl           = Column(Float, default=0.0)
    per_wl_02           = Column(Float, default=0.0)
    extra_loss_g        = Column(Float, default=0.0)
    solder_weight_g     = Column(Float, default=0.0)
    product_type_id     = Column(Integer, ForeignKey("product_types.id"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    wire_sheet_batch  = relationship("WireSheetBatch", back_populates="goldsmith_batches")
    worker_logs       = relationship("GoldsmithWorkerLog", back_populates="goldsmith_batch", cascade="all, delete-orphan")
    design_logs       = relationship("GoldsmithDesignLog", back_populates="goldsmith_batch", cascade="all, delete-orphan")
    polish_batches    = relationship("PolishBatch", back_populates="goldsmith_batch")


class GoldsmithWorkerLog(Base):
    __tablename__ = "goldsmith_worker_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    goldsmith_batch_id  = Column(Integer, ForeignKey("goldsmith_batches.id"), nullable=False)
    worker_id           = Column(Integer, ForeignKey("workers.id"), nullable=False)
    log_date            = Column(Date, nullable=False, index=True)
    from_date           = Column(Date)
    to_date             = Column(Date)
    debit_g             = Column(Float, default=0.0)
    credit_g            = Column(Float, default=0.0)
    weight_loss_g       = Column(Float, default=0.0)
    pcs                 = Column(Integer, default=0)
    ppwl                = Column(Float, default=0.0)
    act_wl              = Column(Float, default=0.0)
    extra_loss_g        = Column(Float, default=0.0)
    pay_earned          = Column(Float, default=0.0)
    daybook_sno         = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    goldsmith_batch = relationship("GoldsmithBatch", back_populates="worker_logs")
    worker          = relationship("Worker", back_populates="goldsmith_logs")


class GoldsmithDesignLog(Base):
    __tablename__ = "goldsmith_design_logs"

    id                 = Column(Integer, primary_key=True, index=True)
    goldsmith_batch_id = Column(Integer, ForeignKey("goldsmith_batches.id"), nullable=False)
    worker_id          = Column(Integer, ForeignKey("workers.id"), nullable=False)
    design_type_id     = Column(Integer, ForeignKey("design_types.id"), nullable=False)
    month_year         = Column(String(10), nullable=False, index=True)
    from_date          = Column(Date)
    to_date            = Column(Date)
    pieces_count       = Column(Integer, default=0)
    created_at         = Column(DateTime, server_default=func.now())

    goldsmith_batch = relationship("GoldsmithBatch", back_populates="design_logs")


class PolishBatch(Base):
    __tablename__ = "polish_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_date          = Column(Date, nullable=False, index=True)
    worker_id           = Column(Integer, ForeignKey("workers.id"))
    goldsmith_batch_id  = Column(Integer, ForeignKey("goldsmith_batches.id"), nullable=False)
    chains_in           = Column(Integer, default=0)
    chains_out          = Column(Integer, default=0)
    notes               = Column(Text, default="No gold loss in polish process")
    created_at          = Column(DateTime, server_default=func.now())

    goldsmith_batch   = relationship("GoldsmithBatch", back_populates="polish_batches")
    faceting_batches  = relationship("FacetingBatch", back_populates="polish_batch")


class FacetingBatch(Base):
    __tablename__ = "faceting_batches"

    id               = Column(Integer, primary_key=True, index=True)
    from_date        = Column(Date, nullable=False, index=True)
    to_date          = Column(Date, nullable=False, index=True)
    worker_id        = Column(Integer, ForeignKey("workers.id"))
    team_id          = Column(Integer, ForeignKey("teams.id"))
    polish_batch_id  = Column(Integer, ForeignKey("polish_batches.id"))
    weight_in_g      = Column(Float, nullable=False)
    weight_out_g     = Column(Float, nullable=False)
    weight_loss_g    = Column(Float, default=0.0)
    fin_pcs          = Column(Integer, default=0)
    ree_cu           = Column(Integer, default=0)
    act_fin_pcs      = Column(Integer, default=0)
    act_wl           = Column(Float, default=0.0)
    extra_loss_g     = Column(Float, default=0.0)
    solder_weight_g  = Column(Float, default=0.0)
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    v_account_used   = Column(Boolean, default=True)
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())

    polish_batch  = relationship("PolishBatch", back_populates="faceting_batches")
    kambi_batches = relationship("KambiBatch", back_populates="faceting_batch")


class KambiBatch(Base):
    __tablename__ = "kambi_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_date          = Column(Date, nullable=False, index=True)
    worker_id           = Column(Integer, ForeignKey("workers.id"))
    faceting_batch_id   = Column(Integer, ForeignKey("faceting_batches.id"))
    weight_in_g         = Column(Float, nullable=False)
    weight_out_g        = Column(Float, nullable=False)
    loss_g              = Column(Float, default=0.0)
    gold_box_drawn_g    = Column(Float, default=0.0)
    gold_returned_g     = Column(Float, default=0.0)
    chains_linked       = Column(Integer, default=0)
    hooks_used          = Column(Integer, default=0)
    solder_weight_g     = Column(Float, default=0.0)
    daybook_sno         = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    faceting_batch = relationship("FacetingBatch", back_populates="kambi_batches")
