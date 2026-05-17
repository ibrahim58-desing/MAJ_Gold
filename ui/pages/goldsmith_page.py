"""Goldsmith page — batches + worker logs + design logs (GS-CLOSING + GS-PCS)."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QTabWidget, QLineEdit
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.process_service import ProcessService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight, calc_ppwl, calc_extra_loss, calc_pay


class GoldsmithPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []; self._products = []; self._designs = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("⚒  GOLDSMITH — GS-CLOSING")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        tabs = QTabWidget()
        self._batch_tab = GoldsmithBatchTab()
        self._log_tab = WorkerLogTab()
        self._design_tab = DesignLogTab()
        tabs.addTab(self._batch_tab, "📦  Batches")
        tabs.addTab(self._log_tab, "📋  Worker Logs")
        tabs.addTab(self._design_tab, "🎨  Design Logs (GS-PCS)")
        layout.addWidget(tabs)

        self._load_masters()

    def _load_masters(self):
        w1 = DBWorker(MasterService.get_workers)
        w1.result.connect(self._on_workers); w1.start()

    def _on_workers(self, workers):
        self._workers = workers
        self._batch_tab.set_workers(workers)
        self._log_tab.set_workers(workers)
        self._design_tab.set_workers(workers)


class GoldsmithBatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self._batches = []; self._workers = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New GS Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        cols = ["ID", "From", "To", "Wt In (g)", "Wt Out (g)", "Loss (g)",
                "Fin Pcs", "Per Pc WL", "Notes"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)
        self._overlay = LoadingOverlay(self)
        self._load()

    def set_workers(self, w): self._workers = w

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_goldsmith_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[
            b.id, fmt_date(b.from_date), fmt_date(b.to_date),
            fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g),
            fmt_weight(b.weight_loss_g), b.fin_pcs,
            f"{b.per_pc_wl:.4f}", b.notes or ""] for b in batches])

    def _add(self):
        dlg = GoldsmithBatchDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_goldsmith_batch(**dlg.get_data())).start()
            Toast.show_toast(self, "Batch created.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = GoldsmithBatchDialog(self, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.update_goldsmith_batch(bid, **dlg.get_data())).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this goldsmith batch?"):
            DBWorker(lambda: ProcessService.delete_goldsmith_batch(bid)).start()
            self._load()


class GoldsmithBatchDialog(QDialog):
    def __init__(self, parent, batch=None):
        super().__init__(parent); self.setWindowTitle("Goldsmith Batch")
        self.setFixedSize(420, 340); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._from = QDateEdit(); self._from.setCalendarPopup(True)
        self._from.setDate(QDate.fromString(str(batch.from_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._to = QDateEdit(); self._to.setCalendarPopup(True)
        self._to.setDate(QDate.fromString(str(batch.to_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(batch.weight_in_g if batch else 0)
        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0,999999); self._wt_out.setDecimals(3)
        self._wt_out.setValue(batch.weight_out_g if batch else 0)
        self._pcs = QSpinBox(); self._pcs.setRange(0, 999999)
        self._pcs.setValue(batch.fin_pcs if batch else 0)
        self._notes = QLineEdit(batch.notes or "" if batch else "")
        for lbl, w in [("From Date *", self._from), ("To Date *", self._to),
                        ("Weight IN (g) *", self._wt_in), ("Weight OUT (g) *", self._wt_out),
                        ("Finished Pcs", self._pcs), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"from_date": self._from.date().toPyDate(), "to_date": self._to.date().toPyDate(),
                "weight_in_g": self._wt_in.value(), "weight_out_g": self._wt_out.value(),
                "fin_pcs": self._pcs.value(), "notes": self._notes.text() or None}


class WorkerLogTab(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []; self._batches = []; self._logs = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Add Log")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        cols = ["ID", "Batch", "Worker", "Date", "Debit (g)", "Credit (g)",
                "Loss (g)", "Pcs", "PPWL", "Act WL", "Extra Loss", "Pay ₹"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def set_workers(self, w): self._workers = w

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_worker_logs)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, logs):
        self._overlay.hide_overlay(); self._logs = logs
        self._table.populate([[
            l.id, l.goldsmith_batch_id,
            l.worker.name if l.worker else "—", fmt_date(l.log_date),
            fmt_weight(l.debit_g), fmt_weight(l.credit_g), fmt_weight(l.weight_loss_g),
            l.pcs, f"{l.ppwl:.4f}", f"{l.act_wl:.4f}", fmt_weight(l.extra_loss_g),
            f"₹{l.pay_earned:.2f}"] for l in logs])

    def _add(self):
        dlg = WorkerLogDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_worker_log(**dlg.get_data())).start()
            Toast.show_toast(self, "Log added.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a row.", "warning")
        lid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this worker log?"):
            DBWorker(lambda: ProcessService.delete_worker_log(lid)).start(); self._load()


class WorkerLogDialog(QDialog):
    def __init__(self, parent, workers):
        super().__init__(parent); self.setWindowTitle("Worker Log")
        self.setFixedSize(420, 400); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)
        self._batch_id = QSpinBox(); self._batch_id.setRange(1, 999999)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._worker = QComboBox()
        self._worker_ids = [w.id for w in workers]
        self._worker.addItems([f"{w.code} — {w.name}" for w in workers])
        self._debit = QDoubleSpinBox(); self._debit.setRange(0, 999999); self._debit.setDecimals(3)
        self._credit = QDoubleSpinBox(); self._credit.setRange(0, 999999); self._credit.setDecimals(3)
        self._pcs = QSpinBox(); self._pcs.setRange(0, 999999)
        self._ppwl = QDoubleSpinBox(); self._ppwl.setRange(0, 9999); self._ppwl.setDecimals(4)
        self._notes = QLineEdit()
        for lbl, w in [("GS Batch ID *", self._batch_id), ("Date *", self._date),
                        ("Worker *", self._worker), ("Debit (g) *", self._debit),
                        ("Credit (g) *", self._credit), ("Pieces *", self._pcs),
                        ("PPWL (allowed)", self._ppwl), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "goldsmith_batch_id": self._batch_id.value(),
            "worker_id": self._worker_ids[self._worker.currentIndex()] if self._worker_ids else None,
            "log_date": self._date.date().toPyDate(),
            "debit_g": self._debit.value(), "credit_g": self._credit.value(),
            "pcs": self._pcs.value(), "ppwl": self._ppwl.value(),
            "notes": self._notes.text() or None,
        }


class DesignLogTab(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []; self._designs = []; self._logs = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Add Design Log")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID", "Batch", "Worker", "Design", "Month", "Pieces"])
        layout.addWidget(self._table, 1)

        self._overlay = LoadingOverlay(self)
        self._load_designs()

    def set_workers(self, w): self._workers = w

    def _load_designs(self):
        w = DBWorker(MasterService.get_design_types)
        w.result.connect(lambda d: setattr(self, '_designs', d) or self._load())
        w.start()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_design_logs)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, logs):
        self._overlay.hide_overlay(); self._logs = logs
        design_map = {d.id: d.code for d in self._designs}
        self._table.populate([[l.id, l.goldsmith_batch_id, l.worker_id,
                               design_map.get(l.design_type_id, "—"),
                               l.month_year, l.pieces_count] for l in logs])

    def _add(self):
        dlg = DesignLogDialog(self, self._workers, self._designs)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_design_log(**dlg.get_data())).start()
            Toast.show_toast(self, "Design log added.", "success"); self._load()


class DesignLogDialog(QDialog):
    def __init__(self, parent, workers, designs):
        super().__init__(parent); self.setWindowTitle("Design Log (GS-PCS)")
        self.setFixedSize(400, 300); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._batch = QSpinBox(); self._batch.setRange(1, 999999)
        self._worker = QComboBox()
        self._worker_ids = [w.id for w in workers]
        self._worker.addItems([f"{w.code}" for w in workers])
        self._design = QComboBox()
        self._design_ids = [d.id for d in designs]
        self._design.addItems([d.code for d in designs])
        self._month = QLineEdit(); self._month.setPlaceholderText("Apr-26")
        self._pcs = QSpinBox(); self._pcs.setRange(0, 999999)
        for lbl, w in [("GS Batch ID *", self._batch), ("Worker *", self._worker),
                        ("Design *", self._design), ("Month-Year *", self._month),
                        ("Pieces *", self._pcs)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "goldsmith_batch_id": self._batch.value(),
            "worker_id": self._worker_ids[self._worker.currentIndex()] if self._worker_ids else None,
            "design_type_id": self._design_ids[self._design.currentIndex()] if self._design_ids else None,
            "month_year": self._month.text().strip(),
            "pieces_count": self._pcs.value(),
        }
