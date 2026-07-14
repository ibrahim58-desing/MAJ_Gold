"""Main Window — sidebar + stacked pages + header."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from datetime import date, datetime

from ui.widgets.sidebar import Sidebar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.masters_page import MastersPage
from ui.pages.daybook_page import DaybookPage
from ui.pages.gold_receipt_page import GoldReceiptPage
from ui.pages.melt_page import MeltPage
from ui.pages.gold_box_page import GoldBoxPage
from ui.goldsmith_ui import GoldsmithUI
from ui.pages.stock_pages import FinishedStockPage, TotStockPage, StockSummaryPage
from ui.pages.ledger_page import LedgerPage
from ui.pages.v_account_page import VAccountPage
from ui.pages.gs_pcs_page import GSPCSPage
from ui.pages.process_pages import FacetingPage
from ui.polish_ui import PolishUI
from ui.wire_sheet_ui import WireSheetUI
from config.settings import WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT


PAGE_MAP = {
    "dashboard":     DashboardPage,
    "masters":       MastersPage,
    "daybook":       DaybookPage,
    "gold_receipt":  GoldReceiptPage,
    "melt":          MeltPage,
    "gold_box":      GoldBoxPage,
    "wire_sheet":    WireSheetUI,
    "goldsmith":     GoldsmithUI,
    "polish":        PolishUI,
    "faceting":      FacetingPage,
    "finished_stock":FinishedStockPage,
    "tot_stock":     TotStockPage,
    "stock_summary": StockSummaryPage,
    "ledger":        LedgerPage,
    "v_account":     VAccountPage,
    "gs_pcs":        GSPCSPage,
}

PAGE_TITLES = {
    "dashboard":     ("Dashboard", "Overview & KPIs"),
    "masters":       ("Masters", "Dealers · Workers · Teams · Types"),
    "daybook":       ("Daybook", "Inventory Day Book — Double Entry Ledger"),
    "gold_receipt":  ("Gold Receipts", "Raw gold received from dealers"),
    "melt":          ("Melt Batches", "NG Melting & Scrap Melting"),
    "gold_box":      ("Gold Box", "Physical gold storage — Stock & Issues"),
    "wire_sheet":    ("Wire & Sheet", "Wire drawing & sheet rolling batches"),
    "goldsmith":     ("Goldsmith", "Issue gold, track returns, team management"),
    "polish":        ("Polish", "Isolated Polish Loss tracking"),
    "faceting":      ("Faceting", "Faceting batches — V Account linked"),
    "finished_stock":("Finished Stock", "Jewellery stock register"),
    "tot_stock":     ("Tot Stock", "Total Stock Register — CHAIN / BOX / FACTORY"),
    "stock_summary": ("Stock Summary", "STOCK_SUM — Gold Box · 24K · V Account"),
    "ledger":        ("Ledger", "Account-wise running ledger"),
    "v_account":     ("V Account", "Virtual account — faceting gold tracking"),
    "gs_pcs":        ("GS-PCS Report", "Design-wise piece count per worker"),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.showMaximized()
        self._page_cache = {}
        self._setup_ui()
        self._navigate("dashboard")

    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._navigate)
        main_layout.addWidget(self._sidebar)

        # ── Content area ──────────────────────────────────────────────────────
        content_col = QVBoxLayout()
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)

        # Header bar
        self._header = self._build_header()
        content_col.addWidget(self._header)

        # Page stack
        self._stack = QStackedWidget()
        content_col.addWidget(self._stack, 1)

        content_widget = QWidget()
        content_widget.setLayout(content_col)
        main_layout.addWidget(content_widget, 1)

        # Live clock
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(60000)
        self._update_clock()

    def _build_header(self):
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(56)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self._title_lbl = QLabel("Dashboard")
        self._title_lbl.setObjectName("PageTitle")
        self._subtitle_lbl = QLabel("Overview & KPIs")
        self._subtitle_lbl.setObjectName("PageSubtitle")

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#1E2640;")
        sep.setFixedWidth(1)

        self._clock_lbl = QLabel()
        self._clock_lbl.setObjectName("HeaderDate")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._title_lbl)
        layout.addWidget(sep)
        layout.addWidget(self._subtitle_lbl)
        layout.addStretch()
        layout.addWidget(self._clock_lbl)
        return header

    def _navigate(self, key: str):
        if key not in PAGE_MAP:
            return

        # Lazy-load pages
        is_revisit = key in self._page_cache
        if not is_revisit:
            page = PAGE_MAP[key]()
            self._page_cache[key] = page
            self._stack.addWidget(page)

        page = self._page_cache[key]
        if is_revisit and hasattr(page, "refresh"):
            # Cached pages don't re-fetch on their own; other pages may have
            # changed shared data (Gold Box, V Account, etc.) since we left.
            page.refresh()

        self._stack.setCurrentWidget(page)
        self._sidebar.set_active(key)

        title, subtitle = PAGE_TITLES.get(key, (key.replace("_", " ").title(), ""))
        self._title_lbl.setText(title)
        self._subtitle_lbl.setText(subtitle)

    def _update_clock(self):
        now = datetime.now()
        self._clock_lbl.setText(
            f"{now.strftime('%a, %d %b %Y')}  ·  {now.strftime('%H:%M')}"
        )
