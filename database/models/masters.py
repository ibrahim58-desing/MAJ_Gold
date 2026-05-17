"""
Masters — reference/lookup tables that rarely change.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base


class ProcessType(str, enum.Enum):
    MELTING       = "MELTING"
    SCRAP_MELTING = "SCRAP_MELTING"
    WIRE_SHEET    = "WIRE_SHEET"
    GOLDSMITH     = "GOLDSMITH"
    POLISH        = "POLISH"
    FACETING      = "FACETING"
    KAMBI         = "KAMBI"
    HALLMARKING   = "HALLMARKING"
    GOLD_BOX      = "GOLD_BOX"


class PayType(str, enum.Enum):
    PER_CHAIN = "PER_CHAIN"
    MONTHLY   = "MONTHLY"


class GoldPurity(str, enum.Enum):
    K999  = "999"
    K9999 = "9999"
    K995  = "995"
    K996  = "996"
    K916  = "916"
    K22   = "22K"


class Dealer(Base):
    __tablename__ = "dealers"

    id         = Column(Integer, primary_key=True, index=True)
    code       = Column(String(20), unique=True, nullable=False)
    name       = Column(String(100), nullable=False)
    phone      = Column(String(20))
    address    = Column(Text)
    gstin      = Column(String(20))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    receipts = relationship("GoldReceipt", back_populates="dealer")


class Team(Base):
    __tablename__ = "teams"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(50), nullable=False)
    process_type = Column(String(20), nullable=False)
    created_at   = Column(DateTime, server_default=func.now())

    workers = relationship("Worker", back_populates="team")


class Worker(Base):
    __tablename__ = "workers"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(String(30), unique=True, nullable=False)
    name            = Column(String(100), nullable=False)
    phone           = Column(String(20))
    process_type    = Column(String(20), nullable=False)
    pay_type        = Column(String(20), default=PayType.PER_CHAIN)
    rate_per_chain  = Column(Float, default=0.0)
    monthly_wage    = Column(Float, default=0.0)
    team_id         = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_active       = Column(Boolean, default=True)
    joined_on       = Column(Date)
    created_at      = Column(DateTime, server_default=func.now())

    team                  = relationship("Team", back_populates="workers")
    goldsmith_logs        = relationship("GoldsmithWorkerLog", back_populates="worker")
    gold_box_issues       = relationship("GoldBoxIssue", back_populates="worker")
    v_account_entries     = relationship("VAccountEntry", back_populates="worker")


class ProductType(Base):
    __tablename__ = "product_types"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(20), unique=True, nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(Text)


class DesignType(Base):
    __tablename__ = "design_types"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(20), unique=True, nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(Text)


class AlloyType(Base):
    __tablename__ = "alloy_types"

    id   = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    alloy_additions = relationship("MeltBatchAlloy", back_populates="alloy_type")
