"""Gold Receipts page — manage raw gold incoming from dealers."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDateEdit, QDoubleSpinBox,
    QComboBox, QDialogButtonBox
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.melt_service import MeltService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight
from config.settings import PURITY_OPTIONS


class GoldReceiptPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._receipts = []
        self._all_rows = []
        self._dealers = []
        self._setup_ui()
        self._load_dealers()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("🏅  GOLD RECEIPTS")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title); hdr.addStretch()
        self._search = SearchBar("Search receipts…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._filter)
        hdr.addWidget(self._search)
        add_btn = QPushButton("＋  Add Receipt")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        cols = ["ID", "Date", "Dealer", "Purity", "Weight (g)", "Net Wt (g)", "Receipt No", "Notes"]
        self._table = DataTable(cols)
        root.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel("0 receipts")
        self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        act.addWidget(self._cnt); act.addStretch()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addWidget(edit_btn); act.addWidget(del_btn)
        root.addLayout(act)
        self._overlay = LoadingOverlay(self)

    def _load_dealers(self):
        w = DBWorker(MasterService.get_dealers)
        w.result.connect(lambda dealers: setattr(self, '_dealers', dealers) or self._load())
        w.start()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(MeltService.get_receipts)
        w.result.connect(self._on_data); w.error.connect(self._on_err); w.start()

    def _on_data(self, receipts):
        self._overlay.hide_overlay()
        self._receipts = receipts
        dealer_map = {d.id: d.name for d in self._dealers}
        self._all_rows = [
            [r.id, fmt_date(r.receipt_date), dealer_map.get(r.dealer_id, str(r.dealer_id)),
             r.purity, fmt_weight(r.weight_g), fmt_weight(r.net_weight_g),
             r.receipt_no or "—", r.notes or ""]
            for r in receipts
        ]
        self._table.populate(self._all_rows)
        self._cnt.setText(f"{len(receipts)} receipts")

    def _filter(self, text):
        t = text.lower()
        self._table.populate([r for r in self._all_rows if any(t in str(v).lower() for v in r)])

    def _add(self):
        dlg = ReceiptDialog(self, self._dealers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                DBWorker(lambda: MeltService.create_receipt(**d)).start()
                Toast.show_toast(self, "Receipt added.", "success"); self._load()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a receipt.", "warning")
        rid = int(self._table.item(row, 0).text())
        receipt = next((r for r in self._receipts if r.id == rid), None)
        if not receipt: return
        dlg = ReceiptDialog(self, self._dealers, receipt)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: MeltService.update_receipt(rid, **dlg.get_data())).start()
            Toast.show_toast(self, "Receipt updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a receipt.", "warning")
        rid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete Receipt", "Delete this receipt?"):
            DBWorker(lambda: MeltService.delete_receipt(rid)).start()
            Toast.show_toast(self, "Deleted.", "info"); self._load()

    def _on_err(self, msg): self._overlay.hide_overlay(); Toast.show_toast(self, msg, "error")


class ReceiptDialog(QDialog):
    def __init__(self, parent, dealers, receipt=None):
        super().__init__(parent)
        self.setWindowTitle("Gold Receipt"); self.setFixedSize(400, 340); self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)

        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(receipt.receipt_date), "yyyy-MM-dd") if receipt
                          else QDate.currentDate())
        self._dealer = QComboBox()
        self._dealer_ids = [d.id for d in dealers]
        self._dealer.addItems([f"{d.code} — {d.name}" for d in dealers])
        if receipt:
            idx = self._dealer_ids.index(receipt.dealer_id) if receipt.dealer_id in self._dealer_ids else 0
            self._dealer.setCurrentIndex(idx)
        self._purity = QComboBox(); self._purity.addItems(PURITY_OPTIONS)
        if receipt: self._purity.setCurrentText(receipt.purity)
        self._wt = QDoubleSpinBox(); self._wt.setRange(0.001, 99999); self._wt.setDecimals(3)
        self._wt.setValue(receipt.weight_g if receipt else 0.0)
        self._net = QDoubleSpinBox(); self._net.setRange(0, 99999); self._net.setDecimals(3)
        self._net.setValue(receipt.net_weight_g if receipt else 0.0)
        self._rno = QLineEdit(receipt.receipt_no or "" if receipt else "")
        self._notes = QLineEdit(receipt.notes or "" if receipt else "")

        for lbl, w in [("Date *", self._date), ("Dealer *", self._dealer),
                        ("Purity *", self._purity), ("Weight (g) *", self._wt),
                        ("Net Weight (g)", self._net), ("Receipt No", self._rno), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "receipt_date": self._date.date().toPyDate(),
            "dealer_id": self._dealer_ids[self._dealer.currentIndex()],
            "purity": self._purity.currentText(),
            "weight_g": self._wt.value(),
            "net_weight_g": self._net.value() or None,
            "receipt_no": self._rno.text().strip() or None,
            "notes": self._notes.text().strip() or None,
        }
