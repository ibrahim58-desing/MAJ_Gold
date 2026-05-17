"""V Account page — virtual account entries for faceting workers."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QFrame, QTabWidget
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.v_account_service import VAccountService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight


class VAccountPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        title = QLabel("🔐  V ACCOUNT — Virtual Account")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        info = QLabel("V Account tracks gold with faceting workers. Debit = issued, Credit = returned/finished.")
        info.setStyleSheet("color:#4A5568; font-size:12px; font-style:italic;")
        layout.addWidget(info)

        # Summary card
        sf = QFrame(); sf.setObjectName("Card")
        sv = QHBoxLayout(sf); sv.setContentsMargins(16,10,16,10); sv.setSpacing(32)
        self._dr_lbl = QLabel("DR: —")
        self._dr_lbl.setStyleSheet("color:#FF4757;font-size:15px;font-weight:700;")
        self._cr_lbl = QLabel("CR: —")
        self._cr_lbl.setStyleSheet("color:#2ED573;font-size:15px;font-weight:700;")
        self._bal_lbl = QLabel("BAL: —")
        self._bal_lbl.setStyleSheet("color:#F5A623;font-size:15px;font-weight:700;")
        self._pcs_lbl = QLabel("PCS: —")
        self._pcs_lbl.setStyleSheet("color:#8A9BB5;font-size:13px;font-weight:600;")
        sv.addWidget(self._dr_lbl); sv.addWidget(self._cr_lbl)
        sv.addWidget(self._bal_lbl); sv.addWidget(self._pcs_lbl); sv.addStretch()
        layout.addWidget(sf)

        tabs = QTabWidget()
        self._entries_tab = VEntriesTab()
        self._balance_tab = VBalanceTab()
        tabs.addTab(self._entries_tab, "📋  Entries")
        tabs.addTab(self._balance_tab, "📊  Daily Balance")
        layout.addWidget(tabs)

        DBWorker(MasterService.get_workers).result.connect(self._on_workers)
        DBWorker(MasterService.get_workers).start()
        self._load_totals()

    def _on_workers(self, workers):
        self._workers = workers
        self._entries_tab.set_workers(workers)

    def _load_totals(self):
        w = DBWorker(VAccountService.get_totals)
        w.result.connect(self._on_totals); w.start()

    def _on_totals(self, t):
        self._dr_lbl.setText(f"DR: {t['total_dr']:,.3f} g")
        self._cr_lbl.setText(f"CR: {t['total_cr']:,.3f} g")
        self._bal_lbl.setText(f"BAL: {t['balance']:,.3f} g")
        self._pcs_lbl.setText(f"PCS DR:{t['total_dr_pcs']} CR:{t['total_cr_pcs']}")


class VEntriesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []; self._entries = []
        layout = QVBoxLayout(self); layout.setContentsMargins(10,10,10,10); layout.setSpacing(10)
        bar = QHBoxLayout()
        wf = QComboBox(); wf.addItem("All Workers"); wf.setFixedWidth(200)
        wf.currentIndexChanged.connect(self._filter_worker); self._wf = wf
        add_btn = QPushButton("＋  Add Entry"); add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(wf); bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)
        cols = ["ID","Date","Worker","Particular","Debit (g)","Dr Pcs","Credit (g)","Cr Pcs","Balance"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)
        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger")
        del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self); self._load()

    def set_workers(self, workers):
        self._workers = workers
        self._wf.blockSignals(True)
        self._wf.clear(); self._wf.addItem("All Workers")
        self._wf.addItems([f"{w.code} — {w.name}" for w in workers])
        self._wf.blockSignals(False)

    def _load(self, worker_id=None):
        self._overlay.show_over(self)
        w = DBWorker(VAccountService.get_entries, worker_id=worker_id)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _filter_worker(self, idx):
        wid = self._workers[idx-1].id if idx > 0 else None
        self._load(wid)

    def _on_data(self, entries):
        self._overlay.hide_overlay(); self._entries = entries
        self._table.populate([[
            e.id, fmt_date(e.entry_date), e.worker.name if e.worker else "—",
            e.particular, f"{e.debit_g:.3f}" if e.debit_g else "—",
            e.debit_pcs or "—", f"{e.credit_g:.3f}" if e.credit_g else "—",
            e.credit_pcs or "—", f"{e.balance_g:.3f}"] for e in entries])

    def _add(self):
        prev = float(self._entries[-1].balance_g) if self._entries else 0.0
        dlg = VEntryDialog(self, self._workers, prev)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: VAccountService.create_entry(**dlg.get_data())).start()
            Toast.show_toast(self, "Entry added.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select an entry.", "warning")
        eid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this V Account entry?"):
            DBWorker(lambda: VAccountService.delete_entry(eid)).start(); self._load()


class VEntryDialog(QDialog):
    def __init__(self, parent, workers, prev_balance):
        super().__init__(parent); self.setWindowTitle("V Account Entry")
        self.setFixedSize(380, 340); self.setModal(True)
        self._prev = prev_balance
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._worker = QComboBox()
        self._worker_ids = [w.id for w in workers]
        self._worker.addItems([f"{w.code} — {w.name}" for w in workers])
        self._particular = QLineEdit()
        self._debit = QDoubleSpinBox(); self._debit.setRange(0,999999); self._debit.setDecimals(3)
        self._dr_pcs = QSpinBox(); self._dr_pcs.setRange(0,999999)
        self._credit = QDoubleSpinBox(); self._credit.setRange(0,999999); self._credit.setDecimals(3)
        self._cr_pcs = QSpinBox(); self._cr_pcs.setRange(0,999999)
        self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("Worker *", self._worker),
                        ("Particular *", self._particular), ("Debit (g)", self._debit),
                        ("Dr Pcs", self._dr_pcs), ("Credit (g)", self._credit),
                        ("Cr Pcs", self._cr_pcs), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def get_data(self):
        return {"entry_date": self._date.date().toPyDate(),
                "worker_id": self._worker_ids[self._worker.currentIndex()] if self._worker_ids else None,
                "particular": self._particular.text().strip(),
                "debit_g": self._debit.value(), "debit_pcs": self._dr_pcs.value(),
                "credit_g": self._credit.value(), "credit_pcs": self._cr_pcs.value(),
                "prev_balance": self._prev, "notes": self._notes.text() or None}


class VBalanceTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self); layout.setContentsMargins(10,10,10,10); layout.setSpacing(10)
        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Record Balance"); add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)
        self._table = DataTable(["ID","Date","Opening","IN","OUT","Closing","Physical","Sys Diff"])
        layout.addWidget(self._table, 1)
        self._overlay = LoadingOverlay(self); self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(VAccountService.get_daily_balances)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, items):
        self._overlay.hide_overlay()
        self._table.populate([[i.id, fmt_date(i.balance_date),
                               f"{i.opening_g:.3f}", f"{i.total_in_g:.3f}",
                               f"{i.total_out_g:.3f}", f"{i.closing_g:.3f}",
                               f"{i.physical_g:.3f}" if i.physical_g else "—",
                               f"{i.sys_diff_g:.3f}" if i.sys_diff_g else "—"] for i in items])

    def _add(self):
        dlg = VBalanceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: VAccountService.upsert_daily_balance(**dlg.get_data())).start()
            Toast.show_toast(self, "Balance saved.", "success"); self._load()


class VBalanceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("V Account Daily Balance")
        self.setFixedSize(360, 300); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        def sp(): s = QDoubleSpinBox(); s.setRange(0,999999); s.setDecimals(3); return s
        self._open = sp(); self._in = sp(); self._out = sp(); self._phy = sp()
        for lbl, w in [("Date *", self._date), ("Opening (g)", self._open),
                        ("IN (g)", self._in), ("OUT (g)", self._out), ("Physical (g)", self._phy)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def get_data(self):
        return {"balance_date": self._date.date().toPyDate(),
                "opening_g": self._open.value(), "total_in_g": self._in.value(),
                "total_out_g": self._out.value(),
                "physical_g": self._phy.value() if self._phy.value() > 0 else None}
