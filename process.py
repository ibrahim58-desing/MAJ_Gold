"""
Manufacturing process models.

Flow: MeltBatch → WireSheetBatch → GoldsmithBatch → PolishBatch → FacetingBatch → KambiBatch → FinishedStock

GoldsmithWorkerLog: per-worker per-day log inside a goldsmith batch.
  Supports per-chain pay calculation.
  Seen in GS-CLOSING sheet: debit, credit, wt loss, pcs, per pc wl, extra loss.
  Seen in GS-PCS sheet: worker × design type × month piece counts.

FacetingBatch: 2 teams (FAC-MUMTAJ, FAC-ATHAUL, FAC-RAJDIP seen).
  Uses V ACCOUNT for gold issued (seen in DAYBOOK).

KambiBatch: linking chain + hook.
  Seen in DAYBOOK as 'KAMBI' ledger account with GOLD BOX, RETURN, WEIGHT LOSS entries.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─── Wire & Sheet ────────────────────────────────────────────────────────────

class WireSheetBatch(Base):
    """
    Wire drawing and sheet rolling after melting.
    Same worker as melting (noted in requirements).
    Gold comes from MeltBatch.ng_weight_g.
    Produces wires/sheets ready for goldsmiths.
    """
    __tablename__ = "wire_sheet_batches"

    id               = Column(Integer, primary_key=True, index=True)
    batch_date       = Column(Date, nullable=False, index=True)
    worker_id        = Column(Integer, ForeignKey("workers.id"))
    melt_batch_id    = Column(Integer, ForeignKey("melt_batches.id"), nullable=False)
    weight_in_g      = Column(Float, nullable=False)
    weight_out_g     = Column(Float, nullable=False)
    loss_g           = Column(Float, default=0.0)       # computed
    chains_count     = Column(Integer, default=0)
    solder_weight_g  = Column(Float, default=0.0)       # scrap from this process
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())

    goldsmith_batches = relationship("GoldsmithBatch", back_populates="wire_sheet_batch")


# ─── Goldsmith ────────────────────────────────────────────────────────────────

class GoldsmithBatch(Base):
    """
    A goldsmith batch: gold handed out to goldsmith team/worker for a period.
    Weight in comes from WireSheetBatch output.

    GS-CLOSING sheet columns:
      S.NO | GOLD SMITH | FROM DATE | TO DATE | DEBIT | CREDIT | WEIGHT LOSS | FIN PCS
      | PER PC WL | PER/WL/02 | EXTRA LOSS

    1ST CLOSING and 2ND CLOSING sections in the same sheet allow
    mid-period closings (e.g. for audit or handover checks).
    """
    __tablename__ = "goldsmith_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    from_date           = Column(Date, nullable=False, index=True)
    to_date             = Column(Date, nullable=False, index=True)
    wire_sheet_batch_id = Column(Integer, ForeignKey("wire_sheet_batches.id"))
    weight_in_g         = Column(Float, nullable=False)    # DEBIT total
    weight_out_g        = Column(Float, nullable=False)    # CREDIT total
    weight_loss_g       = Column(Float, default=0.0)      # WEIGHT LOSS
    fin_pcs             = Column(Integer, default=0)       # finished pieces
    per_pc_wl           = Column(Float, default=0.0)       # per piece weight loss
    per_wl_02           = Column(Float, default=0.0)       # target wl/02 standard
    extra_loss_g        = Column(Float, default=0.0)       # actual - standard
    solder_weight_g     = Column(Float, default=0.0)
    product_type_id     = Column(Integer, ForeignKey("product_types.id"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    wire_sheet_batch  = relationship("WireSheetBatch", back_populates="goldsmith_batches")
    worker_logs       = relationship("GoldsmithWorkerLog", back_populates="goldsmith_batch", cascade="all, delete-orphan")
    design_logs       = relationship("GoldsmithDesignLog", back_populates="goldsmith_batch", cascade="all, delete-orphan")
    polish_batches    = relationship("PolishBatch", back_populates="goldsmith_batch")


class GoldsmithWorkerLog(Base):
    """
    Per-worker per-day record within a goldsmith batch.
    Used for: daily chain count, weight handled, loss, pay calculation.

    Matches 1ST CLOSING section of GS-CLOSING sheet:
      FROM DATE | T DATE | DEBIT | CREDIT | WT LOSS | PCS | PPWL | ACT WL | EXTRA LOSS
    """
    __tablename__ = "goldsmith_worker_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    goldsmith_batch_id  = Column(Integer, ForeignKey("goldsmith_batches.id"), nullable=False)
    worker_id           = Column(Integer, ForeignKey("workers.id"), nullable=False)
    log_date            = Column(Date, nullable=False, index=True)
    from_date           = Column(Date)
    to_date             = Column(Date)
    debit_g             = Column(Float, default=0.0)     # gold given to worker
    credit_g            = Column(Float, default=0.0)     # gold returned by worker
    weight_loss_g       = Column(Float, default=0.0)     # loss = debit - credit
    pcs                 = Column(Integer, default=0)     # chains made this session
    ppwl                = Column(Float, default=0.0)     # per piece weight loss allowed
    act_wl              = Column(Float, default=0.0)     # actual weight loss per piece
    extra_loss_g        = Column(Float, default=0.0)     # extra_loss = actual - allowed
    pay_earned          = Column(Float, default=0.0)     # pcs × rate_per_chain
    daybook_sno         = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    goldsmith_batch = relationship("GoldsmithBatch", back_populates="worker_logs")
    worker          = relationship("Worker", back_populates="goldsmith_logs")


class GoldsmithDesignLog(Base):
    """
    Piece count by design type per worker per month.
    Matches GS-PCS sheet: GOLD SMITH DESIGN WISE PC REPORT.

    Seen designs: KCN, SEEMA, BABY, 4S, FS30, 30INC
    Seen workers: GS-MUSTHAFA (249 tot, 247 KCN), GS-CHANDRU (47 tot, 34 KCN) etc.
    """
    __tablename__ = "goldsmith_design_logs"

    id                 = Column(Integer, primary_key=True, index=True)
    goldsmith_batch_id = Column(Integer, ForeignKey("goldsmith_batches.id"), nullable=False)
    worker_id          = Column(Integer, ForeignKey("workers.id"), nullable=False)
    design_type_id     = Column(Integer, ForeignKey("design_types.id"), nullable=False)
    month_year         = Column(String(10), nullable=False, index=True)   # e.g. "Apr-26"
    from_date          = Column(Date)
    to_date            = Column(Date)
    pieces_count       = Column(Integer, default=0)
    created_at         = Column(DateTime, server_default=func.now())

    goldsmith_batch = relationship("GoldsmithBatch", back_populates="design_logs")


# ─── Polish ───────────────────────────────────────────────────────────────────

class PolishBatch(Base):
    """
    Polish process — no weight loss tracked (dirt/residue is not gold loss).
    Only chain counts recorded.
    No weight_in_g / weight_out_g / loss_g columns.
    """
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


# ─── Faceting ─────────────────────────────────────────────────────────────────

class FacetingBatch(Base):
    """
    Faceting process — 2-3 teams (FAC-MUMTAJ, FAC-ATHAUL, FAC-RAJDIP).
    Gold is issued via V ACCOUNT (seen in DAYBOOK).

    GS-CLOSING sheet — FACETING section:
      S.NO | FACETING | F DATE | T DATE | DEBIT | CREDIT | WL | F PCS | REE CU
      | ACT F PCS | ACT WL | EXTRA LOSS

    Seen values: FAC-MUMTAJ 5302.90 debit, 4580.41 credit, 286 pcs
                 FAC-ATHAUL 2562.52 debit, 2228.10 credit, 100 pcs
    """
    __tablename__ = "faceting_batches"

    id               = Column(Integer, primary_key=True, index=True)
    from_date        = Column(Date, nullable=False, index=True)
    to_date          = Column(Date, nullable=False, index=True)
    worker_id        = Column(Integer, ForeignKey("workers.id"))
    team_id          = Column(Integer, ForeignKey("teams.id"))
    polish_batch_id  = Column(Integer, ForeignKey("polish_batches.id"))
    weight_in_g      = Column(Float, nullable=False)    # DEBIT
    weight_out_g     = Column(Float, nullable=False)    # CREDIT
    weight_loss_g    = Column(Float, default=0.0)       # WL
    fin_pcs          = Column(Integer, default=0)       # F PCS (finished pieces)
    ree_cu           = Column(Integer, default=0)       # REE CU column in sheet
    act_fin_pcs      = Column(Integer, default=0)       # ACT F PCS
    act_wl           = Column(Float, default=0.0)       # actual weight loss
    extra_loss_g     = Column(Float, default=0.0)       # extra loss
    solder_weight_g  = Column(Float, default=0.0)
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    v_account_used   = Column(Boolean, default=True)    # gold via V ACCOUNT
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())

    polish_batch  = relationship("PolishBatch", back_populates="faceting_batches")
    kambi_batches = relationship("KambiBatch", back_populates="faceting_batch")


# ─── Kambi (Linking) ──────────────────────────────────────────────────────────

class KambiBatch(Base):
    """
    Kambi = linking process — chain body + hook are joined.
    Then goes to finished stock.

    Seen in DAYBOOK as 'KAMBI' ledger account:
      KAMBI / GOLD BOX     → drawing gold
      KAMBI / RETURN       → returning unused gold
      KAMBI / WEIGHT LOSS  → loss entry
      WEIGHT LOSS / KAMBI  → loss on the other side
      NG MELTING / KAMBI   → gold from melt going to kambi

    Also seen: KAMBI OB = Opening Balance (548.28g on 16-May-26)
    """
    __tablename__ = "kambi_batches"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_date          = Column(Date, nullable=False, index=True)
    worker_id           = Column(Integer, ForeignKey("workers.id"))
    faceting_batch_id   = Column(Integer, ForeignKey("faceting_batches.id"))
    weight_in_g         = Column(Float, nullable=False)
    weight_out_g        = Column(Float, nullable=False)
    loss_g              = Column(Float, default=0.0)    # computed
    gold_box_drawn_g    = Column(Float, default=0.0)    # drawn from gold box
    gold_returned_g     = Column(Float, default=0.0)    # returned to gold box
    chains_linked       = Column(Integer, default=0)
    hooks_used          = Column(Integer, default=0)
    solder_weight_g     = Column(Float, default=0.0)
    daybook_sno         = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes               = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    faceting_batch = relationship("FacetingBatch", back_populates="kambi_batches")
