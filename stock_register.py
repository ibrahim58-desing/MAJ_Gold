"""
Stock Register models — matches TOT STOCK and STOCK_SUM sheets.

TOT STOCK sheet (TOTAL STOCK REGISTER):
  Columns: DATE | PARTICULAR | DEBIT | CREDIT | TAG NO | BALANCE | MUM(location)
  Summary header: TOTAL | CHAIN 22K | BOX 22K | FACTORY 22K | 999 | 995 | PURSE

  Balance row: 8431.05 total
  Tag Wgt row: -8383.71 total (weight of tagged/sold items)
  Breakdown: CHAIN 22K: 1851.61 | BOX 22K: 535.01 | FACTORY 22K: 5996.04 | 999: 1.05 | 995: 1.00

CHAIN STOCK — seen in LEDGER as 'CHAIN STOCK' with credit entries (440.73 | 25 pcs, 825.11 | 66 pcs)
  These are finished chains going into stock.

TAG STOCK — tagged items ready for sale/dispatch (TAG NO 11, MUM location)
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class FinishedStock(Base):
    """
    Finished jewellery items entering the stock.
    Source: KambiBatch or direct goldsmith output.
    Stock categories match TOT STOCK summary header:
      CHAIN 22K, BOX 22K, FACTORY 22K, 999, 995, PURSE
    """
    __tablename__ = "finished_stock"

    id               = Column(Integer, primary_key=True, index=True)
    stocked_date     = Column(Date, nullable=False, index=True)
    kambi_batch_id   = Column(Integer, ForeignKey("kambi_batches.id"), nullable=True)
    stock_category   = Column(String(30), nullable=False)
    # CHAIN_22K / BOX_22K / FACTORY_22K / 999 / 995 / PURSE
    product_type_id  = Column(Integer, ForeignKey("product_types.id"))
    design_type_id   = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    pcs_in           = Column(Integer, default=0)
    weight_in_g      = Column(Float, default=0.0)
    pcs_out          = Column(Integer, default=0)      # sold/dispatched
    weight_out_g     = Column(Float, default=0.0)
    pcs_balance      = Column(Integer, default=0)      # running balance pcs
    weight_balance_g = Column(Float, default=0.0)      # running balance weight
    location         = Column(String(20), default="MUM")  # MUM = Mumbai (seen in sheet)
    purity           = Column(String(10), default="916")
    barcode          = Column(String(50), unique=True, nullable=True)
    daybook_sno      = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes            = Column(Text)
    created_at       = Column(DateTime, server_default=func.now())


class ChainStock(Base):
    """
    Chain-specific stock ledger.
    Seen in LEDGER as 'CHAIN STOCK' entries with pcs column.
    E.g. 14-May-26: CHAIN STOCK credit 440.73 | 25 pcs
         01-Jun-24: CHAIN STOCK credit 801.13 | 21 pcs
                    CHAIN STOCK credit  32.13 |  1 pcs
    """
    __tablename__ = "chain_stock"

    id              = Column(Integer, primary_key=True, index=True)
    entry_date      = Column(Date, nullable=False, index=True)
    design_type_id  = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"))
    weight_g        = Column(Float, nullable=False)
    pcs             = Column(Integer, default=0)
    transaction     = Column(String(10), default="CREDIT")  # CREDIT = in, DEBIT = out
    reference       = Column(String(50))   # source batch or sale ref
    daybook_sno     = Column(Integer, ForeignKey("daybook_entries.serial_no"))
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())


class TagStock(Base):
    """
    Tagged items ready for sale — matched to TAG NO in TOT STOCK sheet.
    TAG NO 11 seen with MUM location, TAG WGT = 14.92g.
    Negative values in CHAIN 22K / BOX 22K / FACTORY 22K columns
    indicate weight tagged/committed = deducted from available stock.
    """
    __tablename__ = "tag_stock"

    id              = Column(Integer, primary_key=True, index=True)
    tag_no          = Column(Integer, nullable=False, index=True)    # TAG NO 11
    tag_date        = Column(Date, nullable=False)
    location        = Column(String(20))                             # MUM
    stock_category  = Column(String(30))                             # CHAIN_22K etc
    product_type_id = Column(Integer, ForeignKey("product_types.id"))
    design_type_id  = Column(Integer, ForeignKey("design_types.id"), nullable=True)
    tagged_weight_g = Column(Float, nullable=False)
    tagged_pcs      = Column(Integer, default=0)
    status          = Column(String(20), default="TAGGED")
    # TAGGED / SOLD / RETURNED
    sale_date       = Column(Date, nullable=True)
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())


class StockSummaryDaily(Base):
    """
    Daily stock summary — mirrors STOCK_SUM sheet.
    Tracks three sections: GOLD BOX, 24K GOLD, V ACCOUNT.
    Each has: OPENING | IN | OUT | CLOSING | PHYSICAL | DIF SYS | PHY DIF

    24K GOLD section shows negative closing (system tracks as liability).
    V ACCOUNT = virtual account for gold issued to faceting workers.
    """
    __tablename__ = "stock_summary_daily"

    id                    = Column(Integer, primary_key=True, index=True)
    summary_date          = Column(Date, nullable=False, unique=True, index=True)

    # GOLD BOX section
    gb_opening_g          = Column(Float, default=0.0)
    gb_in_g               = Column(Float, default=0.0)
    gb_out_g              = Column(Float, default=0.0)
    gb_closing_g          = Column(Float, default=0.0)
    gb_physical_g         = Column(Float, nullable=True)
    gb_sys_diff_g         = Column(Float, nullable=True)
    gb_phy_diff_g         = Column(Float, nullable=True)

    # 24K GOLD section (raw gold in system)
    gold_opening_g        = Column(Float, default=0.0)
    gold_in_g             = Column(Float, default=0.0)
    gold_out_g            = Column(Float, default=0.0)
    gold_closing_g        = Column(Float, default=0.0)
    gold_physical_g       = Column(Float, nullable=True)

    # V ACCOUNT section (gold with faceting workers)
    va_opening_g          = Column(Float, default=0.0)
    va_in_g               = Column(Float, default=0.0)
    va_out_g              = Column(Float, default=0.0)
    va_closing_g          = Column(Float, default=0.0)
    va_physical_g         = Column(Float, nullable=True)
    va_sys_diff_g         = Column(Float, nullable=True)

    notes                 = Column(Text)
    updated_at            = Column(DateTime, server_default=func.now(), onupdate=func.now())
