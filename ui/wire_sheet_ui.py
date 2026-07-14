"""Wire & Sheet — single-page UI. Inline output editing."""
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QDoubleSpinBox, QTextEdit, QDialog, QFrame,
    QMessageBox, QScrollArea, QLineEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from services.wire_sheet_service import (
    create_batch, record_outputs, get_all_batches,
    get_batch_by_id, get_total_rod_received, clear_test_data
)
from database.models.base import SessionLocal, Setting
from workers.db_worker import DBWorker
from utils.formatters import fmt_weight
from ui.widgets.process_widgets import WorkerTeamSelector
from ui.widgets.widgets import StatCard, DataTable


# ─── Tiny reusable widgets ───────────────────────────────────────────────────

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


_INLINE_EDIT_QSS = """
    QLineEdit {
        background: rgba(245,166,35,0.08);
        color: #F0F4FF;
        border: 1px solid rgba(245,166,35,0.35);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 12px;
    }
    QLineEdit:focus { border-color: #F5A623; }
"""


class WireSheetUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_sample_data()
        self._build()
        self._load()

    def _check_sample_data(self):
        session = SessionLocal()
        try:
            setting = session.query(Setting).filter(
                Setting.key == "ws_sample_cleared"
            ).first()
            if not setting:
                clear_test_data()
                session.add(Setting(
                    key="ws_sample_cleared",
                    value="true"
                ))
                session.commit()
        except Exception as e:
            session.rollback()
            print("Error clearing test data:", e)
        finally:
            session.close()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # header row
        hdr = QHBoxLayout()
        title = QLabel("🔗  WIRE & SHEET")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        sub = QLabel("Rod → Dye / Wire / Strip")
        sub.setStyleSheet("color:#8A9BB5; font-size:12px;")
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        left.addWidget(title)
        left.addWidget(sub)
        hdr.addLayout(left)
        hdr.addStretch()
        btn_new = QPushButton("＋  New Batch")
        btn_new.setObjectName("BtnPrimary")
        btn_new.clicked.connect(self._on_new)
        hdr.addWidget(btn_new)
        root.addLayout(hdr)

        # summary cards
        cards = QHBoxLayout()
        self.c_rod   = StatCard("Total Rod Received (g)", "0.000", icon="🪙", color="#F5A623")
        self.c_batch = StatCard("Total Batches", "0", icon="📦")
        self.c_pend  = StatCard("Pending", "0", icon="⏳", color="#2ED573")
        self.c_loss  = StatCard("Total Loss (g)", "0.000", icon="⚠", color="#FF4757")
        for c in (self.c_rod, self.c_batch, self.c_pend, self.c_loss):
            cards.addWidget(c)
        root.addLayout(cards)

        # table
        self.table = DataTable([
            "ID", "Date", "Worker", "Rod (g)", "Dye (g)", "Wire (g)",
            "Strips (g)", "Loss (g)", "Loss%", "Status", "Actions"
        ])
        root.addWidget(self.table, 1)

    def _load(self):
        batches = get_all_batches()
        total_rod = get_total_rod_received()

        pending = sum(1 for b in batches if b["status"] == "pending")
        total_loss = sum(b["loss_g"] for b in batches)

        self.c_rod.set_value(f"{total_rod:.3f}")
        self.c_batch.set_value(str(len(batches)))
        self.c_pend.set_value(str(pending), "#F5A623" if pending else "#2ED573")
        self.c_loss.set_value(f"{total_loss:.3f}")

        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(batches))
        for row, b in enumerate(batches):
            self.table.setRowHeight(row, 48)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(f"#{b['id']}"))

            # Date
            self.table.setItem(row, 1, QTableWidgetItem(b["batch_date"].strftime("%d-%m-%Y")))

            # Worker
            self.table.setItem(row, 2, QTableWidgetItem(b.get("worker_name", "—")))

            # Rod
            cr = QTableWidgetItem(f"{b['rod_weight_g']:.3f}")
            cr.setForeground(QColor("#2ED573"))
            self.table.setItem(row, 3, cr)

            # Cells for live calculation
            loss_cell = QTableWidgetItem()
            loss_pct_cell = QTableWidgetItem()

            if b["status"] == "pending":
                # Create 3 inputs
                inputs = []
                for col in (4, 5, 6): # Dye, Wire, Strips
                    inp = QLineEdit()
                    inp.setPlaceholderText("0.000")
                    inp.setStyleSheet(_INLINE_EDIT_QSS)
                    inputs.append(inp)
                    self.table.setCellWidget(row, col, inp)

                inputs[0].textChanged.connect(lambda _, r=b['rod_weight_g'], rw=row, i_list=inputs: self._update_live_loss(r, i_list, rw))
                inputs[1].textChanged.connect(lambda _, r=b['rod_weight_g'], rw=row, i_list=inputs: self._update_live_loss(r, i_list, rw))
                inputs[2].textChanged.connect(lambda _, r=b['rod_weight_g'], rw=row, i_list=inputs: self._update_live_loss(r, i_list, rw))

                loss_cell.setText("Pending")
                loss_cell.setForeground(QColor("#F5A623"))
                loss_pct_cell.setText("—")

            else:
                self.table.setItem(row, 4, QTableWidgetItem(fmt_weight(b.get("dye_weight_g", 0))))
                self.table.setItem(row, 5, QTableWidgetItem(fmt_weight(b.get("wire_weight_g", 0))))
                self.table.setItem(row, 6, QTableWidgetItem(fmt_weight(b.get("strips_weight_g", 0))))

                loss_cell.setText(f"{b['loss_g']:.3f}")
                loss_pct_cell.setText(f"{b['loss_pct']:.2f}%")

                if b["loss_pct"] <= 2:
                    loss_pct_cell.setForeground(QColor("#2ED573"))
                elif b["loss_pct"] <= 5:
                    loss_pct_cell.setForeground(QColor("#F5A623"))
                else:
                    loss_pct_cell.setForeground(QColor("#FF4757"))

            self.table.setItem(row, 7, loss_cell)
            self.table.setItem(row, 8, loss_pct_cell)

            # Status badge
            st_lbl = QLabel("Pending" if b["status"] == "pending" else "Completed")
            st_lbl.setObjectName("BadgeGold" if b["status"] == "pending" else "BadgeSuccess")
            st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 9, st_lbl)

            # Actions
            act = QWidget()
            aly = QHBoxLayout(act)
            aly.setContentsMargins(4, 4, 4, 4)
            aly.setSpacing(6)

            if b["status"] == "pending":
                btn = QPushButton("Save")
                btn.setObjectName("BtnPrimary")
                btn.clicked.connect(
                    lambda _, bid=b["id"], r=row: self._on_save_row(bid, r)
                )
                aly.addWidget(btn)
            else:
                info = QLabel("✓")
                info.setObjectName("BadgeSuccess")
                aly.addWidget(info)

            self.table.setCellWidget(row, 10, act)
        self.table.setSortingEnabled(True)

    def _update_live_loss(self, rod, inputs, row):
        try:
            dye = float(inputs[0].text() or 0)
            wire = float(inputs[1].text() or 0)
            strips = float(inputs[2].text() or 0)

            total = dye + wire + strips
            loss = rod - total
            loss_pct = (loss / rod * 100) if rod > 0 else 0.0

            loss_cell = self.table.item(row, 7)
            loss_pct_cell = self.table.item(row, 8)
            if not loss_cell or not loss_pct_cell:
                return

            loss_cell.setText(f"{loss:.3f}")
            loss_pct_cell.setText(f"{loss_pct:.2f}%")

            if loss_pct <= 2:
                loss_pct_cell.setForeground(QColor("#2ED573"))
            elif loss_pct <= 5:
                loss_pct_cell.setForeground(QColor("#F5A623"))
            else:
                loss_pct_cell.setForeground(QColor("#FF4757"))

        except ValueError:
            pass

    def _on_new(self):
        dlg = _NewBatchDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def refresh(self):
        self._load()

    def _on_save_row(self, batch_id, row):
        try:
            dye_inp = self.table.cellWidget(row, 4)
            wire_inp = self.table.cellWidget(row, 5)
            strips_inp = self.table.cellWidget(row, 6)

            dye = float(dye_inp.text() or 0)
            wire = float(wire_inp.text() or 0)
            strips = float(strips_inp.text() or 0)

            if dye == 0 and wire == 0 and strips == 0:
                QMessageBox.warning(self, "Error", "Enter at least one output value.")
                return

            res = record_outputs(batch_id, {
                "dye_weight_g": dye,
                "wire_weight_g": wire,
                "strips_weight_g": strips
            })

            if res.get("success"):
                pct = res.get("loss_pct", 0)
                if pct > 2:
                    QMessageBox.warning(
                        self, "Loss Alert",
                        f"Loss is {pct:.2f}% — please verify the weights.",
                    )
                self._load()
            else:
                QMessageBox.critical(
                    self, "Error", f"Failed:\n{res.get('error')}"
                )
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid numeric values entered.")


class _NewBatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Wire & Sheet Batch")
        self.setFixedSize(480, 500)

        ly = QVBoxLayout(self)
        card = _GoldCard("Batch Details")

        # date
        card.inner.addWidget(_field_label("Date *"))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(QDate.currentDate())
        card.inner.addWidget(self.dt)

        # worker / team
        self.selector = WorkerTeamSelector(process_type="WIRE_SHEET")
        card.inner.addWidget(self.selector)

        # rod weight
        card.inner.addWidget(_field_label("Rod Weight (g)  —  Credit *"))
        self.rod = QDoubleSpinBox()
        self.rod.setRange(0.001, 99999.999)
        self.rod.setDecimals(3)
        self.rod.setSuffix("  g")
        card.inner.addWidget(self.rod)

        # notes
        card.inner.addWidget(_field_label("Notes (optional)"))
        self.notes = QTextEdit()
        self.notes.setFixedHeight(44)
        card.inner.addWidget(self.notes)

        ly.addWidget(card)

        # footer
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
        if self.rod.value() <= 0:
            QMessageBox.warning(self, "Error", "Rod weight must be > 0")
            return
        d = self.dt.date()
        res = create_batch({
            "batch_date":   date(d.year(), d.month(), d.day()),
            "rod_weight_g": self.rod.value(),
            **self.selector.as_dict(),
            "notes":        self.notes.toPlainText(),
        })
        if res.get("success"):
            self.accept()
        else:
            QMessageBox.critical(
                self, "Error", f"Failed to save:\n{res.get('error')}"
            )
