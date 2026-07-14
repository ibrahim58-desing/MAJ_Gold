"""Wire & Sheet, Polish, Faceting pages — one file for brevity."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QCheckBox, QTabWidget, QMessageBox
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from ui.widgets.process_widgets import ChainTallyWidget, WorkerTeamSelector
from workers.db_worker import DBWorker
from services.process_service import ProcessService
from services.master_service import MasterService
from utils.formatters import fmt_date, fmt_weight


# ─────────────────────────────────────────────────────────────────────────────
# Wire & Sheet
# ─────────────────────────────────────────────────────────────────────────────
class WireSheetPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []; self._workers = []; self._products = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("🔗  WIRE & SHEET BATCHES")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID","Date","Melt Batch","Wt In (g)","Wt Out (g)",
                                  "Loss (g)","Chains","Solder (g)","Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        DBWorker(MasterService.get_workers).result.connect(lambda w: setattr(self, '_workers', w))
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_wire_sheet_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.batch_date), b.melt_batch_id,
                               fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g),
                               fmt_weight(b.loss_g), b.chains_count,
                               fmt_weight(b.solder_weight_g), b.notes or ""] for b in batches])

    def _add(self):
        dlg = WireSheetDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_wire_sheet(**dlg.get_data())).start()
            Toast.show_toast(self, "Wire/Sheet batch created.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = WireSheetDialog(self, self._workers, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.update_wire_sheet(bid, **dlg.get_data())).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this wire/sheet batch?"):
            DBWorker(lambda: ProcessService.delete_wire_sheet(bid)).start(); self._load()


class WireSheetDialog(QDialog):
    def __init__(self, parent, workers, batch=None):
        super().__init__(parent); self.setWindowTitle("Wire & Sheet Batch")
        self.setFixedSize(420, 360); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(batch.batch_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._melt_id = QSpinBox(); self._melt_id.setRange(1, 999999)
        if batch: self._melt_id.setValue(batch.melt_batch_id)
        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(batch.weight_in_g if batch else 0)
        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0,999999); self._wt_out.setDecimals(3)
        self._wt_out.setValue(batch.weight_out_g if batch else 0)
        self._chains = QSpinBox(); self._chains.setRange(0, 999999)
        self._chains.setValue(batch.chains_count if batch else 0)
        self._solder = QDoubleSpinBox(); self._solder.setRange(0,999999); self._solder.setDecimals(3)
        self._solder.setValue(batch.solder_weight_g if batch else 0)
        self._notes = QLineEdit(batch.notes or "" if batch else "")
        for lbl, w in [("Date *", self._date), ("Melt Batch ID *", self._melt_id),
                        ("Wt In (g) *", self._wt_in), ("Wt Out (g) *", self._wt_out),
                        ("Chains Count", self._chains), ("Solder (g)", self._solder),
                        ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"batch_date": self._date.date().toPyDate(),
                "melt_batch_id": self._melt_id.value(), "weight_in_g": self._wt_in.value(),
                "weight_out_g": self._wt_out.value(), "chains_count": self._chains.value(),
                "solder_weight_g": self._solder.value(), "notes": self._notes.text() or None}


# ─────────────────────────────────────────────────────────────────────────────
# Polish
# ─────────────────────────────────────────────────────────────────────────────
class PolishPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("✨  POLISH BATCHES")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        note = QLabel("ℹ  Polish has no gold weight loss — only chain count tracked.")
        note.setStyleSheet("color:#4A5568; font-size:12px; font-style:italic;")
        layout.addWidget(note)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Polish Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID","Date","GS Batch ID","Chains In","Chains Out","Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_polish_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.batch_date), b.goldsmith_batch_id,
                               b.chains_in, b.chains_out, b.notes or ""] for b in batches])

    def _add(self):
        dlg = PolishDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_polish_batch(**dlg.get_data())).start()
            Toast.show_toast(self, "Polish batch created.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this polish batch?"):
            DBWorker(lambda: ProcessService.delete_polish_batch(bid)).start(); self._load()


class PolishDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("Polish Batch")
        self.setFixedSize(380, 280); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._gs_batch = QSpinBox(); self._gs_batch.setRange(1, 999999)
        self._chains_in = QSpinBox(); self._chains_in.setRange(0, 999999)
        self._chains_out = QSpinBox(); self._chains_out.setRange(0, 999999)
        self._notes = QLineEdit()
        for lbl, w in [("Date *", self._date), ("GS Batch ID *", self._gs_batch),
                        ("Chains IN", self._chains_in), ("Chains OUT", self._chains_out),
                        ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"batch_date": self._date.date().toPyDate(), "goldsmith_batch_id": self._gs_batch.value(),
                "chains_in": self._chains_in.value(), "chains_out": self._chains_out.value(),
                "notes": self._notes.text() or None}


# ─────────────────────────────────────────────────────────────────────────────
# Faceting
# ─────────────────────────────────────────────────────────────────────────────
class FacetingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("💎  FACETING")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        tabs = QTabWidget()
        self._batches_tab = FacetingBatchesTab()
        self._loss_tab = FacetingLossTab()
        tabs.addTab(self._batches_tab, "📋  Batches")
        tabs.addTab(self._loss_tab, "♻  Loss")
        layout.addWidget(tabs)

    def refresh(self):
        self._batches_tab.refresh()
        self._loss_tab.refresh()


class FacetingBatchesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Faceting Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID","From","To","Assigned To","Wt In (g)","Wt Out (g)",
                                  "Loss (g)","Loss→Melt (g)","Loss→GBox (g)","Loss Routed",
                                  "Status","Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        update_btn = QPushButton("⚙  Update"); update_btn.setObjectName("BtnPrimary"); update_btn.clicked.connect(self._update)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(update_btn); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_faceting_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.from_date), fmt_date(b.to_date),
                               b.assigned_to_type or "INDIVIDUAL",
                               fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g),
                               fmt_weight(b.weight_loss_g),
                               fmt_weight(b.loss_to_melting_g or 0) if b.loss_routed else "—",
                               fmt_weight(b.loss_to_gold_box_g or 0) if b.loss_routed else "—",
                               ("Yes" if b.loss_routed else "No") if b.status == "completed" else "—",
                               b.status or "pending", b.notes or ""] for b in batches])

    def _add(self):
        dlg = FacetingCreateDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_faceting_batch(**dlg.get_data())).start()
            Toast.show_toast(self, "Faceting batch created.", "success"); self._load()

    def _update(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        if batch.status == "completed":
            return Toast.show_toast(self, "Batch is already completed.", "warning")
        dlg = FacetingUpdateDialog(self, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            def _run():
                ProcessService.update_faceting_output(bid, **dlg.get_data())
            w = DBWorker(_run)
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            w.result.connect(lambda _: (Toast.show_toast(self, "Faceting output recorded.", "success"), self._load()))
            w.start()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this faceting batch?"):
            DBWorker(lambda: ProcessService.delete_faceting_batch(bid)).start(); self._load()

    def refresh(self):
        self._load()


class FacetingCreateDialog(QDialog):
    """Step 1: who is doing the work, how much gold, and what chain sizes went in."""
    def __init__(self, parent):
        super().__init__(parent); self.setWindowTitle("New Faceting Batch")
        self.setFixedSize(440, 560); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)

        self._from = QDateEdit(); self._from.setCalendarPopup(True); self._from.setDate(QDate.currentDate())
        l = QLabel("From Date *"); l.setObjectName("FieldLabel"); form.addRow(l, self._from)

        self._selector = WorkerTeamSelector(process_type="FACETING")
        form.addRow(self._selector)

        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0, 999999); self._wt_in.setDecimals(3)
        l = QLabel("Wt In (g) *"); l.setObjectName("FieldLabel"); form.addRow(l, self._wt_in)

        l = QLabel("Chain Length — click to tally *"); l.setObjectName("FieldLabel"); form.addRow(l)
        self._tally = ChainTallyWidget()
        form.addRow(self._tally)

        self._notes = QLineEdit()
        l = QLabel("Notes"); l.setObjectName("FieldLabel"); form.addRow(l, self._notes)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate_and_accept(self):
        if self._wt_in.value() <= 0:
            QMessageBox.warning(self, "Error", "Wt In must be > 0"); return
        self.accept()

    def get_data(self):
        counts = self._tally.counts
        return {
            "from_date": self._from.date().toPyDate(),
            **self._selector.as_dict(),
            "weight_in_g": self._wt_in.value(),
            "in_qty_baby": counts["baby"], "in_qty_normal": counts["normal"],
            "in_qty_30inch": counts["30inch"],
            "notes": self._notes.text() or None,
        }


class FacetingUpdateDialog(QDialog):
    """Step 2: just the output weight and chain tally. At this point it's
    usually not yet known whether the resulting loss is clean scrap (goes
    back to Melting) or mixed/dirty (goes to the Gold Box) — that decision
    is made later, once it's actually known, on the Faceting Loss page."""
    def __init__(self, parent, batch):
        super().__init__(parent); self.setWindowTitle(f"Update Faceting Batch #{batch.id}")
        self.setFixedSize(440, 420); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)

        lbl_in = QLabel(f"Wt In: {batch.weight_in_g:.3f} g"); lbl_in.setObjectName("FieldLabel")
        form.addRow(lbl_in)

        self._to = QDateEdit(); self._to.setCalendarPopup(True); self._to.setDate(QDate.currentDate())
        l = QLabel("To Date *"); l.setObjectName("FieldLabel"); form.addRow(l, self._to)

        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0, 999999); self._wt_out.setDecimals(3)
        l = QLabel("Wt Out (g) *"); l.setObjectName("FieldLabel"); form.addRow(l, self._wt_out)

        l = QLabel("Chain Length — click to tally *"); l.setObjectName("FieldLabel"); form.addRow(l)
        self._tally = ChainTallyWidget()
        form.addRow(self._tally)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate_and_accept(self):
        if self._wt_out.value() <= 0:
            QMessageBox.warning(self, "Error", "Wt Out must be > 0"); return
        self.accept()

    def get_data(self):
        counts = self._tally.counts
        return {
            "to_date": self._to.date().toPyDate(), "weight_out_g": self._wt_out.value(),
            "out_qty_baby": counts["baby"], "out_qty_normal": counts["normal"],
            "out_qty_30inch": counts["30inch"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Faceting Loss — decide, after the fact, where a completed batch's loss goes
# ─────────────────────────────────────────────────────────────────────────────
class FacetingLossTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(10)

        info = QLabel("Completed Faceting batches whose weight loss hasn't been assigned yet. "
                       "Decide once it's known whether it's clean scrap (→ Melting) or dirty/mixed (→ Gold Box). "
                       "Once assigned, the split stays visible on the Batches tab.")
        info.setStyleSheet("color:#4A5568; font-size:12px; font-style:italic;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = DataTable(["ID","From","To","Assigned To","Wt In (g)","Wt Out (g)","Loss (g)"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        assign_btn = QPushButton("⚙  Assign Loss")
        assign_btn.setObjectName("BtnPrimary"); assign_btn.clicked.connect(self._assign)
        act.addStretch(); act.addWidget(assign_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_unrouted_faceting_losses)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.from_date), fmt_date(b.to_date),
                               b.assigned_to_type or "INDIVIDUAL",
                               fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g),
                               fmt_weight(b.weight_loss_g)] for b in batches])

    def _assign(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = AssignLossDialog(self, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            def _run():
                ProcessService.route_faceting_loss(bid, **data)
            w = DBWorker(_run)
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            w.result.connect(lambda _: (Toast.show_toast(self, "Loss assigned.", "success"), self._load()))
            w.start()

    def refresh(self):
        self._load()


class AssignLossDialog(QDialog):
    def __init__(self, parent, batch):
        super().__init__(parent); self.setWindowTitle(f"Assign Loss — Batch #{batch.id}")
        self.setFixedSize(400, 320); self.setModal(True)
        self._loss = batch.weight_loss_g
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)

        lbl = QLabel(f"Weight Loss: {batch.weight_loss_g:.3f} g"); lbl.setObjectName("FieldLabel")
        form.addRow(lbl)

        self._loss_melt = QDoubleSpinBox(); self._loss_melt.setRange(0, 999999); self._loss_melt.setDecimals(3)
        self._loss_gbox = QDoubleSpinBox(); self._loss_gbox.setRange(0, 999999); self._loss_gbox.setDecimals(3)
        for lbl2, w in [("Loss → Melting (g)", self._loss_melt), ("Loss → Gold Box (g)", self._loss_gbox)]:
            l = QLabel(lbl2); l.setObjectName("FieldLabel"); form.addRow(l, w)

        quick = QHBoxLayout()
        btn_all_melt = QPushButton("All → Melting"); btn_all_melt.setObjectName("BtnSecondary")
        btn_all_melt.clicked.connect(self._all_to_melting)
        btn_all_gbox = QPushButton("All → Gold Box"); btn_all_gbox.setObjectName("BtnSecondary")
        btn_all_gbox.clicked.connect(self._all_to_gold_box)
        quick.addWidget(btn_all_melt); quick.addWidget(btn_all_gbox)
        form.addRow(quick)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _all_to_melting(self):
        self._loss_melt.setValue(self._loss); self._loss_gbox.setValue(0)

    def _all_to_gold_box(self):
        self._loss_gbox.setValue(self._loss); self._loss_melt.setValue(0)

    def _validate_and_accept(self):
        split = self._loss_melt.value() + self._loss_gbox.value()
        if abs(split - self._loss) > 0.001:
            QMessageBox.warning(
                self, "Loss not fully assigned",
                f"Weight Loss is {self._loss:.3f} g but Melting + Gold Box = {split:.3f} g.\n"
                f"Use the quick buttons or adjust the split so both amounts add up to the total loss."
            )
            return
        self.accept()

    def get_data(self):
        return {"loss_to_melting_g": self._loss_melt.value(), "loss_to_gold_box_g": self._loss_gbox.value()}

