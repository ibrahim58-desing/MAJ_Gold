"""V Account page — virtual account entries for faceting workers."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QDateEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLineEdit, QFrame, QTabWidget, QTextEdit,
    QMessageBox
)
from PyQt6.QtCore import QDate
from ui.widgets.widgets import DataTable, Toast, LoadingOverlay, ConfirmDialog
from ui.widgets.process_widgets import ChainTallyWidget
from workers.db_worker import DBWorker
from services.v_account_service import VAccountService
from services.master_service import MasterService
from services.complaint_service import (
    create_complaint, send_to_goldsmith, record_goldsmith_return_for_complaint,
    get_all_complaints,
)
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

        tabs = QTabWidget()
        self._entries_tab = VEntriesTab()
        self._balance_tab = VBalanceTab()
        self._complaints_tab = ComplaintsTab()
        tabs.addTab(self._entries_tab, "📋  Entries")
        tabs.addTab(self._balance_tab, "📊  Daily Balance")
        tabs.addTab(self._complaints_tab, "⚠  Complaints")
        layout.addWidget(tabs)

        w = DBWorker(MasterService.get_workers)
        w.result.connect(self._on_workers)
        w.start()

    def _on_workers(self, workers):
        self._workers = workers
        self._entries_tab.set_workers(workers)
        self._complaints_tab.set_workers(workers)

    def refresh(self):
        self._entries_tab._load()
        self._balance_tab._load()
        self._complaints_tab._load()


class VEntriesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []; self._entries = []
        layout = QVBoxLayout(self); layout.setContentsMargins(10,10,10,10); layout.setSpacing(10)
        bar = QHBoxLayout()
        wf = QComboBox(); wf.addItem("All Workers"); wf.setFixedWidth(200)
        wf.currentIndexChanged.connect(self._filter_worker); self._wf = wf
        manual_btn = QPushButton("＋  Manual Entry"); manual_btn.setObjectName("BtnSecondary")
        manual_btn.clicked.connect(self._add_manual)
        batch_btn = QPushButton("＋  New Batch"); batch_btn.setObjectName("BtnPrimary")
        batch_btn.clicked.connect(self._add_new_batch)
        bar.addWidget(wf); bar.addStretch()
        bar.addWidget(manual_btn); bar.addWidget(batch_btn)
        layout.addLayout(bar)
        cols = ["ID","Date","Worker","Particular","Debit (g)","Dr Pcs","Credit (g)","Cr Pcs",
                "Balance","Source","Status"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)
        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit (Faceting Return)"); edit_btn.setObjectName("BtnSecondary")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🗑  Delete"); del_btn.setObjectName("BtnDanger")
        del_btn.clicked.connect(self._delete)
        act.addStretch(); act.addWidget(edit_btn); act.addWidget(del_btn)
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
            e.credit_pcs or "—", f"{e.balance_g:.3f}",
            e.source_type or "MANUAL", e.status or "closed"] for e in entries])

    def _add_manual(self):
        prev = float(self._entries[-1].balance_g) if self._entries else 0.0
        dlg = VEntryDialog(self, self._workers, prev)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: VAccountService.create_entry(**dlg.get_data())).start()
            Toast.show_toast(self, "Entry added.", "success"); self._load()

    def _add_new_batch(self):
        if not self._workers:
            return Toast.show_toast(self, "No workers loaded yet.", "warning")
        dlg = NewBatchDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            batch_type = data.pop("type")
            if batch_type == "FACETING":
                fn = lambda: VAccountService.create_manual_faceting_entry(**data)
                msg = "Faceting entry recorded (pending return)."
            else:
                fn = lambda: VAccountService.create_wire_draw_entry(**data)
                msg = "Wire draw recorded."
            w = DBWorker(fn)
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            w.result.connect(lambda _: (Toast.show_toast(self, msg, "success"), self._load()))
            w.start()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select an entry.", "warning")
        eid = int(self._table.item(row, 0).text())
        entry = next((e for e in self._entries if e.id == eid), None)
        if not entry: return
        if entry.source_type != "FACETING" or entry.status != "open":
            return Toast.show_toast(self, "Only an open Faceting entry can be edited.", "warning")
        dlg = FacetingReturnDialog(self, entry)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            def _run():
                return VAccountService.close_faceting_entry(**data)
            w = DBWorker(_run)
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            def _done(res):
                if res.get("loss_alert"):
                    Toast.show_toast(self, f"Faceting loss is {res['loss_pct']:.2f}% — please verify.", "warning")
                else:
                    Toast.show_toast(self, "Faceting return recorded.", "success")
                self._load()
            w.result.connect(_done)
            w.start()

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


class NewBatchDialog(QDialog):
    """Single entry point for both Faceting- and Wire-sourced gold, entered
    by hand (worker reports pics/weight — no linkage to a specific batch
    record). Faceting carries the Baby/Normal/30" chain tally; Wire is
    weight-only and stays open until its return weight is later Edited."""

    def __init__(self, parent, workers):
        super().__init__(parent); self.setWindowTitle("New Batch")
        self.setFixedSize(420, 520); self.setModal(True)
        self._worker_ids = [w.id for w in workers]
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)

        self._type = QComboBox(); self._type.addItems(["FACETING", "WIRE"])
        self._type.currentTextChanged.connect(self._on_type_changed)
        l = QLabel("Type *"); l.setObjectName("FieldLabel"); form.addRow(l, self._type)

        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        l = QLabel("Date *"); l.setObjectName("FieldLabel"); form.addRow(l, self._date)

        self._worker = QComboBox(); self._worker.addItems([f"{w.code} — {w.name}" for w in workers])
        l = QLabel("Worker *"); l.setObjectName("FieldLabel"); form.addRow(l, self._worker)

        self._weight = QDoubleSpinBox(); self._weight.setRange(0, 999999); self._weight.setDecimals(3)
        l = QLabel("Weight (g) *"); l.setObjectName("FieldLabel"); form.addRow(l, self._weight)

        self._tally_label = QLabel("Chain Length — click to tally *"); self._tally_label.setObjectName("FieldLabel")
        form.addRow(self._tally_label)
        self._tally = ChainTallyWidget()
        form.addRow(self._tally)

        self._notes = QLineEdit()
        l = QLabel("Notes"); l.setObjectName("FieldLabel"); form.addRow(l, self._notes)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def _on_type_changed(self, type_text):
        is_faceting = type_text == "FACETING"
        self._tally_label.setVisible(is_faceting)
        self._tally.setVisible(is_faceting)

    def _validate_and_accept(self):
        if self._weight.value() <= 0 or not self._worker_ids:
            QMessageBox.warning(self, "Error", "Select a worker and enter a weight > 0"); return
        if self._type.currentText() == "FACETING" and self._tally.total_pcs() == 0:
            QMessageBox.warning(self, "Error", "Tally at least one piece (Baby / Normal / 30 Inch)."); return
        self.accept()

    def get_data(self):
        data = {
            "type": self._type.currentText(),
            "entry_date": self._date.date().toPyDate(),
            "worker_id": self._worker_ids[self._worker.currentIndex()],
            "weight_g": self._weight.value(),
            "notes": self._notes.text() or None,
        }
        if data["type"] == "FACETING":
            counts = self._tally.counts
            data["qty_baby"] = counts["baby"]
            data["qty_normal"] = counts["normal"]
            data["qty_30inch"] = counts["30inch"]
        return data


class FacetingReturnDialog(QDialog):
    def __init__(self, parent, entry):
        super().__init__(parent); self.setWindowTitle(f"Faceting Return — Entry #{entry.id}")
        self.setFixedSize(380, 260); self.setModal(True)
        self._entry_id = entry.id
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        lbl = QLabel(f"Issued: {entry.debit_g:.3f} g"); lbl.setObjectName("FieldLabel")
        form.addRow(lbl)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._returned = QDoubleSpinBox(); self._returned.setRange(0, 999999); self._returned.setDecimals(3)
        self._returned.setMaximum(entry.debit_g)
        self._notes = QLineEdit()
        for lbl2, w in [("Return Date *", self._date), ("Returned Weight (g) *", self._returned),
                         ("Notes", self._notes)]:
            l = QLabel(lbl2); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def get_data(self):
        return {"entry_id": self._entry_id, "return_date": self._date.date().toPyDate(),
                "returned_weight_g": self._returned.value(), "notes": self._notes.text() or None}


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


class ComplaintsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []; self._complaints = []
        layout = QVBoxLayout(self); layout.setContentsMargins(10,10,10,10); layout.setSpacing(10)

        info = QLabel("Small gold-quality issues on a worker's item — sent to Goldsmith for rework.")
        info.setStyleSheet("color:#4A5568; font-size:12px; font-style:italic;")
        layout.addWidget(info)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  New Complaint"); add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        cols = ["ID","Date","Worker","Description","Wt Sent (g)","Chain Tally","Status","Loss %"]
        self._table = DataTable(cols)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        send_btn = QPushButton("📤  Send to Goldsmith"); send_btn.setObjectName("BtnSecondary")
        send_btn.clicked.connect(self._send)
        return_btn = QPushButton("📥  Record Goldsmith Return"); return_btn.setObjectName("BtnPrimary")
        return_btn.clicked.connect(self._record_return)
        act.addStretch(); act.addWidget(send_btn); act.addWidget(return_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self); self._load()

    def set_workers(self, workers):
        self._workers = workers

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(get_all_complaints)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, complaints):
        self._overlay.hide_overlay(); self._complaints = complaints
        self._table.populate([[
            c.id, fmt_date(c.complaint_date), c.worker.name if c.worker else "—",
            c.description or "", f"{c.weight_sent_g:.3f}",
            f"Baby:{c.qty_baby} Normal:{c.qty_normal} 30\":{c.qty_30inch}",
            c.status,
            f"{c.loss_pct:.2f}%" if c.status == "resolved" else "—"] for c in complaints])

    def _add(self):
        if not self._workers:
            return Toast.show_toast(self, "No workers loaded yet.", "warning")
        dlg = ComplaintDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            w = DBWorker(lambda: create_complaint(**data))
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            w.result.connect(lambda _: (Toast.show_toast(self, "Complaint recorded.", "success"), self._load()))
            w.start()

    def _selected(self):
        row = self._table.currentRow()
        if row < 0:
            Toast.show_toast(self, "Select a complaint.", "warning"); return None
        cid = int(self._table.item(row, 0).text())
        return next((c for c in self._complaints if c.id == cid), None)

    def _send(self):
        c = self._selected()
        if not c: return
        if c.status != "open":
            return Toast.show_toast(self, "Complaint already sent.", "warning")
        w = DBWorker(lambda: send_to_goldsmith(c.id))
        w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
        w.result.connect(lambda _: (Toast.show_toast(self, "Sent to Goldsmith.", "success"), self._load()))
        w.start()

    def _record_return(self):
        c = self._selected()
        if not c: return
        if c.status != "sent_to_goldsmith":
            return Toast.show_toast(self, "Complaint is not awaiting a goldsmith return.", "warning")
        dlg = ComplaintReturnDialog(self, c)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            w = DBWorker(lambda: record_goldsmith_return_for_complaint(c.id, data))
            w.error.connect(lambda m: Toast.show_toast(self, f"Failed: {m}", "error"))
            def _done(res):
                if res.get("loss_alert"):
                    Toast.show_toast(self, f"Goldsmith loss is {res['loss_pct']:.2f}% — please verify.", "warning")
                else:
                    Toast.show_toast(self, "Goldsmith return recorded.", "success")
                self._load()
            w.result.connect(_done)
            w.start()


class ComplaintDialog(QDialog):
    def __init__(self, parent, workers):
        super().__init__(parent); self.setWindowTitle("New Complaint")
        self.setFixedSize(400, 500); self.setModal(True)
        self._worker_ids = [w.id for w in workers]
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        self._worker = QComboBox(); self._worker.addItems([f"{w.code} — {w.name}" for w in workers])
        self._desc = QLineEdit()
        self._weight = QDoubleSpinBox(); self._weight.setRange(0, 999999); self._weight.setDecimals(3)
        for lbl, w in [("Date *", self._date), ("Worker *", self._worker),
                        ("Description *", self._desc), ("Weight Sent (g) *", self._weight)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)

        l = QLabel("Chain Length — click to tally *"); l.setObjectName("FieldLabel"); form.addRow(l)
        self._tally = ChainTallyWidget()
        form.addRow(self._tally)

        self._notes = QLineEdit()
        l = QLabel("Notes"); l.setObjectName("FieldLabel"); form.addRow(l, self._notes)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def _validate_and_accept(self):
        if self._weight.value() <= 0 or not self._desc.text().strip():
            QMessageBox.warning(self, "Error", "Enter a description and a weight sent > 0"); return
        if self._tally.total_pcs() == 0:
            QMessageBox.warning(self, "Error", "Tally at least one piece (Baby / Normal / 30 Inch)."); return
        self.accept()

    def get_data(self):
        counts = self._tally.counts
        return {"complaint_date": self._date.date().toPyDate(),
                "worker_id": self._worker_ids[self._worker.currentIndex()],
                "description": self._desc.text().strip(),
                "weight_sent_g": self._weight.value(),
                "qty_baby": counts["baby"], "qty_normal": counts["normal"], "qty_30inch": counts["30inch"],
                "notes": self._notes.text() or None}


class ComplaintReturnDialog(QDialog):
    def __init__(self, parent, complaint):
        super().__init__(parent); self.setWindowTitle(f"Goldsmith Return — Complaint #{complaint.id}")
        self.setFixedSize(400, 460); self.setModal(True)
        form = QFormLayout(self); form.setContentsMargins(20,20,20,20); form.setSpacing(10)
        lbl = QLabel(f"Sent to Goldsmith: {complaint.weight_sent_g:.3f} g"); lbl.setObjectName("FieldLabel")
        form.addRow(lbl)
        self._date = QDateEdit(); self._date.setCalendarPopup(True); self._date.setDate(QDate.currentDate())
        l = QLabel("Return Date *"); l.setObjectName("FieldLabel"); form.addRow(l, self._date)

        l = QLabel("Chain Length — click to tally *"); l.setObjectName("FieldLabel"); form.addRow(l)
        self._tally = ChainTallyWidget()
        form.addRow(self._tally)

        self._weight = QDoubleSpinBox(); self._weight.setRange(0, 999999); self._weight.setDecimals(3)
        l = QLabel("Total Weight (g) *"); l.setObjectName("FieldLabel"); form.addRow(l, self._weight)

        self._notes = QLineEdit()
        l = QLabel("Notes"); l.setObjectName("FieldLabel"); form.addRow(l, self._notes)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept); btns.rejected.connect(self.reject); form.addRow(btns)

    def _validate_and_accept(self):
        if self._tally.total_pcs() == 0:
            QMessageBox.warning(self, "Error", "Tally at least one piece (Baby / Normal / 30 Inch)."); return
        self.accept()

    def get_data(self):
        counts = self._tally.counts
        return {
            "return_date": self._date.date().toPyDate(),
            "pcs": self._tally.total_pcs(),
            "total_inches": self._tally.total_inches(),
            "qty_baby": counts["baby"], "qty_normal": counts["normal"], "qty_30inch": counts["30inch"],
            "weight_g": self._weight.value(),
            "notes": f"Baby: {counts['baby']}, Normal: {counts['normal']}, 30 Inch: {counts['30inch']}"
                     + (f" — {self._notes.text()}" if self._notes.text() else ""),
        }
