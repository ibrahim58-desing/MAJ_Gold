"""Ledger page — per-account running ledger entries."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QFrame
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.ledger_service import LedgerService
from utils.formatters import fmt_date, fmt_weight


class LedgerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._accounts = []; self._entries = []; self._selected_account_id = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        title = QLabel("📜  LEDGER — Account Entries")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        sel_row = QHBoxLayout(); sel_row.setSpacing(10)
        self._acct_combo = QComboBox(); self._acct_combo.setFixedWidth(300)
        self._acct_combo.currentIndexChanged.connect(self._on_account_changed)
        load_btn = QPushButton("Load"); load_btn.setObjectName("BtnSecondary")
        load_btn.clicked.connect(self._load_entries)
        add_acct_btn = QPushButton("＋  New Account"); add_acct_btn.setObjectName("BtnPrimary")
        add_acct_btn.clicked.connect(self._add_account)
        sel_row.addWidget(QLabel("Account:")); sel_row.addWidget(self._acct_combo)
        sel_row.addWidget(load_btn); sel_row.addStretch(); sel_row.addWidget(add_acct_btn)
        layout.addLayout(sel_row)

        sf = QFrame(); sf.setObjectName("Card")
        sv = QHBoxLayout(sf); sv.setContentsMargins(16,10,16,10); sv.setSpacing(32)
        self._dr_lbl = QLabel("DR: —")
        self._dr_lbl.setStyleSheet("color:#FF4757;font-size:15px;font-weight:700;")
        self._cr_lbl = QLabel("CR: —")
        self._cr_lbl.setStyleSheet("color:#2ED573;font-size:15px;font-weight:700;")
        self._bal_lbl = QLabel("BAL: —")
        self._bal_lbl.setStyleSheet("color:#F5A623;font-size:15px;font-weight:700;")
        sv.addWidget(self._dr_lbl); sv.addWidget(self._cr_lbl)
        sv.addWidget(self._bal_lbl); sv.addStretch()
        layout.addWidget(sf)

        b2 = QHBoxLayout()
        ae_btn = QPushButton("＋  Add Entry"); ae_btn.setObjectName("BtnPrimary")
        ae_btn.clicked.connect(self._add_entry)
        b2.addStretch(); b2.addWidget(ae_btn)
        layout.addLayout(b2)

        self._table = DataTable(["ID","Date","Particular","Debit","Dr Pcs","Credit","Cr Pcs","Balance"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete Entry"); del_btn.setObjectName("BtnDanger")
        del_btn.clicked.connect(self._delete_entry)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self)
        self._load_accounts()

    def _load_accounts(self):
        w = DBWorker(LedgerService.get_accounts, active_only=False)
        w.result.connect(self._on_accounts); w.start()

    def _on_accounts(self, accounts):
        self._accounts = accounts
        self._acct_combo.blockSignals(True)
        self._acct_combo.clear()
        self._acct_combo.addItems([f"{a.code} — {a.name}" for a in accounts])
        self._acct_combo.blockSignals(False)
        if accounts:
            self._selected_account_id = accounts[0].id
            self._load_entries()

    def _on_account_changed(self, idx):
        if 0 <= idx < len(self._accounts):
            self._selected_account_id = self._accounts[idx].id

    def _load_entries(self):
        if not self._selected_account_id: return
        self._overlay.show_over(self)
        aid = self._selected_account_id
        w = DBWorker(LedgerService.get_entries, account_id=aid)
        w.result.connect(self._on_entries); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()
        w2 = DBWorker(LedgerService.get_account_totals, aid)
        w2.result.connect(self._on_totals); w2.start()

    def _on_entries(self, entries):
        self._overlay.hide_overlay(); self._entries = entries
        self._table.populate([[
            e.id, fmt_date(e.entry_date), e.particular,
            f"{e.debit_g:.3f}" if e.debit_g else "—", e.debit_pcs or "—",
            f"{e.credit_g:.3f}" if e.credit_g else "—", e.credit_pcs or "—",
            f"{e.balance_g:.3f}"] for e in entries])

    def _on_totals(self, t):
        self._dr_lbl.setText(f"DR: {t['total_dr']:,.3f} g")
        self._cr_lbl.setText(f"CR: {t['total_cr']:,.3f} g")
        self._bal_lbl.setText(f"BAL: {t['balance']:,.3f} g")

    def _add_account(self):
        dlg = LedgerAccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: LedgerService.create_account(**dlg.get_data())).start()
            Toast.show_toast(self, "Account created.", "success"); self._load_accounts()

    def _add_entry(self):
        if not self._selected_account_id:
            return Toast.show_toast(self, "Select an account first.", "warning")
        prev = float(self._entries[-1].balance_g) if self._entries else 0.0
        dlg = LedgerEntryDialog(self, self._selected_account_id, prev)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: LedgerService.create_entry(**dlg.get_data())).start()
            Toast.show_toast(self, "Entry added.", "success"); self._load_entries()

    def _delete_entry(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select an entry.", "warning")
        eid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this ledger entry?"):
            DBWorker(lambda: LedgerService.delete_entry(eid)).start(); self._load_entries()


class LedgerAccountDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("New Ledger Account")
        self.setFixedSize(360, 240); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(12)
        self._code = QLineEdit(); self._name = QLineEdit()
        self._type = QComboBox(); self._type.addItems(["WORKER","PROCESS","STOCK","VIRTUAL"])
        self._ob = QDoubleSpinBox(); self._ob.setRange(-999999,999999); self._ob.setDecimals(3)
        for lbl, w in [("Code *", self._code), ("Name *", self._name),
                        ("Type *", self._type), ("Opening Balance (g)", self._ob)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def get_data(self):
        return {"code": self._code.text().strip(), "name": self._name.text().strip(),
                "account_type": self._type.currentText(), "opening_balance_g": self._ob.value()}


class LedgerEntryDialog(QDialog):
    def __init__(self, parent, account_id, prev_balance):
        super().__init__(parent); self.setWindowTitle("Add Ledger Entry")
        self.setFixedSize(380, 340); self.setModal(True)
        self._account_id = account_id; self._prev_balance = prev_balance
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._particular = QLineEdit()
        self._debit = QDoubleSpinBox(); self._debit.setRange(0,999999); self._debit.setDecimals(3)
        self._dr_pcs = QSpinBox(); self._dr_pcs.setRange(0,999999)
        self._credit = QDoubleSpinBox(); self._credit.setRange(0,999999); self._credit.setDecimals(3)
        self._cr_pcs = QSpinBox(); self._cr_pcs.setRange(0,999999)
        self._voucher = QLineEdit(); self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("Particular *", self._particular),
                        ("Debit (g)", self._debit), ("Dr Pcs", self._dr_pcs),
                        ("Credit (g)", self._credit), ("Cr Pcs", self._cr_pcs),
                        ("Voucher Ref", self._voucher), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def get_data(self):
        return {"account_id": self._account_id, "entry_date": self._date.date().toPyDate(),
                "particular": self._particular.text().strip(),
                "debit_g": self._debit.value(), "debit_pcs": self._dr_pcs.value(),
                "credit_g": self._credit.value(), "credit_pcs": self._cr_pcs.value(),
                "prev_balance": self._prev_balance,
                "voucher_ref": self._voucher.text() or None, "notes": self._notes.text() or None}
