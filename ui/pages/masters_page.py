"""Masters page — Dealers, Workers, Teams, Product/Design/Alloy Types."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QDialog, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt
from ui.pages.base_page import BasePage
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.master_service import MasterService
from utils.formatters import fmt_date


class MastersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("🗂  MASTERS")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(DealersTab(), "🏅  Dealers")
        tabs.addTab(WorkersTab(), "👷  Workers")
        tabs.addTab(TeamsTab(), "🤝  Teams")
        tabs.addTab(TypesTab(), "🏷  Types")
        layout.addWidget(tabs)


# ─── Dealers Tab ──────────────────────────────────────────────────────────────
class DealersTab(QWidget):
    COLS = ["ID", "Code", "Name", "Phone", "GSTIN", "Active", "Created"]

    def __init__(self):
        super().__init__()
        self._rows_raw = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self._search = SearchBar("Search dealers…")
        self._search.textChanged.connect(self._filter)
        add_btn = QPushButton("＋  Add Dealer")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(self._search, 1)
        bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(self.COLS)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel("")
        self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        edit_btn = QPushButton("✏  Edit")
        edit_btn.setObjectName("BtnSecondary")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("🔘  Toggle Active")
        del_btn.setObjectName("BtnDanger")
        del_btn.clicked.connect(self._toggle)
        act.addWidget(self._cnt); act.addStretch()
        act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(MasterService.get_dealers)
        w.result.connect(self._on_data); w.error.connect(self._on_err); w.start()

    def _on_data(self, dealers):
        self._overlay.hide_overlay()
        self._dealers = dealers
        self._rows_raw = [
            [d.id, d.code, d.name, d.phone or "—", d.gstin or "—",
             "✅" if d.is_active else "❌", fmt_date(d.created_at)]
            for d in dealers
        ]
        self._table.populate(self._rows_raw)
        self._cnt.setText(f"{len(dealers)} dealers")

    def _filter(self, text):
        t = text.lower()
        filtered = [r for r in self._rows_raw if any(t in str(v).lower() for v in r)]
        self._table.populate(filtered)

    def _add(self):
        dlg = DealerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                DBWorker(lambda: MasterService.create_dealer(**d)).start()
                Toast.show_toast(self, "Dealer added successfully.", "success")
                self._load()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a dealer.", "warning")
        dealer_id = int(self._table.item(row, 0).text())
        dealer = next((d for d in self._dealers if d.id == dealer_id), None)
        if not dealer: return
        dlg = DealerDialog(self, dealer)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            DBWorker(lambda: MasterService.update_dealer(dealer_id, **data)).start()
            Toast.show_toast(self, "Dealer updated.", "success")
            self._load()

    def _toggle(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a dealer.", "warning")
        dealer_id = int(self._table.item(row, 0).text())
        DBWorker(lambda: MasterService.toggle_dealer_active(dealer_id)).start()
        Toast.show_toast(self, "Status toggled.", "info")
        self._load()

    def _on_err(self, msg): Toast.show_toast(self, msg, "error"); self._overlay.hide_overlay()


class DealerDialog(QDialog):
    def __init__(self, parent, dealer=None):
        super().__init__(parent)
        self.setWindowTitle("Dealer" if not dealer else "Edit Dealer")
        self.setFixedSize(400, 300)
        self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)

        self._code  = QLineEdit(dealer.code if dealer else "")
        self._name  = QLineEdit(dealer.name if dealer else "")
        self._phone = QLineEdit(dealer.phone or "" if dealer else "")
        self._gstin = QLineEdit(dealer.gstin or "" if dealer else "")

        for label, widget in [("Code *", self._code), ("Name *", self._name),
                               ("Phone", self._phone), ("GSTIN", self._gstin)]:
            lbl = QLabel(label); lbl.setObjectName("FieldLabel")
            form.addRow(lbl, widget)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"code": self._code.text().strip(), "name": self._name.text().strip(),
                "phone": self._phone.text().strip() or None,
                "gstin": self._gstin.text().strip() or None}


# ─── Workers Tab ──────────────────────────────────────────────────────────────
class WorkersTab(QWidget):
    COLS = ["ID", "Code", "Name", "Process", "Pay Type", "Rate/Chain", "Active"]

    def __init__(self):
        super().__init__()
        self._workers_data = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self._search = SearchBar("Search workers…")
        self._search.textChanged.connect(self._filter)
        add_btn = QPushButton("＋  Add Worker")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(self._search, 1); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(self.COLS)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel("")
        self._cnt.setStyleSheet("color:#4A5568;font-size:12px;")
        edit_btn = QPushButton("✏  Edit")
        edit_btn.setObjectName("BtnSecondary")
        edit_btn.clicked.connect(self._edit)
        tog_btn = QPushButton("🔘  Toggle")
        tog_btn.setObjectName("BtnDanger")
        tog_btn.clicked.connect(self._toggle)
        act.addWidget(self._cnt); act.addStretch()
        act.addWidget(edit_btn); act.addWidget(tog_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self._load()

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(MasterService.get_workers)
        w.result.connect(self._on_data); w.error.connect(lambda m: (self._overlay.hide_overlay(), Toast.show_toast(self, m, "error"))); w.start()

    def _on_data(self, workers):
        self._overlay.hide_overlay()
        self._workers_data = workers
        rows = [[w.id, w.code, w.name, w.process_type, w.pay_type,
                 f"{w.rate_per_chain:.2f}", "✅" if w.is_active else "❌"]
                for w in workers]
        self._table.populate(rows)
        self._cnt.setText(f"{len(workers)} workers")

    def _filter(self, text):
        t = text.lower()
        rows = [[w.id, w.code, w.name, w.process_type, w.pay_type,
                 f"{w.rate_per_chain:.2f}", "✅" if w.is_active else "❌"]
                for w in self._workers_data if t in w.name.lower() or t in w.code.lower()]
        self._table.populate(rows)

    def _add(self):
        dlg = WorkerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                DBWorker(lambda: MasterService.create_worker(**dlg.get_data())).start()
                Toast.show_toast(self, "Worker added.", "success"); self._load()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a worker.", "warning")
        wid = int(self._table.item(row, 0).text())
        worker = next((w for w in self._workers_data if w.id == wid), None)
        if not worker: return
        dlg = WorkerDialog(self, worker)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            DBWorker(lambda: MasterService.update_worker(wid, **dlg.get_data())).start()
            Toast.show_toast(self, "Worker updated.", "success"); self._load()

    def _toggle(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a worker.", "warning")
        wid = int(self._table.item(row, 0).text())
        DBWorker(lambda: MasterService.toggle_worker_active(wid)).start()
        Toast.show_toast(self, "Status toggled.", "info"); self._load()


class WorkerDialog(QDialog):
    PROCESS_TYPES = ["GOLDSMITH", "FACETING", "KAMBI", "MELTING", "WIRE_SHEET", "HALLMARKING"]
    PAY_TYPES = ["PER_CHAIN", "MONTHLY"]

    def __init__(self, parent, worker=None):
        super().__init__(parent)
        self.setWindowTitle("Worker")
        self.setFixedSize(420, 340)
        self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)

        self._code = QLineEdit(worker.code if worker else "")
        self._name = QLineEdit(worker.name if worker else "")
        self._phone = QLineEdit(worker.phone or "" if worker else "")
        self._process = QComboBox()
        self._process.addItems(self.PROCESS_TYPES)
        if worker: self._process.setCurrentText(worker.process_type)
        self._pay = QComboBox()
        self._pay.addItems(self.PAY_TYPES)
        if worker: self._pay.setCurrentText(worker.pay_type)
        self._rate = QDoubleSpinBox()
        self._rate.setRange(0, 9999); self._rate.setDecimals(2)
        self._rate.setValue(worker.rate_per_chain if worker else 0.0)

        for lbl, w in [("Code *", self._code), ("Name *", self._name),
                        ("Phone", self._phone), ("Process Type", self._process),
                        ("Pay Type", self._pay), ("Rate/Chain ₹", self._rate)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel")
            form.addRow(l, w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {"code": self._code.text().strip(), "name": self._name.text().strip(),
                "phone": self._phone.text().strip() or None,
                "process_type": self._process.currentText(),
                "pay_type": self._pay.currentText(),
                "rate_per_chain": self._rate.value()}


# ─── Teams Tab ────────────────────────────────────────────────────────────────
class TeamsTab(QWidget):
    COLS = ["ID", "Name", "Process Type", "Team Lead", "Created"]

    def __init__(self):
        super().__init__()
        self._teams = []; self._workers = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        info = QLabel("⚠  A team without a Team Lead cannot be credited/debited in "
                       "V Account, Goldsmith, Polish, or Wire & Sheet — set one here.")
        info.setStyleSheet("color:#F5A623; font-size:12px; font-style:italic;")
        layout.addWidget(info)

        bar = QHBoxLayout()
        add_btn = QPushButton("＋  Add Team")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        bar.addStretch(); bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._table = DataTable(self.COLS)
        layout.addWidget(self._table, 1)

        act = QHBoxLayout()
        edit_btn = QPushButton("✏  Edit"); edit_btn.setObjectName("BtnSecondary")
        edit_btn.clicked.connect(self._edit)
        act.addStretch(); act.addWidget(edit_btn)
        layout.addLayout(act)

        self._overlay = LoadingOverlay(self)
        w = DBWorker(MasterService.get_workers)
        w.result.connect(self._on_workers)
        w.start()
        self._load()

    def _on_workers(self, workers):
        self._workers = workers

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(MasterService.get_teams)
        w.result.connect(self._on_data); w.error.connect(lambda m: self._overlay.hide_overlay()); w.start()

    def _on_data(self, teams):
        self._overlay.hide_overlay(); self._teams = teams
        lead_names = {w.id: w.name for w in self._workers}
        self._table.populate([[
            t.id, t.name, t.process_type,
            lead_names.get(t.team_lead_id, "— none —") if t.team_lead_id else "— none —",
            fmt_date(t.created_at)] for t in teams])

    def _add(self):
        dlg = TeamDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: MasterService.create_team(**d)).start()
            Toast.show_toast(self, "Team added.", "success"); self._load()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0: return Toast.show_toast(self, "Select a team.", "warning")
        tid = int(self._table.item(row, 0).text())
        team = next((t for t in self._teams if t.id == tid), None)
        if not team: return
        dlg = TeamDialog(self, self._workers, team)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            DBWorker(lambda: MasterService.update_team(tid, **d)).start()
            Toast.show_toast(self, "Team updated.", "success"); self._load()


class TeamDialog(QDialog):
    PROCESS_TYPES = ["GOLDSMITH", "FACETING", "POLISH", "WIRE_SHEET"]

    def __init__(self, parent, workers, team=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Team" if team else "New Team")
        self.setFixedSize(360, 240); self.setModal(True)
        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20); form.setSpacing(12)
        self._name = QLineEdit(team.name if team else "")
        self._pt = QComboBox(); self._pt.addItems(self.PROCESS_TYPES)
        if team and team.process_type in self.PROCESS_TYPES:
            self._pt.setCurrentText(team.process_type)
        self._lead = QComboBox()
        self._lead_ids = [None] + [w.id for w in workers]
        self._lead.addItems(["— none —"] + [f"{w.code} — {w.name}" for w in workers])
        if team and team.team_lead_id in self._lead_ids:
            self._lead.setCurrentIndex(self._lead_ids.index(team.team_lead_id))
        for lbl, w in [("Name *", self._name), ("Process Type", self._pt), ("Team Lead", self._lead)]:
            l = QLabel(lbl); l.setObjectName("FieldLabel"); form.addRow(l, w)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        name = self._name.text().strip()
        return {"name": name, "team_name": name, "process_type": self._pt.currentText(),
                "team_lead_id": self._lead_ids[self._lead.currentIndex()]}


# ─── Types Tab ────────────────────────────────────────────────────────────────
class TypesTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        tabs = QTabWidget()
        tabs.addTab(self._make_tab("Product Types", MasterService.get_product_types,
                                   ["ID","Code","Name"]), "Products")
        tabs.addTab(self._make_tab("Design Types", MasterService.get_design_types,
                                   ["ID","Code","Name"]), "Designs")
        tabs.addTab(self._make_tab("Alloy Types", MasterService.get_alloy_types,
                                   ["ID","Code","Name"]), "Alloys")
        layout.addWidget(tabs)

    def _make_tab(self, title, fetch_fn, cols):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        table = DataTable(cols)
        layout.addWidget(table)
        overlay = LoadingOverlay(w)
        overlay.show_over(w)
        worker = DBWorker(fetch_fn)
        worker.result.connect(lambda items, t=table, o=overlay: (
            o.hide_overlay(),
            t.populate([[i.id, i.code, i.name] for i in items])
        ))
        worker.start()
        return w
