"""Shared process widgets: chain-size tally and worker/team selector.

Extracted from the original Goldsmith `_TallyOption` tally UI and the
duplicated Goldsmith/Polish Team-vs-Individual combo logic, so every page
that captures chain-size counts or worker/team assignment shares one
implementation instead of copy-pasting it. Styled entirely via the shared
app theme (ui/styles/theme.py) using objectName selectors.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.models.base import SessionLocal
from database.models.masters import Team, Worker


class _TallyOption(QFrame):
    """Click-to-count card for one chain-length category."""

    def __init__(self, label: str, on_change):
        super().__init__()
        self.count = 0
        self._on_change = on_change
        self.setObjectName("Card")
        self.setMinimumWidth(90)

        ly = QVBoxLayout(self)
        ly.setContentsMargins(6, 6, 6, 6)
        ly.setSpacing(4)

        self.btn = QPushButton(label)
        self.btn.setObjectName("BtnTally")
        self.btn.clicked.connect(self._increment)
        ly.addWidget(self.btn)

        row = QHBoxLayout()
        row.setSpacing(4)
        self.count_lbl = QLabel("0")
        self.count_lbl.setObjectName("StatValue")
        self.count_lbl.setStyleSheet("font-size:16px;")
        self.count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        undo_btn = QPushButton("−1")
        undo_btn.setObjectName("BtnTallyMinus")
        undo_btn.clicked.connect(self._decrement)
        row.addWidget(self.count_lbl, 1)
        row.addWidget(undo_btn)
        ly.addLayout(row)

    def _increment(self):
        self.count += 1
        self.count_lbl.setText(str(self.count))
        self._on_change()

    def _decrement(self):
        if self.count > 0:
            self.count -= 1
            self.count_lbl.setText(str(self.count))
            self._on_change()

    def set_count(self, n: int):
        self.count = max(0, n)
        self.count_lbl.setText(str(self.count))


class ChainTallyWidget(QWidget):
    """Baby / Normal / 30-Inch click-to-tally widget with a running totals label."""

    changed = pyqtSignal()

    def __init__(self, initial: dict | None = None, parent=None):
        super().__init__(parent)
        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.opt_baby = _TallyOption("Baby", self._on_change)
        self.opt_normal = _TallyOption("Normal", self._on_change)
        self.opt_30 = _TallyOption("30 Inch", self._on_change)
        row.addWidget(self.opt_baby)
        row.addWidget(self.opt_normal)
        row.addWidget(self.opt_30)
        ly.addLayout(row)

        self.lbl_totals = QLabel("Total: 0 pcs · 0.0 inches")
        self.lbl_totals.setObjectName("FieldLabel")
        ly.addWidget(self.lbl_totals)

        if initial:
            self.set_counts(
                initial.get("baby", 0), initial.get("normal", 0), initial.get("30inch", 0)
            )
        else:
            self._update_totals()

    def _on_change(self):
        self._update_totals()
        self.changed.emit()

    def _update_totals(self):
        pcs = self.total_pcs()
        inches = self.total_inches()
        self.lbl_totals.setText(f"Total: {pcs} pcs · {inches:.1f} inches (30\" pieces only)")

    @property
    def counts(self) -> dict:
        return {
            "baby": self.opt_baby.count,
            "normal": self.opt_normal.count,
            "30inch": self.opt_30.count,
        }

    def total_pcs(self) -> int:
        return self.opt_baby.count + self.opt_normal.count + self.opt_30.count

    def total_inches(self) -> float:
        return self.opt_30.count * 30

    def set_counts(self, baby: int = 0, normal: int = 0, thirty: int = 0):
        self.opt_baby.set_count(baby)
        self.opt_normal.set_count(normal)
        self.opt_30.set_count(thirty)
        self._update_totals()

    def reset(self):
        self.set_counts(0, 0, 0)


class WorkerTeamSelector(QWidget):
    """TEAM / INDIVIDUAL toggle plus the dependent Team/Worker combo."""

    changed = pyqtSignal()

    def __init__(self, process_type: str, worker_process_types: list | None = None,
                 initial_type: str = "TEAM", parent=None):
        super().__init__(parent)
        self._process_type = process_type
        self._worker_process_types = worker_process_types or [process_type]

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(6)

        lbl_type = QLabel("Assigned To *")
        lbl_type.setObjectName("FieldLabel")
        ly.addWidget(lbl_type)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["TEAM", "INDIVIDUAL"])
        self.type_cb.setCurrentText(initial_type)
        ly.addWidget(self.type_cb)

        self.lbl_target = QLabel("Select Team *")
        self.lbl_target.setObjectName("FieldLabel")
        ly.addWidget(self.lbl_target)

        self.target_cb = QComboBox()
        ly.addWidget(self.target_cb)

        self.type_cb.currentTextChanged.connect(self._load_targets)
        self._load_targets()
        self.type_cb.currentTextChanged.connect(self.changed.emit)
        self.target_cb.currentIndexChanged.connect(self.changed.emit)

    def _load_targets(self):
        self.target_cb.clear()
        t = self.type_cb.currentText()
        session = SessionLocal()
        try:
            if t == "TEAM":
                self.lbl_target.setText("Select Team *")
                teams = (
                    session.query(Team)
                    .filter(Team.process_type == self._process_type, Team.is_active == True)
                    .order_by(Team.team_name, Team.name)
                    .all()
                )
                for tm in teams:
                    self.target_cb.addItem(tm.team_name or tm.name, tm.id)
            else:
                self.lbl_target.setText("Select Worker *")
                workers = (
                    session.query(Worker)
                    .filter(Worker.process_type.in_(self._worker_process_types), Worker.is_active == True)
                    .order_by(Worker.name)
                    .all()
                )
                for w in workers:
                    self.target_cb.addItem(w.name, w.id)
        finally:
            session.close()

    @property
    def selection_type(self) -> str:
        return self.type_cb.currentText()

    @property
    def selected_id(self):
        return self.target_cb.currentData()

    @property
    def selected_label(self) -> str:
        return self.target_cb.currentText()

    def as_dict(self) -> dict:
        t = self.selection_type
        return {
            "assigned_to_type": t,
            "team_id": self.selected_id if t == "TEAM" else None,
            "worker_id": self.selected_id if t == "INDIVIDUAL" else None,
        }
