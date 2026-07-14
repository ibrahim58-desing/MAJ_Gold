"""Goldsmith UI — Issue Gold, Track Returns, Teams."""
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QDoubleSpinBox, QTextEdit, QDialog, QFrame,
    QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from services.goldsmith_service import (
    get_totals, get_all_issues, get_all_teams,
    create_issue, record_return, create_team, add_team_member
)
from utils.formatters import fmt_weight
from ui.widgets.process_widgets import ChainTallyWidget, WorkerTeamSelector
from ui.widgets.widgets import StatCard, DataTable, Toast


class _GoldCard(QFrame):
    def __init__(self, title=None):
        super().__init__()
        self.setObjectName("CardGold")
        self.inner = QVBoxLayout(self)
        self.inner.setContentsMargins(16, 14, 16, 16)
        self.inner.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("SectionTitle")
            self.inner.addWidget(lbl)


class GoldsmithUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # header
        title = QLabel("⚒  GOLDSMITH OPERATIONS")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        root.addWidget(title)

        self._build_stock_summary(root)
        self._build_issues_table(root)

    def _build_stock_summary(self, parent_layout):
        ly = QVBoxLayout()
        ly.setSpacing(10)

        lbl = QLabel("Ready for Issue (From Wire & Sheet)")
        lbl.setObjectName("SectionTitle")
        ly.addWidget(lbl)

        cards = QHBoxLayout()
        self.c_dye = StatCard("Dye Available (g)", "0.000", icon="🧪", color="#2ED573")
        self.c_wire = StatCard("Wire Available (g)", "0.000", icon="🔗", color="#2ED573")
        self.c_strips = StatCard("Strips Available (g)", "0.000", icon="📏", color="#2ED573")
        self.c_loss = StatCard("Total GS Loss (g)", "0.000", icon="⚠", color="#FF4757", accent=True)

        cards.addWidget(self.c_dye)
        cards.addWidget(self.c_wire)
        cards.addWidget(self.c_strips)
        cards.addWidget(self.c_loss)
        ly.addLayout(cards)

        parent_layout.addLayout(ly)

    def _build_issues_table(self, parent_layout):
        ly = QVBoxLayout()

        top = QHBoxLayout()
        btn_new = QPushButton("＋  New Issue")
        btn_new.setObjectName("BtnPrimary")
        btn_new.clicked.connect(self._on_new_issue)
        top.addStretch()
        top.addWidget(btn_new)
        ly.addLayout(top)

        self.t_issues = DataTable([
            "ID", "Date", "Type", "Team/Worker", "Dye", "Wire",
            "Strips", "Issued", "Ret Pcs", "Ret Ins", "Ret Wt", "Loss(g)", "Status", "Loss%", "Actions"
        ])
        ly.addWidget(self.t_issues)
        parent_layout.addLayout(ly)

    def _load(self):
        self._load_stock()
        self._load_issues()

    def _load_stock(self):
        totals = get_totals()
        self.c_dye.set_value(f"{totals['total_dye_available_g']:.3f}")
        self.c_wire.set_value(f"{totals['total_wire_available_g']:.3f}")
        self.c_strips.set_value(f"{totals['total_strips_available_g']:.3f}")
        self.c_loss.set_value(f"{totals['total_loss_g']:.3f}")

    def _load_issues(self):
        issues = get_all_issues()
        self.t_issues.setSortingEnabled(False)
        self.t_issues.setRowCount(len(issues))
        for row, i in enumerate(issues):
            self.t_issues.setRowHeight(row, 44)
            self.t_issues.setItem(row, 0, QTableWidgetItem(f"#{i['id']}"))
            self.t_issues.setItem(row, 1, QTableWidgetItem(i['issue_date'].strftime("%d-%m-%Y")))
            self.t_issues.setItem(row, 2, QTableWidgetItem(i['issue_type']))
            self.t_issues.setItem(row, 3, QTableWidgetItem(i['target_name']))

            self.t_issues.setItem(row, 4, QTableWidgetItem(fmt_weight(i['dye_issued_g'])))
            self.t_issues.setItem(row, 5, QTableWidgetItem(fmt_weight(i['wire_issued_g'])))
            self.t_issues.setItem(row, 6, QTableWidgetItem(fmt_weight(i['strips_issued_g'])))

            t_iss = QTableWidgetItem(fmt_weight(i['total_issued_g']))
            t_iss.setForeground(QColor("#2ED573"))
            self.t_issues.setItem(row, 7, t_iss)

            if i['status'] == 'returned':
                self.t_issues.setItem(row, 8, QTableWidgetItem(str(i.get('return_pcs', '—'))))
                self.t_issues.setItem(row, 9, QTableWidgetItem(f"{i.get('return_inches', 0):.2f}"))
                self.t_issues.setItem(row, 10, QTableWidgetItem(fmt_weight(i.get('return_weight_g', 0))))

                l_g = QTableWidgetItem(fmt_weight(i.get('loss_g', 0)))
                l_g.setForeground(QColor("#FF4757"))
                self.t_issues.setItem(row, 11, l_g)
            else:
                for col in (8, 9, 10, 11):
                    self.t_issues.setItem(row, col, QTableWidgetItem("—"))

            # Status
            st = i['status']
            if st == "open":
                st_str = f"Open ({i['days_open']}d)"
                badge = "BadgeGold"
            else:
                st_str = "Returned"
                badge = "BadgeSuccess"
            st_lbl = QLabel(st_str)
            st_lbl.setObjectName(badge)
            st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.t_issues.setCellWidget(row, 12, st_lbl)

            # Loss Pct
            if i.get('loss_pct') is not None:
                l_pct = QTableWidgetItem(f"{i['loss_pct']:.2f}%")
                if i['loss_pct'] <= 2: l_pct.setForeground(QColor("#2ED573"))
                elif i['loss_pct'] <= 5: l_pct.setForeground(QColor("#F5A623"))
                else: l_pct.setForeground(QColor("#FF4757"))
                self.t_issues.setItem(row, 13, l_pct)
            else:
                self.t_issues.setItem(row, 13, QTableWidgetItem("—"))

            # Actions
            if st == "open":
                btn = QPushButton("Record Return")
                btn.setObjectName("BtnPrimary")
                btn.clicked.connect(lambda _, x=i: self._on_record_return(x))
                self.t_issues.setCellWidget(row, 14, btn)
            else:
                lbl = QLabel("✓")
                lbl.setObjectName("BadgeSuccess")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.t_issues.setCellWidget(row, 14, lbl)
        self.t_issues.setSortingEnabled(True)

    def _load_teams(self):
        teams = get_all_teams()
        self.t_teams.setRowCount(len(teams))
        for row, t in enumerate(teams):
            self.t_teams.setItem(row, 0, QTableWidgetItem(str(t['id'])))
            self.t_teams.setItem(row, 1, QTableWidgetItem(t['team_name']))
            self.t_teams.setItem(row, 2, QTableWidgetItem(t['lead_name']))
            self.t_teams.setItem(row, 3, QTableWidgetItem(str(t['member_count'])))

    def _on_new_issue(self):
        dlg = _NewGoldsmithIssueDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_record_return(self, issue_data):
        dlg = _RecordReturnDialog(issue_data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_new_team(self):
        Toast.show_toast(self, "Team creation not fully detailed in prompt, but UI placeholder is here.", "info")

    def refresh(self):
        self._load()


class _NewGoldsmithIssueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue Gold")
        self.setFixedSize(400, 520)

        ly = QVBoxLayout(self)
        card = _GoldCard("New Issue")

        # Date
        card.inner.addWidget(_field_label("Date *"))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(QDate.currentDate())
        card.inner.addWidget(self.dt)

        # Team / Individual selection
        self.selector = WorkerTeamSelector(process_type="GOLDSMITH")
        card.inner.addWidget(self.selector)

        # Inputs
        card.inner.addWidget(_field_label("Dye Issued (g) *"))
        self.dye = QDoubleSpinBox()
        self.dye.setRange(0, 99999.999); self.dye.setDecimals(3)
        card.inner.addWidget(self.dye)

        card.inner.addWidget(_field_label("Wire Issued (g) *"))
        self.wire = QDoubleSpinBox()
        self.wire.setRange(0, 99999.999); self.wire.setDecimals(3)
        card.inner.addWidget(self.wire)

        card.inner.addWidget(_field_label("Strips Issued (g) *"))
        self.strips = QDoubleSpinBox()
        self.strips.setRange(0, 99999.999); self.strips.setDecimals(3)
        card.inner.addWidget(self.strips)

        ly.addWidget(card)

        # footer
        ft = QHBoxLayout()
        ft.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnSecondary")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Issue Gold")
        btn_save.setObjectName("BtnPrimary")
        btn_save.clicked.connect(self._save)

        ft.addWidget(btn_cancel)
        ft.addWidget(btn_save)
        ly.addLayout(ft)

    def _save(self):
        if self.dye.value() == 0 and self.wire.value() == 0 and self.strips.value() == 0:
            QMessageBox.warning(self, "Error", "Must issue at least one item type")
            return

        sel = self.selector.as_dict()
        data = {
            "issue_date": self.dt.date().toPyDate(),
            "issue_type": sel["assigned_to_type"],
            "team_id": sel["team_id"],
            "worker_id": sel["worker_id"],
            "dye_issued_g": self.dye.value(),
            "wire_issued_g": self.wire.value(),
            "strips_issued_g": self.strips.value(),
        }

        res = create_issue(data)
        if res.get("success"):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", res.get("error", "Unknown error"))


class _RecordReturnDialog(QDialog):
    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.setWindowTitle("Record Return")
        self.setFixedSize(360, 460)

        ly = QVBoxLayout(self)
        card = _GoldCard(f"Return for Issue #{issue_data['id']}")

        card.inner.addWidget(_field_label(f"Total Issued: {issue_data['total_issued_g']:.3f} g"))
        card.inner.addWidget(_field_label("Return Date *"))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(QDate.currentDate())
        card.inner.addWidget(self.dt)

        card.inner.addWidget(_field_label("Chain Length — click to tally *"))
        self.tally = ChainTallyWidget()
        card.inner.addWidget(self.tally)

        card.inner.addWidget(_field_label("Total Weight (g) *"))
        self.wt = QDoubleSpinBox()
        self.wt.setRange(0, 99999.999)
        self.wt.setDecimals(3)
        card.inner.addWidget(self.wt)

        ly.addWidget(card)

        # footer
        ft = QHBoxLayout()
        ft.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnSecondary")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Record Return")
        btn_save.setObjectName("BtnPrimary")
        btn_save.clicked.connect(self._save)

        ft.addWidget(btn_cancel)
        ft.addWidget(btn_save)
        ly.addLayout(ft)

    def _save(self):
        pcs = self.tally.total_pcs()
        if pcs == 0:
            QMessageBox.warning(self, "Error", "Tally at least one piece (Baby / Normal / 30 Inch).")
            return

        counts = self.tally.counts
        data = {
            "issue_id": self.issue_data['id'],
            "return_date": self.dt.date().toPyDate(),
            "pcs": pcs,
            "total_inches": self.tally.total_inches(),
            "qty_baby": counts["baby"],
            "qty_normal": counts["normal"],
            "qty_30inch": counts["30inch"],
            "weight_g": self.wt.value(),
            "notes": f"Baby: {counts['baby']}, Normal: {counts['normal']}, 30 Inch: {counts['30inch']}"
        }
        res = record_return(data)
        if res.get("success"):
            if res.get("loss_alert"):
                QMessageBox.warning(self, "Loss Alert", f"Goldsmith Loss exceeded 2% ({res['loss_pct']:.2f}%)!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", res.get("error", "Unknown error"))


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl
