"""Dashboard Page — KPI cards, stock summary, daily activity."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.widgets.widgets import StatCard, Toast, LoadingOverlay
from workers.db_worker import DBWorker
from services.dashboard_service import DashboardService
from utils.formatters import fmt_weight, fmt_date
from datetime import date


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ── Page header ──────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("DASHBOARD")
        title.setObjectName("SectionTitle")
        title.setStyleSheet("font-size:22px; font-weight:800; color:#F5A623; letter-spacing:2px;")
        self._date_lbl = QLabel(fmt_date(date.today()))
        self._date_lbl.setStyleSheet("color:#4A5568; font-size:13px;")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self._date_lbl)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("BtnSecondary")
        refresh_btn.clicked.connect(self._load)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        # ── KPI cards row ─────────────────────────────────────────────────────
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        self._cards = {}
        card_defs = [
            ("gold_box",     "Gold Box Balance", "0.000 g", "📦", "#F5A623", True),
            ("stock_wt",     "Finished Stock",   "0.000 g", "🏺", "#2ED573", False),
            ("stock_pcs",    "Stock Pieces",     "0",       "💎", "#1E90FF", False),
            ("workers",      "Active Workers",   "0",       "👷", "#A855F7", False),
            ("melt",         "Melt Batches",     "0",       "🔥", "#FF6B35", False),
            ("today",        "Today's Entries",  "0",       "📋", "#E8C547", False),
        ]
        for idx, (key, lbl, val, icon, color, accent) in enumerate(card_defs):
            card = StatCard(lbl, val, icon, color, accent)
            self._cards[key] = card
            kpi_grid.addWidget(card, idx // 3, idx % 3)

        root.addLayout(kpi_grid)

        # ── Two-column layout ─────────────────────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(16)

        # Stock by category
        cat_frame = QFrame()
        cat_frame.setObjectName("Card")
        cat_layout = QVBoxLayout(cat_frame)
        cat_layout.setContentsMargins(16, 14, 16, 14)
        cat_layout.setSpacing(10)

        cat_title = QLabel("STOCK BY CATEGORY")
        cat_title.setStyleSheet("color:#F5A623; font-size:11px; font-weight:700; letter-spacing:1px;")
        cat_layout.addWidget(cat_title)

        self._cat_layout = QVBoxLayout()
        self._cat_layout.setSpacing(6)
        cat_layout.addLayout(self._cat_layout)
        cat_layout.addStretch()
        cols.addWidget(cat_frame, 1)

        # Recent activity
        act_frame = QFrame()
        act_frame.setObjectName("Card")
        act_layout = QVBoxLayout(act_frame)
        act_layout.setContentsMargins(16, 14, 16, 14)
        act_layout.setSpacing(10)

        act_title = QLabel("7-DAY DAYBOOK ACTIVITY")
        act_title.setStyleSheet("color:#F5A623; font-size:11px; font-weight:700; letter-spacing:1px;")
        act_layout.addWidget(act_title)

        self._act_layout = QVBoxLayout()
        self._act_layout.setSpacing(4)
        act_layout.addLayout(self._act_layout)
        act_layout.addStretch()
        cols.addWidget(act_frame, 1)

        root.addLayout(cols)

        # Process summary row
        proc_frame = QFrame()
        proc_frame.setObjectName("Card")
        proc_layout = QVBoxLayout(proc_frame)
        proc_layout.setContentsMargins(16, 14, 16, 14)
        proc_title = QLabel("PROCESS SUMMARY")
        proc_title.setStyleSheet("color:#F5A623; font-size:11px; font-weight:700; letter-spacing:1px;")
        proc_layout.addWidget(proc_title)
        self._proc_row = QHBoxLayout()
        self._proc_row.setSpacing(24)
        proc_layout.addLayout(self._proc_row)
        root.addWidget(proc_frame)

        root.addStretch()

        # Loading overlay
        self._overlay = LoadingOverlay(self)

    def _load(self):
        self._overlay.show_over(self)
        self._worker = DBWorker(DashboardService.get_kpis)
        self._worker.result.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_data(self, data: dict):
        self._overlay.hide_overlay()

        self._cards["gold_box"].set_value(fmt_weight(data["gold_box_balance"]))
        self._cards["stock_wt"].set_value(fmt_weight(data["finished_stock_wt"]))
        self._cards["stock_pcs"].set_value(str(data["finished_stock_pcs"]))
        self._cards["workers"].set_value(str(data["active_workers"]))
        self._cards["melt"].set_value(str(data["melt_count"]))
        self._cards["today"].set_value(str(data["today_entries"]))

        # Category breakdown
        while self._cat_layout.count():
            item = self._cat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        COLORS = {"CHAIN_22K": "#F5A623", "BOX_22K": "#2ED573",
                  "FACTORY_22K": "#1E90FF", "999": "#A855F7",
                  "995": "#FF6B35", "PURSE": "#E8C547"}

        for c in data.get("categories", []):
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{COLORS.get(c['cat'], '#8A9BB5')}; font-size:10px;")
            dot.setFixedWidth(16)
            lbl = QLabel(c["cat"].replace("_", " "))
            lbl.setStyleSheet("color:#D0D8F0; font-size:12px;")
            wt = QLabel(fmt_weight(c["wt"]))
            wt.setStyleSheet("color:#8A9BB5; font-size:12px;")
            pcs = QLabel(f"{c['pcs']} pcs")
            pcs.setStyleSheet("color:#4A5568; font-size:11px;")
            row.addWidget(dot)
            row.addWidget(lbl, 1)
            row.addWidget(wt)
            row.addWidget(pcs)
            w = QWidget()
            w.setLayout(row)
            self._cat_layout.addWidget(w)

        # Daily activity
        while self._act_layout.count():
            item = self._act_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for a in data.get("daily_activity", []):
            row = QHBoxLayout()
            d_lbl = QLabel(a["date"])
            d_lbl.setStyleSheet("color:#8A9BB5; font-size:12px; min-width:90px;")
            cnt = QLabel(f"{a['count']} entries")
            cnt.setStyleSheet("color:#F0F4FF; font-size:12px;")
            wt = QLabel(fmt_weight(a["debit"]))
            wt.setStyleSheet("color:#F5A623; font-size:12px;")
            row.addWidget(d_lbl)
            row.addWidget(cnt, 1)
            row.addWidget(wt)
            w = QWidget(); w.setLayout(row)
            self._act_layout.addWidget(w)

        # Process summary
        while self._proc_row.count():
            item = self._proc_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for label, key in [("Melt", "melt_count"), ("Goldsmith", "gs_count"),
                            ("Faceting", "fac_count"), ("Kambi", "kambi_count")]:
            col = QVBoxLayout()
            v = QLabel(str(data.get(key, 0)))
            v.setStyleSheet("color:#F5A623; font-size:22px; font-weight:800;")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l = QLabel(label.upper())
            l.setStyleSheet("color:#4A5568; font-size:10px; letter-spacing:1px;")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(v)
            col.addWidget(l)
            w = QWidget(); w.setLayout(col)
            self._proc_row.addWidget(w)
        self._proc_row.addStretch()

    def _on_error(self, msg: str):
        self._overlay.hide_overlay()
        Toast.show_toast(self, f"Error loading dashboard: {msg}", "error")
