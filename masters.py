"""
Masters — reference/lookup tables that rarely change.
Matches what is seen in the Excel sheets:
  - Dealers: SJU, DL, ML etc (receipt 24K - SJU/999)
  - Workers: GS-MUSTHAFA, GS-CHANDRU, FAC-MUMTAJ, FAC-ATHAUL etc
  - Teams: goldsmith teams, faceting teams
  - DesignType: KCN, SEEMA, BABY, 4S, FS30, 30INC (from GS-PCS sheet)
  - AlloyType: SILVER, COPPER, EXTRA COPPER, ZINC, EXTRA ZINC (from TOT STOCK)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base


class ProcessType(str, enum.Enum):
    """All processes in the factory."""
    MELTING       = "MELTING"
    SCRAP_MELTING = "SCRAP_MELTING"
    WIRE_SHEET    = "WIRE_SHEET"
    GOLDSMITH     = "GOLDSMITH"
    POLISH        = "POLISH"
    FACETING      = "FACETING"
    KAMBI         = "KAMBI"       # linking (chain + hook)
    HALLMARKING   = "HALLMARKING"
    GOLD_BOX      = "GOLD_BOX"


class PayType(str, enum.Enum):
    PER_CHAIN = "PER_CHAIN"
    MONTHLY   = "MONTHLY"


class GoldPurity(str, enum.Enum):
    """Incoming raw gold purities + outgoing 916."""
    K999  = "999"
    K9999 = "9999"
    K995  = "995"
    K996  = "996"
    K916  = "916"
    K22   = "22K"    # 22K finished stock


class Dealer(Base):
    """
    Gold suppliers / dealers.
    Examples seen: SJU, DL, ML (from 'RECEIPT 24K - SJU/999')
    """
    __tablename__ = "dealers"

    id         = Column(Integer, primary_key=True, index=True)
    code       = Column(String(20), unique=True, nullable=False)   # SJU, DL, ML
    name       = Column(String(100), nullable=False)
    phone      = Column(String(20))
    address    = Column(Text)
    gstin      = Column(String(20))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    receipts = relationship("GoldReceipt", back_populates="dealer")


class Team(Base):
    """
    Work teams. E.g. goldsmith teams 1-4, faceting teams 1-2.
    Seen in GS-CLOSING sheet as groups of workers.
    """
    __tablename__ = "teams"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(50), nullable=False)
    process_type = Column(String(20), nullable=False)  # GOLDSMITH / FACETING
    created_at   = Column(DateTime, server_default=func.now())

    workers = relationship("Worker", back_populates="team")


class Worker(Base):
    """
    All factory workers.
    Naming convention seen: GS-MUSTHAFA, GS-CHANDRU, GS-SHAIJU, GS-MARILAL,
    GS-ISRAIL, GS-RAJU, GS-SATHEESH (goldsmith), GS-BALLS, GS-MOKTHAR
    FAC-MUMTAJ, FAC-ATHAUL, FAC-RAJDIP (faceting)
    Also: KAMBI worker for linking process
    """
    __tablename__ = "workers"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(String(30), unique=True, nullable=False)  # GS-MUSTHAFA
    name            = Column(String(100), nullable=False)
    phone           = Column(String(20))
    process_type    = Column(String(20), nullable=False)   # GOLDSMITH / FACETING / KAMBI / MELTING
    pay_type        = Column(String(20), default=PayType.PER_CHAIN)
    rate_per_chain  = Column(Float, default=0.0)   # if PER_CHAIN
    monthly_wage    = Column(Float, default=0.0)   # if MONTHLY
    team_id         = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_active       = Column(Boolean, default=True)
    joined_on       = Column(Date)
    created_at      = Column(DateTime, server_default=func.now())

    team                  = relationship("Team", back_populates="workers")
    goldsmith_logs        = relationship("GoldsmithWorkerLog", back_populates="worker")
    gold_box_issues       = relationship("GoldBoxIssue", back_populates="worker")
    v_account_entries     = relationship("VAccountEntry", back_populates="worker")


class ProductType(Base):
    """
    Product categories.
    Seen: CHAIN (main), PURSE (seen in TOT STOCK header), BOX 22K, FACTORY 22K
    """
    __tablename__ = "product_types"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(20), unique=True, nullable=False)   # CHAIN, PURSE, BOX
    name        = Column(String(100), nullable=False)
    description = Column(Text)


class DesignType(Base):
    """
    Chain design types — used in GS-PCS (goldsmith piece count) sheet.
    Seen: KCN, SEEMA, BABY, 4S, FS30, 30INC
    """
    __tablename__ = "design_types"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(20), unique=True, nullable=False)   # KCN, SEEMA, BABY
    name        = Column(String(100), nullable=False)
    description = Column(Text)


class AlloyType(Base):
    """
    Alloys added during melting.
    Seen in TOT STOCK and DAYBOOK: SILVER, COPPER, EXTRA COPPER, ZINC, EXTRA ZINC
    """
    __tablename__ = "alloy_types"

    id   = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)  # SILVER, COPPER
    name = Column(String(100), nullable=False)

    alloy_additions = relationship("MeltBatchAlloy", back_populates="alloy_type")
