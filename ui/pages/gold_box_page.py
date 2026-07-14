"""Gold Box page — stock IN, issues OUT, and daily balance."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QTabWidget, QLineEdit, QFrame
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.gold_box_service import GoldBoxService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight


class GoldBoxPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("📦  GOLD BOX")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        # Balance card
        self._balance_lbl = QLabel("Current Balance: — g")
        self._balance_lbl.setStyleSheet(
            "color:#F5A623; font-size:18px; font-weight:800; "
            "background:rgba(245,166,35,0.1); border:1px solid rgba(245,166,35,0.3); "
            "border-radius:8px; padding:10px 20px;")
        layout.addWidget(self._balance_lbl)

        tabs = QTabWidget()
        self._stock_tab = StockInTab(self._workers)
        self._issue_tab = IssueOutTab(self._workers)
        self._balance_tab = DailyBalanceTab()
        tabs.addTab(self._stock_tab, "📥  Stock IN")
        tabs.addTab(self._issue_tab, "📤  Issues OUT")
        tabs.addTab(self._balance_tab, "📊  Daily Balance")
        layout.addWidget(tabs)

        w = DBWorker(MasterService.get_workers)
        w.result.connect(self._on_workers)
        w.start()
        self._load_balance()

    def _on_workers(self, workers):
        self._workers = workers
        self._stock_tab.set_workers(workers)
        self._issue_tab.set_workers(workers)

    def _load_balance(self):
        w = DBWorker(GoldBoxService.get_current_balance)
        w.result.connect(lambda v: self._balance_lbl.setText(f"Current Balance: {v:,.3f} g"))
        w.start()

    def refresh(self):
        self._load_balance()
        self._stock_tab._load()
        self._issue_tab._load()
        self._balance_tab._load()


class StockInTab(QWidget):
    SOURCES = ["MELT_BATCH", "SOLDER_RETURN", "OPENING_BALANCE", "OTHER"]

    def __init__(self, workers):
        super().__init__()
        self._all_rows = []; self._items = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Add Stock IN")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID", "Date", "Source", "Weight Added (g)", "Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self)
        self._load()

    def set_workers(self, workers): self._workers = workers

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(GoldBoxService.get_stock_entries)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay(); self._items = items
        self._table.populate([[i.id, fmt_date(i.added_date), i.source,
                               fmt_weight(i.weight_added_g), i.notes or ""] for i in items])

    def _add(self):
        dlg = StockInDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: GoldBoxService.add_stock(**d)).start()
            Toast.show_toast(self, "Stock IN added.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a row.", "warning")
        sid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this stock entry?"):
            DBWorker(lambda: GoldBoxService.delete_stock(sid)).start()
            self._load()


class StockInDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("Add Stock IN")
        self.setFixedSize(360, 260); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._source = QComboBox()
        self._source.addItems(["MELT_BATCH", "SOLDER_RETURN", "OPENING_BALANCE", "OTHER"])
        self._wt = QDoubleSpinBox(); self._wt.setRange(0.001, 99999); self._wt.setDecimals(3)
        self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("Source *", self._source),
                        ("Weight (g) *", self._wt), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"added_date": self._date.date().toPyDate(), "source": self._source.currentText(),
                "weight_added_g": self._wt.value(), "notes": self._notes.text() or None}


class IssueOutTab(QWidget):
    def __init__(self, workers):
        super().__init__()
        self._workers = workers; self._items = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Add Issue OUT")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID", "Date", "Worker", "Process", "Issued (g)",
                                  "Returned (g)", "Net Used (g)", "Pcs"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self)
        self._load()

    def set_workers(self, workers): self._workers = workers

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(GoldBoxService.get_issues)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay(); self._items = items
        self._table.populate([[
            i.id, fmt_date(i.issued_date), i.worker.name if i.worker else "—",
            i.process, fmt_weight(i.weight_issued_g), fmt_weight(i.weight_returned_g),
            fmt_weight(i.net_used_g), i.pcs_issued] for i in items])

    def _add(self):
        dlg = IssueOutDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: GoldBoxService.create_issue(**dlg.get_data())).start()
            Toast.show_toast(self, "Issue OUT recorded.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a row.", "warning")
        iid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this issue?"):
            DBWorker(lambda: GoldBoxService.delete_issue(iid)).start(); self._load()


class IssueOutDialog(QDialog):
    PROCESSES = ["WIRE_SHEET", "GOLDSMITH", "FACETING", "KAMBI", "HALLMARKING", "OTHER"]

    def __init__(self, parent, workers):
        super().__init__(parent); self.setWindowTitle("Issue Gold OUT")
        self.setFixedSize(400, 360); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._worker = QComboBox()
        self._worker_ids = [w.id for w in workers]
        self._worker.addItems([f"{w.code} — {w.name}" for w in workers])
        self._process = QComboBox(); self._process.addItems(self.PROCESSES)
        self._issued = QDoubleSpinBox(); self._issued.setRange(0.001, 99999); self._issued.setDecimals(3)
        self._returned = QDoubleSpinBox(); self._returned.setRange(0, 99999); self._returned.setDecimals(3)
        self._pcs = QSpinBox(); self._pcs.setRange(0, 999999)
        self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("Worker *", self._worker),
                        ("Process *", self._process), ("Issued (g) *", self._issued),
                        ("Returned (g)", self._returned), ("Pcs Issued", self._pcs), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "issued_date": self._date.date().toPyDate(),
            "worker_id": self._worker_ids[self._worker.currentIndex()] if self._worker_ids else None,
            "process": self._process.currentText(),
            "weight_issued_g": self._issued.value(),
            "weight_returned_g": self._returned.value(),
            "pcs_issued": self._pcs.value(),
            "notes": self._notes.text() or None,
        }


class DailyBalanceTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Record Balance")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID", "Date", "Opening (g)", "IN (g)", "OUT (g)",
                                  "Closing (g)", "Physical (g)", "Sys Diff"])
        layout.addWidget(self._table, 1)
        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(GoldBoxService.get_daily_balances)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay()
        self._table.populate([[
            i.id, fmt_date(i.balance_date), fmt_weight(i.opening_g), fmt_weight(i.total_in_g),
            fmt_weight(i.total_out_g), fmt_weight(i.closing_g),
            fmt_weight(i.physical_g) if i.physical_g else "—",
            fmt_weight(i.system_diff_g) if i.system_diff_g else "—"] for i in items])

    def _add(self):
        dlg = DailyBalanceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: GoldBoxService.upsert_daily_balance(**d)).start()
            Toast.show_toast(self, "Balance recorded.", "success"); self._load()


class DailyBalanceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("Daily Balance")
        self.setFixedSize(380, 320); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._opening = QDoubleSpinBox(); self._opening.setRange(0,999999); self._opening.setDecimals(3)
        self._in = QDoubleSpinBox(); self._in.setRange(0,999999); self._in.setDecimals(3)
        self._out = QDoubleSpinBox(); self._out.setRange(0,999999); self._out.setDecimals(3)
        self._physical = QDoubleSpinBox(); self._physical.setRange(0,999999); self._physical.setDecimals(3)
        self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("Opening (g)", self._opening),
                        ("Total IN (g)", self._in), ("Total OUT (g)", self._out),
                        ("Physical (g)", self._physical), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "balance_date": self._date.date().toPyDate(),
            "opening_g": self._opening.value(), "total_in_g": self._in.value(),
            "total_out_g": self._out.value(),
            "physical_g": self._physical.value() if self._physical.value() > 0 else None,
            "notes": self._notes.text() or None,
        }
