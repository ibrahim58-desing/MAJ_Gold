"""Stock pages: Finished Stock, Tot Stock, Stock Summary."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QTabWidget, QFrame
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.stock_service import StockService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight
from config.settings import STOCK_CATEGORIES


# ─── Finished Stock ───────────────────────────────────────────────────────────
class FinishedStockPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []; self._all_rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("🏺  FINISHED STOCK")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        self._search = SearchBar("Search…"); self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._filter)
        filt = QComboBox(); filt.addItems(["All"] + STOCK_CATEGORIES)
        filt.setFixedWidth(160); filt.currentTextChanged.connect(self._load_filtered)
        self._cat_filter = filt
        add_btn = QPushButton("＋  Add Stock")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addWidget(self._search); bar.addWidget(filt); bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        cols = ["ID","Date","Category","Wt In (g)","Pcs In","Wt Balance","Pcs Balance","Location","Purity"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel(""); self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addWidget(self._cnt); act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(StockService.get_finished_stock)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _load_filtered(self, cat):
        self._overlay.show_over(self)
        cat_arg = None if cat == "All" else cat
        w = DBWorker(StockService.get_finished_stock, stock_category=cat_arg)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay(); self._items = items
        self._all_rows = [[i.id, fmt_date(i.stocked_date), i.stock_category,
                           fmt_weight(i.weight_in_g), i.pcs_in,
                           fmt_weight(i.weight_balance_g), i.pcs_balance,
                           i.location, i.purity] for i in items]
        self._table.populate(self._all_rows)
        self._cnt.setText(f"{len(items)} records")

    def _filter(self, text):
        t = text.lower()
        self._table.populate([r for r in self._all_rows if any(t in str(v).lower() for v in r)])

    def _add(self):
        dlg = FinishedStockDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: StockService.create_finished_stock(**dlg.get_data())).start()
            Toast.show_toast(self, "Stock added.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a row.", "warning")
        fid = int(self._table.item(row, 0).text())
        item = next((i for i in self._items if i.id == fid), None)
        if not item: return
        dlg = FinishedStockDialog(self, item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: StockService.update_finished_stock(fid, **dlg.get_data())).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        fid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this stock entry?"):
            DBWorker(lambda: StockService.delete_finished_stock(fid)).start(); self._load()


class FinishedStockDialog(QDialog):
    def __init__(self, parent, item=None):
        super().__init__(parent); self.setWindowTitle("Finished Stock")
        self.setFixedSize(420, 380); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(item.stocked_date), "yyyy-MM-dd") if item else QDate.currentDate())
        self._cat = QComboBox(); self._cat.addItems(STOCK_CATEGORIES)
        if item: self._cat.setCurrentText(item.stock_category)
        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(item.weight_in_g if item else 0)
        self._pcs_in = QSpinBox(); self._pcs_in.setRange(0, 999999)
        self._pcs_in.setValue(item.pcs_in if item else 0)
        self._wt_bal = QDoubleSpinBox(); self._wt_bal.setRange(0,999999); self._wt_bal.setDecimals(3)
        self._wt_bal.setValue(item.weight_balance_g if item else 0)
        self._pcs_bal = QSpinBox(); self._pcs_bal.setRange(0, 999999)
        self._pcs_bal.setValue(item.pcs_balance if item else 0)
        self._loc = QLineEdit(item.location if item else "MUM")
        self._purity = QComboBox(); self._purity.addItems(["916","999","995","22K"])
        if item: self._purity.setCurrentText(item.purity)
        self._notes = QLineEdit(item.notes or "" if item else "")
        for lbl, w in [("Date *", self._date), ("Category *", self._cat),
                        ("Wt In (g) *", self._wt_in), ("Pcs In", self._pcs_in),
                        ("Wt Balance (g)", self._wt_bal), ("Pcs Balance", self._pcs_bal),
                        ("Location", self._loc), ("Purity", self._purity), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"stocked_date": self._date.date().toPyDate(),
                "stock_category": self._cat.currentText(),
                "weight_in_g": self._wt_in.value(), "pcs_in": self._pcs_in.value(),
                "location": self._loc.text() or "MUM", "purity": self._purity.currentText(),
                "notes": self._notes.text() or None}


# ─── TOT STOCK ────────────────────────────────────────────────────────────────
class TotStockPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)
        title = QLabel("📊  TOT STOCK — Total Stock Register")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("BtnSecondary"); refresh_btn.clicked.connect(self._load)
        h = QHBoxLayout(); h.addStretch(); h.addWidget(refresh_btn)
        layout.addLayout(h)

        # Summary cards
        self._cards_layout = QHBoxLayout(); self._cards_layout.setSpacing(12)
        layout.addLayout(self._cards_layout)

        # Detail table
        self._table = DataTable(["Category", "Balance Weight (g)", "Balance Pcs"])
        layout.addWidget(self._table, 1)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(StockService.get_tot_stock_summary)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, cats):
        self._overlay.hide_overlay()
        # Clear old cards
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        COLORS = {"CHAIN_22K":"#F5A623","BOX_22K":"#2ED573","FACTORY_22K":"#1E90FF",
                  "999":"#A855F7","995":"#FF6B35","PURSE":"#E8C547"}
        total_wt = sum(c["weight"] for c in cats)
        total_pcs = sum(c["pcs"] for c in cats)
        for c in cats:
            frame = QFrame(); frame.setObjectName("Card")
            cv = QVBoxLayout(frame); cv.setContentsMargins(14,12,14,12); cv.setSpacing(4)
            color = COLORS.get(c["cat"], "#8A9BB5")
            wt_lbl = QLabel(f"{c['weight']:,.3f} g")
            wt_lbl.setStyleSheet(f"color:{color}; font-size:18px; font-weight:800;")
            cat_lbl = QLabel(c["cat"].replace("_"," "))
            cat_lbl.setStyleSheet("color:#8A9BB5; font-size:10px; font-weight:600; letter-spacing:1px;")
            pcs_lbl = QLabel(f"{c['pcs']} pcs")
            pcs_lbl.setStyleSheet("color:#4A5568; font-size:11px;")
            cv.addWidget(wt_lbl); cv.addWidget(cat_lbl); cv.addWidget(pcs_lbl)
            self._cards_layout.addWidget(frame)
        total_frame = QFrame(); total_frame.setObjectName("CardGold")
        tv = QVBoxLayout(total_frame); tv.setContentsMargins(14,12,14,12); tv.setSpacing(4)
        QLabel(f"{total_wt:,.3f} g").setParent(None)
        t1 = QLabel(f"{total_wt:,.3f} g"); t1.setStyleSheet("color:#F5A623;font-size:18px;font-weight:800;")
        t2 = QLabel("TOTAL"); t2.setStyleSheet("color:#8A9BB5;font-size:10px;font-weight:700;letter-spacing:1px;")
        t3 = QLabel(f"{total_pcs} pcs"); t3.setStyleSheet("color:#4A5568;font-size:11px;")
        tv.addWidget(t1); tv.addWidget(t2); tv.addWidget(t3)
        self._cards_layout.addWidget(total_frame)
        self._table.populate([[c["cat"], f"{c['weight']:,.3f}", c["pcs"]] for c in cats])


# ─── Stock Summary ────────────────────────────────────────────────────────────
class StockSummaryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)
        title = QLabel("📈  STOCK SUMMARY — Daily (STOCK_SUM)")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Record Summary")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        cols = ["ID","Date","GB Open","GB IN","GB OUT","GB Close","24K Open","24K IN","24K Close",
                "VA Open","VA IN","VA OUT","VA Close"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(StockService.get_stock_summary)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay()
        self._table.populate([[
            i.id, fmt_date(i.summary_date),
            fmt_weight(i.gb_opening_g), fmt_weight(i.gb_in_g),
            fmt_weight(i.gb_out_g), fmt_weight(i.gb_closing_g),
            fmt_weight(i.gold_opening_g), fmt_weight(i.gold_in_g), fmt_weight(i.gold_closing_g),
            fmt_weight(i.va_opening_g), fmt_weight(i.va_in_g),
            fmt_weight(i.va_out_g), fmt_weight(i.va_closing_g)] for i in items])

    def _add(self):
        dlg = StockSummaryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: StockService.upsert_stock_summary(**dlg.get_data())).start()
            Toast.show_toast(self, "Summary saved.", "success"); self._load()


class StockSummaryDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("Stock Summary")
        self.setFixedSize(460, 560); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(8)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        def spin(): s = QDoubleSpinBox(); s.setRange(-999999,999999); s.setDecimals(3); return s
        self._gb_open = spin(); self._gb_in = spin(); self._gb_out = spin(); self._gb_close = spin()
        self._gold_open = spin(); self._gold_in = spin(); self._gold_out = spin()
        self._va_open = spin(); self._va_in = spin(); self._va_out = spin()
        fields = [("Date", self._date), ("GB Opening (g)", self._gb_open), ("GB IN (g)", self._gb_in),
                  ("GB OUT (g)", self._gb_out), ("GB Closing (g)", self._gb_close),
                  ("24K Opening (g)", self._gold_open), ("24K IN (g)", self._gold_in),
                  ("24K OUT (g)", self._gold_out),
                  ("VA Opening (g)", self._va_open), ("VA IN (g)", self._va_in), ("VA OUT (g)", self._va_out)]
        for lbl, w in fields:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"summary_date": self._date.date().toPyDate(),
                "gb_opening_g": self._gb_open.value(), "gb_in_g": self._gb_in.value(),
                "gb_out_g": self._gb_out.value(),
                "gb_closing_g": self._gb_open.value() + self._gb_in.value() - self._gb_out.value(),
                "gold_opening_g": self._gold_open.value(), "gold_in_g": self._gold_in.value(),
                "gold_out_g": self._gold_out.value(),
                "gold_closing_g": self._gold_open.value() + self._gold_in.value() - self._gold_out.value(),
                "va_opening_g": self._va_open.value(), "va_in_g": self._va_in.value(),
                "va_out_g": self._va_out.value(),
                "va_closing_g": self._va_open.value() + self._va_in.value() - self._va_out.value()}
