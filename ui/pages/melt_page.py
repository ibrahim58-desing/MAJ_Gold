"""Melt Batches page — NG Melting and Scrap Melting."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QTextEdit, QTabWidget, QFrame
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.melt_service import MeltService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight
from config.settings import MELT_TYPES


class MeltPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []; self._all_rows = []
        self._workers = []; self._alloys = []; self._products = []
        self._setup_ui()
        self._load_masters()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("🔥  MELT BATCHES")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title); hdr.addStretch()
        self._search = SearchBar("Search…")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._filter)
        hdr.addWidget(self._search)

        filt = QComboBox(); filt.addItems(["All", "NG_MELTING", "SCRAP_MELTING"])
        filt.setFixedWidth(160)
        filt.currentTextChanged.connect(self._load)
        self._type_filter = filt
        hdr.addWidget(filt)

        add_btn = QPushButton("＋  New Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        cols = ["ID","Date","Type","Wt In (g)","Total Alloy (g)","Gross (g)",
                "Output 916 (g)","NG (g)","Kambi (g)","Loss (g)","Notes"]
        self._table = DataTable(cols)
        root.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel("")
        self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        act.addWidget(self._cnt); act.addStretch()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addWidget(edit_btn); act.addWidget(del_btn)
        root.addLayout(act)
        self._overlay = LoadingOverlay(self)

    def _load_masters(self):
        DBWorker(MasterService.get_workers).result.connect(lambda w: setattr(self, '_workers', w))
        DBWorker(MasterService.get_alloy_types).result.connect(lambda a: setattr(self, '_alloys', a))
        DBWorker(MasterService.get_product_types).result.connect(lambda p: setattr(self, '_products', p) or self._load())
        for w in [DBWorker(MasterService.get_workers), DBWorker(MasterService.get_alloy_types),
                  DBWorker(MasterService.get_product_types)]:
            w.start()
        # Also load after a delay to ensure masters are ready
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(800, self._load)

    def _load(self, *_):
        self._overlay.show_over(self)
        melt_type = self._type_filter.currentText() if hasattr(self, '_type_filter') else "All"
        kwargs = {} if melt_type == "All" else {"melt_type": melt_type}
        w = DBWorker(MeltService.get_melt_batches, **kwargs)
        w.result.connect(self._on_data); w.error.connect(self._on_err); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay()
        self._batches = batches
        self._all_rows = [
            [b.id, fmt_date(b.batch_date), b.melt_type,
             fmt_weight(b.weight_in_g), fmt_weight(b.total_alloy_g), fmt_weight(b.gross_weight_g),
             fmt_weight(b.weight_out_916_g), fmt_weight(b.ng_weight_g),
             fmt_weight(b.kambi_weight_g), fmt_weight(b.loss_g), b.notes or ""]
            for b in batches
        ]
        self._table.populate(self._all_rows)
        self._cnt.setText(f"{len(batches)} batches")

    def _filter(self, text):
        t = text.lower()
        self._table.populate([r for r in self._all_rows if any(t in str(v).lower() for v in r)])

    def _add(self):
        dlg = MeltBatchDialog(self, self._workers, self._alloys, self._products)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                DBWorker(lambda: MeltService.create_melt_batch(**d)).start()
                Toast.show_toast(self, "Melt batch created.", "success"); self._load()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = MeltBatchDialog(self, self._workers, self._alloys, self._products, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: MeltService.update_melt_batch(bid, **d)).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete Melt Batch", "Delete this melt batch and its alloys?"):
            DBWorker(lambda: MeltService.delete_melt_batch(bid)).start()
            Toast.show_toast(self, "Deleted.", "info"); self._load()

    def _on_err(self, msg): self._overlay.hide_overlay(); Toast.show_toast(self, msg, "error")


class MeltBatchDialog(QDialog):
    def __init__(self, parent, workers, alloys, products, batch=None):
        super().__init__(parent)
        self.setWindowTitle("Melt Batch"); self.setFixedSize(500, 500); self.setModal(True)
        self._alloys = alloys
        self._alloy_spins = []
        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)

        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(batch.batch_date), "yyyy-MM-dd") if batch else QDate.currentDate())

        self._type = QComboBox(); self._type.addItems(MELT_TYPES)
        if batch: self._type.setCurrentText(batch.melt_type)

        self._worker = QComboBox()
        self._worker_ids = [None] + [w.id for w in workers]
        self._worker.addItems(["— none —"] + [f"{w.code}" for w in workers])

        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(batch.weight_in_g if batch else 0)
        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0,999999); self._wt_out.setDecimals(3)
        self._wt_out.setValue(batch.weight_out_916_g if batch else 0)
        self._ng = QDoubleSpinBox(); self._ng.setRange(0,999999); self._ng.setDecimals(3)
        self._ng.setValue(batch.ng_weight_g if batch else 0)
        self._kambi = QDoubleSpinBox(); self._kambi.setRange(0,999999); self._kambi.setDecimals(3)
        self._kambi.setValue(batch.kambi_weight_g if batch else 0)
        self._notes = QTextEdit(); self._notes.setFixedHeight(60)
        self._notes.setPlainText(batch.notes or "" if batch else "")

        for lbl, w in [("Date *", self._date), ("Melt Type *", self._type),
                        ("Worker", self._worker), ("Weight In (g) *", self._wt_in),
                        ("Output 916 (g) *", self._wt_out), ("NG Weight (g)", self._ng),
                        ("Kambi Weight (g)", self._kambi), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)

        # Alloy section
        alloy_lbl = QLabel("ALLOY ADDITIONS")
        alloy_lbl.setStyleSheet("color:#F5A623; font-size:11px; font-weight:700; letter-spacing:1px; margin-top:6px;")
        form.addRow(alloy_lbl)
        for a in alloys:
            spin = QDoubleSpinBox(); spin.setRange(0, 9999); spin.setDecimals(3)
            self._alloy_spins.append((a.id, spin))
            l = QLabel(a.name); l.setObjectName("FieldLabel")
            form.addRow(l, spin)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        alloy_adds = [{"alloy_type_id": aid, "weight_g": spin.value()}
                      for aid, spin in self._alloy_spins if spin.value() > 0]
        w_idx = self._worker.currentIndex()
        return {
            "batch_date": self._date.date().toPyDate(),
            "melt_type": self._type.currentText(),
            "weight_in_g": self._wt_in.value(),
            "weight_out_916_g": self._wt_out.value(),
            "ng_weight_g": self._ng.value(),
            "kambi_weight_g": self._kambi.value(),
            "worker_id": self._worker_ids[w_idx],
            "alloy_additions": alloy_adds,
            "notes": self._notes.toPlainText().strip() or None,
        }
