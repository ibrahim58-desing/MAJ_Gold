"""Daybook Page — full CRUD for the central double-entry ledger."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDateEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QTextEdit, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt, QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.daybook_service import DaybookService
from utils.formatters import fmt_date, fmt_weight
from datetime import date


class DaybookPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_rows = []
        self._entries = []
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📒  DAYBOOK — Inventory Day Book")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title); hdr.addStretch()

        self._search = SearchBar("Search account / particular…")
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self._filter)
        hdr.addWidget(self._search)

        add_btn = QPushButton("＋  Add Entry")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        # Filter bar
        fbar = QHBoxLayout()
        fbar.setSpacing(10)
        lbl = QLabel("Date Range:")
        lbl.setStyleSheet("color:#8A9BB5; font-size:12px;")
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDate(QDate.currentDate().addMonths(-1))
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDate(QDate.currentDate())
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("BtnSecondary")
        apply_btn.clicked.connect(self._load)
        fbar.addWidget(lbl)
        fbar.addWidget(self._from_date)
        fbar.addWidget(QLabel("to"))
        fbar.addWidget(self._to_date)
        fbar.addWidget(apply_btn)
        fbar.addStretch()
        root.addLayout(fbar)

        # Table
        cols = ["ID", "S.No", "Date", "Ledger Account", "Particular",
                "Debit Wt", "Dr Pcs", "Credit Wt", "Cr Pcs", "Voucher", "Group", "Notes"]
        self._table = DataTable(cols)
        root.addWidget(self._table, 1)

        # Action bar
        act = QHBoxLayout()
        self._cnt = QLabel("0 entries")
        self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        act.addWidget(self._cnt); act.addStretch()

        edit_btn = QPushButton("✏  Edit")
        edit_btn.setObjectName("BtnSecondary")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete")
        del_btn.setObjectName("BtnDanger")
        del_btn.clicked.connect(self._delete)
        act.addWidget(edit_btn); act.addWidget(del_btn)
        root.addLayout(act)

        self._overlay = LoadingOverlay(self)

    def _load(self):
        self._overlay.show_over(self)
        from_d = self._from_date.date().toPyDate()
        to_d = self._to_date.date().toPyDate()
        w = DBWorker(DaybookService.get_entries, start_date=from_d, end_date=to_d, limit=1000)
        w.result.connect(self._on_data); w.error.connect(self._on_err); w.start()

    def _on_data(self, result):
        self._overlay.hide_overlay()
        entries, total = result
        self._entries = entries
        self._all_rows = [
            [e.id, e.serial_no, fmt_date(e.entry_date), e.ledger_account, e.particular,
             fmt_weight(e.debit_wt), e.debit_pcs or "—",
             fmt_weight(e.credit_wt), e.credit_pcs or "—",
             e.voucher_ref or "—", e.group_type or "—", e.notes or ""]
            for e in entries
        ]
        self._table.populate(self._all_rows)
        self._cnt.setText(f"{total} entries (showing {len(entries)})")

    def _filter(self, text):
        t = text.lower()
        filtered = [r for r in self._all_rows if any(t in str(v).lower() for v in r)]
        self._table.populate(filtered)

    def _add(self):
        dlg = DaybookEntryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                DBWorker(lambda: DaybookService.create_double_entry(**d)).start()
                Toast.show_toast(self, "Double entry created.", "success")
                self._load()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select an entry.", "warning")
        entry_id = int(self._table.item(row, 0).text())
        entry = next((e for e in self._entries if e.id == entry_id), None)
        if not entry: return
        dlg = DaybookEditDialog(self, entry)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: DaybookService.update_entry(entry_id, **d)).start()
            Toast.show_toast(self, "Entry updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select an entry.", "warning")
        entry_id = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete Entry", "Delete this daybook entry?"):
            DBWorker(lambda: DaybookService.delete_entry(entry_id)).start()
            Toast.show_toast(self, "Entry deleted.", "info"); self._load()

    def _on_err(self, msg):
        self._overlay.hide_overlay(); Toast.show_toast(self, msg, "error")


class DaybookEntryDialog(QDialog):
    GROUP_TYPES = ["GOLD SMITH", "FACETING", "MELTING", "KAMBI", "HALLMARKING", "LEDGER", ""]

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Add Daybook Entry (Double Entry)")
        self.setFixedSize(480, 420)
        self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(22, 20, 22, 20)
        form.setSpacing(12)

        title = QLabel("New Double-Entry Transaction")
        title.setObjectName("DialogTitle")
        form.addRow(title)

        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._debit_acc = QLineEdit(); self._debit_acc.setPlaceholderText("e.g. GS-MUSTHAFA")
        self._credit_acc = QLineEdit(); self._credit_acc.setPlaceholderText("e.g. FAC-FACETING")
        self._weight = QDoubleSpinBox(); self._weight.setRange(0, 9999999); self._weight.setDecimals(3)
        self._pcs = QSpinBox(); self._pcs.setRange(0, 999999)
        self._group = QComboBox(); self._group.addItems(self.GROUP_TYPES)
        self._source = QComboBox()
        self._source.addItems(["", "MELTING", "WIRE_SHEET", "GOLDSMITH", "FACETING", "KAMBI", "GOLD_BOX"])
        self._notes = QLineEdit()

        for lbl, w in [("Date *", self._date), ("Debit Account *", self._debit_acc),
                        ("Credit Account *", self._credit_acc), ("Weight (g) *", self._weight),
                        ("Pieces", self._pcs), ("Group Type", self._group),
                        ("Source Process", self._source), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel")
            form.addRow(l, w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "entry_date": self._date.date().toPyDate(),
            "debit_account": self._debit_acc.text().strip(),
            "credit_account": self._credit_acc.text().strip(),
            "weight": self._weight.value(),
            "pcs": self._pcs.value(),
            "group_type": self._group.currentText() or None,
            "source_process": self._source.currentText() or None,
            "notes": self._notes.text().strip() or None,
        }


class DaybookEditDialog(QDialog):
    def __init__(self, parent, entry):
        super().__init__(parent)
        self.setWindowTitle("Edit Daybook Entry")
        self.setFixedSize(420, 360)
        self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(22, 20, 22, 20)
        form.setSpacing(12)

        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(entry.entry_date), "yyyy-MM-dd"))
        self._ledger = QLineEdit(entry.ledger_account)
        self._particular = QLineEdit(entry.particular)
        self._debit_wt = QDoubleSpinBox(); self._debit_wt.setRange(0,9999999); self._debit_wt.setDecimals(3)
        self._debit_wt.setValue(entry.debit_wt or 0)
        self._credit_wt = QDoubleSpinBox(); self._credit_wt.setRange(0,9999999); self._credit_wt.setDecimals(3)
        self._credit_wt.setValue(entry.credit_wt or 0)
        self._notes = QLineEdit(entry.notes or "")

        for lbl, w in [("Date", self._date), ("Ledger Account", self._ledger),
                        ("Particular", self._particular), ("Debit Wt (g)", self._debit_wt),
                        ("Credit Wt (g)", self._credit_wt), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "entry_date": self._date.date().toPyDate(),
            "ledger_account": self._ledger.text().strip(),
            "particular": self._particular.text().strip(),
            "debit_wt": self._debit_wt.value(),
            "credit_wt": self._credit_wt.value(),
            "notes": self._notes.text().strip() or None,
        }
