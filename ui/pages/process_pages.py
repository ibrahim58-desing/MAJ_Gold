"""Wire & Sheet, Polish, Faceting, Kambi pages — one file for brevity."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QCheckBox, QTabWidget
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
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
        self._batches = []; self._workers = []; self._teams = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("💎  FACETING BATCHES")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Faceting Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID","From","To","Worker/Team","Wt In (g)","Wt Out (g)",
                                  "Loss (g)","Fin Pcs","Act Pcs","V Acc","Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load_masters()

    def _load_masters(self):
        w1 = DBWorker(MasterService.get_workers)
        w1.result.connect(lambda w: setattr(self, '_workers', w))
        w1.start()
        w2 = DBWorker(MasterService.get_teams)
        w2.result.connect(lambda t: setattr(self, '_teams', t) or self._load())
        w2.start()

    def _load(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_faceting_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.from_date), fmt_date(b.to_date),
                               f"W:{b.worker_id} T:{b.team_id}",
                               fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g),
                               fmt_weight(b.weight_loss_g), b.fin_pcs, b.act_fin_pcs,
                               "✅" if b.v_account_used else "❌", b.notes or ""] for b in batches])

    def _add(self):
        dlg = FacetingDialog(self, self._workers, self._teams)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_faceting_batch(**dlg.get_data())).start()
            Toast.show_toast(self, "Faceting batch created.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = FacetingDialog(self, self._workers, self._teams, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.update_faceting_batch(bid, **dlg.get_data())).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this faceting batch?"):
            DBWorker(lambda: ProcessService.delete_faceting_batch(bid)).start(); self._load()


class FacetingDialog(QDialog):
    def __init__(self, parent, workers, teams, batch=None):
        super().__init__(parent); self.setWindowTitle("Faceting Batch")
        self.setFixedSize(440, 480); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)
        self._from = QDateEdit(); self._from.setCalendarPopup(True)
        self._from.setDate(QDate.fromString(str(batch.from_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._to = QDateEdit(); self._to.setCalendarPopup(True)
        self._to.setDate(QDate.fromString(str(batch.to_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._worker = QComboBox()
        self._worker_ids = [None] + [w.id for w in workers]
        self._worker.addItems(["— none —"] + [f"{w.code}" for w in workers])
        self._team = QComboBox()
        self._team_ids = [None] + [t.id for t in teams]
        self._team.addItems(["— none —"] + [t.name for t in teams])
        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(batch.weight_in_g if batch else 0)
        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0,999999); self._wt_out.setDecimals(3)
        self._wt_out.setValue(batch.weight_out_g if batch else 0)
        self._fin_pcs = QSpinBox(); self._fin_pcs.setRange(0, 999999)
        self._fin_pcs.setValue(batch.fin_pcs if batch else 0)
        self._act_pcs = QSpinBox(); self._act_pcs.setRange(0, 999999)
        self._act_pcs.setValue(batch.act_fin_pcs if batch else 0)
        self._ree_cu = QSpinBox(); self._ree_cu.setRange(0, 999999)
        self._ree_cu.setValue(batch.ree_cu if batch else 0)
        self._v_acc = QCheckBox("Use V Account")
        self._v_acc.setChecked(batch.v_account_used if batch else True)
        self._notes = QLineEdit(batch.notes or "" if batch else "")
        for lbl, w in [("From Date *", self._from), ("To Date *", self._to),
                        ("Worker", self._worker), ("Team", self._team),
                        ("Wt In (g) *", self._wt_in), ("Wt Out (g) *", self._wt_out),
                        ("Fin Pcs", self._fin_pcs), ("Act Fin Pcs", self._act_pcs),
                        ("REE CU", self._ree_cu), ("", self._v_acc), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "from_date": self._from.date().toPyDate(), "to_date": self._to.date().toPyDate(),
            "worker_id": self._worker_ids[self._worker.currentIndex()],
            "team_id": self._team_ids[self._team.currentIndex()],
            "weight_in_g": self._wt_in.value(), "weight_out_g": self._wt_out.value(),
            "fin_pcs": self._fin_pcs.value(), "act_fin_pcs": self._act_pcs.value(),
            "ree_cu": self._ree_cu.value(), "v_account_used": self._v_acc.isChecked(),
            "notes": self._notes.text() or None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Kambi
# ─────────────────────────────────────────────────────────────────────────────
class KambiPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []; self._workers = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("🔩  KAMBI — Linking Process")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Kambi Batch")
        add_btn.setObjectName("BtnPrimary"); add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(["ID","Date","Wt In (g)","Wt Out (g)","Loss (g)",
                                  "GB Drawn (g)","Returned (g)","Chains","Hooks","Notes"])
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary"); edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger"); del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        DBWorker(MasterService.get_workers).result.connect(lambda w: setattr(self, '_workers', w))
        self._load()

    def _load(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_kambi_batches)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay(); self._batches = batches
        self._table.populate([[b.id, fmt_date(b.batch_date),
                               fmt_weight(b.weight_in_g), fmt_weight(b.weight_out_g), fmt_weight(b.loss_g),
                               fmt_weight(b.gold_box_drawn_g), fmt_weight(b.gold_returned_g),
                               b.chains_linked, b.hooks_used, b.notes or ""] for b in batches])

    def _add(self):
        dlg = KambiDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.create_kambi_batch(**dlg.get_data())).start()
            Toast.show_toast(self, "Kambi batch created.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a batch.", "warning")
        bid = int(self._table.item(row, 0).text())
        batch = next((b for b in self._batches if b.id == bid), None)
        if not batch: return
        dlg = KambiDialog(self, batch)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: ProcessService.update_kambi_batch(bid, **dlg.get_data())).start()
            Toast.show_toast(self, "Updated.", "success"); self._load()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0: return
        bid = int(self._table.item(row, 0).text())
        if ConfirmDialog.ask(self, "Delete", "Delete this kambi batch?"):
            DBWorker(lambda: ProcessService.delete_kambi_batch(bid)).start(); self._load()


class KambiDialog(QDialog):
    def __init__(self, parent, batch=None):
        super().__init__(parent); self.setWindowTitle("Kambi Batch")
        self.setFixedSize(420, 420); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True)
        self._date.setDate(QDate.fromString(str(batch.batch_date), "yyyy-MM-dd") if batch else QDate.currentDate())
        self._wt_in = QDoubleSpinBox(); self._wt_in.setRange(0,999999); self._wt_in.setDecimals(3)
        self._wt_in.setValue(batch.weight_in_g if batch else 0)
        self._wt_out = QDoubleSpinBox(); self._wt_out.setRange(0,999999); self._wt_out.setDecimals(3)
        self._wt_out.setValue(batch.weight_out_g if batch else 0)
        self._gb_drawn = QDoubleSpinBox(); self._gb_drawn.setRange(0,999999); self._gb_drawn.setDecimals(3)
        self._gb_drawn.setValue(batch.gold_box_drawn_g if batch else 0)
        self._returned = QDoubleSpinBox(); self._returned.setRange(0,999999); self._returned.setDecimals(3)
        self._returned.setValue(batch.gold_returned_g if batch else 0)
        self._chains = QSpinBox(); self._chains.setRange(0, 999999)
        self._chains.setValue(batch.chains_linked if batch else 0)
        self._hooks = QSpinBox(); self._hooks.setRange(0, 999999)
        self._hooks.setValue(batch.hooks_used if batch else 0)
        self._solder = QDoubleSpinBox(); self._solder.setRange(0,999999); self._solder.setDecimals(3)
        self._solder.setValue(batch.solder_weight_g if batch else 0)
        self._notes = QLineEdit(batch.notes or "" if batch else "")
        for lbl, w in [("Date *", self._date), ("Wt In (g) *", self._wt_in),
                        ("Wt Out (g) *", self._wt_out), ("GB Drawn (g)", self._gb_drawn),
                        ("Gold Returned (g)", self._returned), ("Chains Linked", self._chains),
                        ("Hooks Used", self._hooks), ("Solder (g)", self._solder), ("Notes", self._notes)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"batch_date": self._date.date().toPyDate(), "weight_in_g": self._wt_in.value(),
                "weight_out_g": self._wt_out.value(), "gold_box_drawn_g": self._gb_drawn.value(),
                "gold_returned_g": self._returned.value(), "chains_linked": self._chains.value(),
                "hooks_used": self._hooks.value(), "solder_weight_g": self._solder.value(),
                "notes": self._notes.text() or None}
