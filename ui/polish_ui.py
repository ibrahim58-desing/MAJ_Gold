"""Polish UI — Isolated Polish Loss Tracking."""
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit, QDialog, QFrame,
    QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from services.polish_service import (
    get_goldsmith_totals, get_all_batches, get_polish_loss_summary,
    create_batch, record_output
)
from utils.formatters import fmt_weight
from ui.widgets.process_widgets import ChainTallyWidget, WorkerTeamSelector
from ui.widgets.widgets import StatCard, DataTable


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


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl


class PolishUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # header
        hdr = QHBoxLayout()
        title = QLabel("✨  POLISH MODULE")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_new = QPushButton("＋  New Batch")
        btn_new.setObjectName("BtnPrimary")
        btn_new.clicked.connect(self._on_new_batch)
        hdr.addWidget(btn_new)
        root.addLayout(hdr)

        # Summary: From Goldsmith + isolated Polish loss, one compact row
        cards = QHBoxLayout()
        self.c_gs_pcs = StatCard("Total Pcs (From Goldsmith)", "0", icon="🔢")
        self.c_gs_weight = StatCard("Total Weight (g)", "0.000", icon="⚖", color="#2ED573")
        self.c_pl_loss_g = StatCard("Total Polish Loss (g)", "0.000", icon="⚠", color="#FF4757", accent=True)
        cards.addWidget(self.c_gs_pcs)
        cards.addWidget(self.c_gs_weight)
        cards.addWidget(self.c_pl_loss_g)
        root.addLayout(cards)

        # Table
        self.table = DataTable([
            "ID", "Date", "Team/Worker", "In Pcs", "In Inches", "In Wt (g)",
            "Out Pcs", "Out Inches", "Out Wt (g)",
            "Loss (g)", "Loss Pcs", "Loss%", "Actions"
        ])
        root.addWidget(self.table, 1)

    def _load(self):
        gs_totals = get_goldsmith_totals()
        self.c_gs_pcs.set_value(str(gs_totals['total_pcs']))
        self.c_gs_weight.set_value(f"{gs_totals['total_weight_g']:.3f}")

        pl_totals = get_polish_loss_summary()
        self.c_pl_loss_g.set_value(f"{pl_totals['total_polish_loss_g']:.3f}")

        batches = get_all_batches()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(batches))
        for row, b in enumerate(batches):
            self.table.setRowHeight(row, 44)
            self.table.setItem(row, 0, QTableWidgetItem(f"#{b['id']}"))
            self.table.setItem(row, 1, QTableWidgetItem(b['batch_date'].strftime("%d-%m-%Y")))

            self.table.setItem(row, 2, QTableWidgetItem(b.get('worker_name', '—')))
            self.table.setItem(row, 3, QTableWidgetItem(str(b['input_pcs'])))
            self.table.setItem(row, 4, QTableWidgetItem(f"{b['input_inches']:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(fmt_weight(b['input_weight_g'])))

            if b['status'] == 'completed':
                self.table.setItem(row, 6, QTableWidgetItem(str(b['output_pcs'])))
                self.table.setItem(row, 7, QTableWidgetItem(f"{b['output_inches']:.2f}"))
                self.table.setItem(row, 8, QTableWidgetItem(fmt_weight(b['output_weight_g'])))

                loss_g = QTableWidgetItem(fmt_weight(b['polish_loss_g']))
                loss_g.setForeground(QColor("#FF4757"))
                self.table.setItem(row, 9, loss_g)

                self.table.setItem(row, 10, QTableWidgetItem(str(b['polish_loss_pcs'])))

                loss_pct = QTableWidgetItem(f"{b['polish_loss_pct']:.2f}%")
                if b['polish_loss_pct'] > 2:
                    loss_pct.setForeground(QColor("#FF4757"))
                else:
                    loss_pct.setForeground(QColor("#F5A623"))
                self.table.setItem(row, 11, loss_pct)

                lbl = QLabel("✓")
                lbl.setObjectName("BadgeSuccess")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(row, 12, lbl)
            else:
                for col in (6, 7, 8, 9, 10, 11):
                    self.table.setItem(row, col, QTableWidgetItem("—"))

                btn = QPushButton("Record Output")
                btn.setObjectName("BtnPrimary")
                btn.clicked.connect(lambda _, x=b: self._on_record_output(x))
                self.table.setCellWidget(row, 12, btn)
        self.table.setSortingEnabled(True)

    def _on_new_batch(self):
        dlg = _NewPolishBatchDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_record_output(self, batch_data):
        dlg = _RecordPolishOutputDialog(batch_data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def refresh(self):
        self._load()


class _NewPolishBatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Polish Batch")
        self.setFixedSize(400, 560)

        ly = QVBoxLayout(self)
        card = _GoldCard("New Batch")

        card.inner.addWidget(_field_label("Date *"))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(QDate.currentDate())
        card.inner.addWidget(self.dt)

        self.selector = WorkerTeamSelector(
            process_type="POLISH", worker_process_types=["POLISH", "GOLDSMITH"],
        )
        card.inner.addWidget(self.selector)

        card.inner.addWidget(_field_label("Chain Length — click to tally *"))
        self.tally = ChainTallyWidget()
        card.inner.addWidget(self.tally)

        card.inner.addWidget(_field_label("Input Weight (g) *"))
        self.wt = QDoubleSpinBox()
        self.wt.setRange(0, 99999.999)
        self.wt.setDecimals(3)
        card.inner.addWidget(self.wt)

        ly.addWidget(card)

        ft = QHBoxLayout()
        ft.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnSecondary")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Batch")
        btn_save.setObjectName("BtnPrimary")
        btn_save.clicked.connect(self._save)

        ft.addWidget(btn_cancel)
        ft.addWidget(btn_save)
        ly.addLayout(ft)

    def _save(self):
        if self.wt.value() <= 0:
            QMessageBox.warning(self, "Error", "Input weight must be > 0")
            return

        if self.tally.total_pcs() == 0:
            QMessageBox.warning(self, "Error", "Tally at least one piece (Baby / Normal / 30 Inch).")
            return

        counts = self.tally.counts
        data = {
            "batch_date": self.dt.date().toPyDate(),
            **self.selector.as_dict(),
            "goldsmith_return_id": None,
            "input_qty_baby": counts["baby"],
            "input_qty_normal": counts["normal"],
            "input_qty_30inch": counts["30inch"],
            "input_weight_g": self.wt.value(),
            "notes": f"Baby: {counts['baby']}, Normal: {counts['normal']}, 30 Inch: {counts['30inch']}"
        }

        res = create_batch(data)
        if res.get("success"):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", res.get("error", "Unknown error"))


class _RecordPolishOutputDialog(QDialog):
    def __init__(self, batch_data, parent=None):
        super().__init__(parent)
        self.batch_data = batch_data
        self.setWindowTitle("Record Polish Output")
        self.setFixedSize(360, 400)

        ly = QVBoxLayout(self)
        card = _GoldCard(f"Output for Batch #{batch_data['id']}")

        card.inner.addWidget(_field_label(f"Input Weight: {batch_data['input_weight_g']:.3f} g"))

        card.inner.addWidget(_field_label("Chain Length — click to tally *"))
        self.tally = ChainTallyWidget()
        card.inner.addWidget(self.tally)

        card.inner.addWidget(_field_label("Output Weight (g) *"))
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
        btn_save = QPushButton("Record Output")
        btn_save.setObjectName("BtnPrimary")
        btn_save.clicked.connect(self._save)

        ft.addWidget(btn_cancel)
        ft.addWidget(btn_save)
        ly.addLayout(ft)

    def _save(self):
        counts = self.tally.counts
        data = {
            "batch_id": self.batch_data['id'],
            "output_qty_baby": counts["baby"],
            "output_qty_normal": counts["normal"],
            "output_qty_30inch": counts["30inch"],
            "output_weight_g": self.wt.value(),
            "notes": f"Baby: {counts['baby']}, Normal: {counts['normal']}, 30 Inch: {counts['30inch']}"
        }
        res = record_output(data)
        if res.get("success"):
            if res.get("polish_loss_pct", 0) > 2.0:
                QMessageBox.warning(self, "Loss Alert", f"Isolated Polish Loss is {res['polish_loss_pct']:.2f}%!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", res.get("error", "Unknown error"))
