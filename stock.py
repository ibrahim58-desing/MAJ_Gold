"""
Stock / raw material intake and melting.

Gold Receipts — seen in TOT STOCK as:
  RECEIPT 24K - SJU/999   (credit 103.20)
  RECEIPT 24K - DL/999    (credit 125.92)
  RECEIPT 24K - ML/999    (credit 2.29)

Melt Batches — NG MELTING (new gold melting) and SCRAP MELTING (solder remelted).
  - Produces: NG (new gold) + KAMBI gold
  - Each melt records alloys added per alloy type

MeltBatchAlloy — the alloy additions per melt:
  ADDED ALLOY - SILVER       10.76
  ADDED ALLOY - COPPER       32.30
  ADDED ALLOY - EXTRA COPPER  0.11
  ADDED ALLOY - ZINC          8.11
  ADDED ALLOY - EXTRA ZINC    0.13

SolderReturn — scrap/solder coming back from any process to be remelted.
  Seen in DAYBOOK as "SCRAP MELTING" entries.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class GoldReceipt(Base):
    """
    Raw gold received from a dealer.
    E.g. 'RECEIPT 24K - SJU/999', 'RECEIPT 24K - DL/999'
    """
    __tablename__ = "gold_receipts"

    id              = Column(Integer, primary_key=True, index=True)
    receipt_date    = Column(Date, nullable=False, index=True)
    dealer_id       = Column(Integer, ForeignKey("dealers.id"), nullable=False)
    purity          = Column(String(10), nullable=False)   # 999, 9999, 995, 996
    weight_g        = Column(Float, nullable=False)        # gross weight received
    net_weight_g    = Column(Float)                        # after deductions if any
    receipt_no      = Column(String(30))                   # physical receipt number
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    dealer      = relationship("Dealer", back_populates="receipts")
    melt_inputs = relationship("MeltBatchInput", back_populates="receipt")


class MeltBatch(Base):
    """
    One melting session — NG MELTING or SCRAP MELTING.
    A single melt may take gold from multiple receipts (MeltBatchInput).
    Alloys added are in MeltBatchAlloy (child records).
    Output goes to:
      - ng_weight_g  → goes to Wire & Sheet / Goldsmith
      - kambi_weight_g → goes to Kambi (linking) process
      - loss_g       → weight lost in melt
    """
    __tablename__ = "melt_batches"

    id               = Column(Integer, primary_key=True, index=True)
    batch_date       = Column(Date, nullable=False, index=True)
    melt_type        = Column(String(20), nullable=False)
    # NG_MELTING or SCRAP_MELTING

    worker_id        = Column(Integer, ForeignKey("workers.id"))
    # same person does melting + wire/sheet

    weight_in_g      = Column(Float, nullable=False)     # total gold going in
    total_alloy_g    = Column(Float, default=0.0)        # sum of all alloys added
    gross_weight_g   = Column(Float)                     # weight_in + alloy = melt input
    weight_out_916_g = Column(Float, nullable=False)     # output at 916 purity

    # Output split
    ng_weight_g      = Column(Float, default=0.0)        # new gold portion
    kambi_weight_g   = Column(Float, default=0.0)        # gold for kambi/linking
    loss_g           = Column(Float, default=0.0)        # computed: gross - out

    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())

    alloy_additions  = relationship("MeltBatchAlloy", back_populates="melt_batch", cascade="all, delete-orphan")
    inputs           = relationship("MeltBatchInput", back_populates="melt_batch")
    solder_sources   = relationship("SolderReturn", back_populates="sent_to_melt")


class MeltBatchInput(Base):
    """
    Which gold receipts (or solder returns) went into a melt batch.
    A melt can combine multiple dealer receipts.
    """
    __tablename__ = "melt_batch_inputs"

    id            = Column(Integer, primary_key=True, index=True)
    melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=False)
    receipt_id    = Column(Integer, ForeignKey("gold_receipts.id"), nullable=True)
    # null if input is solder, not fresh receipt
    weight_used_g = Column(Float, nullable=False)

    melt_batch = relationship("MeltBatch", back_populates="inputs")
    receipt    = relationship("GoldReceipt", back_populates="melt_inputs")


class MeltBatchAlloy(Base):
    """
    Alloys added during a melt batch.
    One row per alloy type per batch.
    E.g. ADDED ALLOY - SILVER: 10.76g
    """
    __tablename__ = "melt_batch_alloys"

    id            = Column(Integer, primary_key=True, index=True)
    melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=False)
    alloy_type_id = Column(Integer, ForeignKey("alloy_types.id"), nullable=False)
    weight_g      = Column(Float, nullable=False)
    daybook_sno   = Column(Integer, ForeignKey("daybook_entries.serial_no"))

    melt_batch = relationship("MeltBatch", back_populates="alloy_additions")
    alloy_type = relationship("AlloyType", back_populates="alloy_additions")


class SolderReturn(Base):
    """
    Solder/scrap collected from any process and returned to be remelted.
    source_process tells us where the scrap came from.
    sent_to_melt_batch_id links to the melt that consumed it.

    Seen in DAYBOOK as 'SCRAP MELTING' entries.
    Also seen in LEDGER: 'SCRAP MELTING' 43.43 credit on 15-May-26.
    """
    __tablename__ = "solder_returns"

    id                    = Column(Integer, primary_key=True, index=True)
    returned_date         = Column(Date, nullable=False, index=True)
    source_process        = Column(String(30), nullable=False)
    # MELTING / WIRE_SHEET / GOLDSMITH / FACETING / KAMBI / HALLMARKING

    source_batch_id       = Column(Integer)
    # FK to the relevant process batch table (flexible — stored as int)

    weight_g              = Column(Float, nullable=False)
    product_type_id       = Column(Integer, ForeignKey("product_types.id"))
    sent_to_melt_batch_id = Column(Integer, ForeignKey("melt_batches.id"), nullable=True)
    daybook_sno           = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes                 = Column(Text)
    created_at            = Column(DateTime, server_default=func.now())

    sent_to_melt = relationship("MeltBatch", back_populates="solder_sources")
