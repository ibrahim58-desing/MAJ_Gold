"""Wire & Sheet — single-page UI.  One output per batch (dye / wire / strip)."""
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QDoubleSpinBox, QTextEdit, QDialog, QFrame,
    QMessageBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from services.wire_sheet_service import (
    create_batch, complete_batch, get_all_batches,
    get_batch_by_id, get_total_rod_received,
)


# ─── Tiny reusable widgets (inline so no external dependency) ────────────────

class _StatCard(QFrame):
    def __init__(self, title, value="0"):
        super().__init__()
        self.setStyleSheet(
            "QFrame{background:#1A1A1A;border:1px solid #333;border-radius:8px;}"
        )
        ly = QVBoxLayout(self)
        t = QLabel(title)
        t.setStyleSheet("color:#B0B0B0;font-size:12px;border:none;")
        self._v = QLabel(str(value))
        self._v.setStyleSheet(
            "color:#F5F5F5;font-size:18px;font-weight:bold;border:none;"
        )
        ly.addWidget(t)
        ly.addWidget(self._v)

    def set_value(self, v, color="#F5F5F5"):
        self._v.setText(str(v))
        self._v.setStyleSheet(
            f"color:{color};font-size:18px;font-weight:bold;border:none;"
        )


class _GoldCard(QFrame):
    def __init__(self, title=None):
        super().__init__()
        self.setStyleSheet(
            "QFrame{background:#1A1A1A;border:1px solid rgba(212,175,55,0.2);"
            "border-radius:8px;}"
        )
        self.inner = QVBoxLayout(self)
        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(
                "color:#D4AF37;font-weight:bold;border:none;font-size:14px;"
            )
            self.inner.addWidget(lbl)


TYPE_COLOURS = {"dye": "#7B8FD4", "wire": "#D4AF37", "strip": "#C0C0C0"}


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════

class WireSheetUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._load()

    # ── build ─────────────────────────────────────────────────────────────────
    def _build(self):
        self.setStyleSheet("QWidget{background:#0D0D0D;color:#F5F5F5;}")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # header row
        hdr = QHBoxLayout()
        title = QLabel("Wire & Sheet")
        title.setStyleSheet("color:#D4AF37;font-size:22px;font-weight:bold;")
        sub = QLabel("Rod → Dye / Wire / Strip")
        sub.setStyleSheet("color:#B0B0B0;font-size:13px;")
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(title)
        left.addWidget(sub)
        hdr.addLayout(left)
        hdr.addStretch()
        btn_new = QPushButton("＋  New Batch")
        btn_new.setStyleSheet(
            "background:#D4AF37;color:#0D0D0D;font-weight:bold;"
            "border-radius:4px;padding:10px 20px;font-size:13px;"
        )
        btn_new.clicked.connect(self._on_new)
        hdr.addWidget(btn_new)
        root.addLayout(hdr)

        # summary cards
        cards = QHBoxLayout()
        self.c_rod   = _StatCard("Total Rod Received (g)")
        self.c_batch = _StatCard("Total Batches")
        self.c_pend  = _StatCard("Pending")
        self.c_loss  = _StatCard("Total Loss (g)")
        for c in (self.c_rod, self.c_batch, self.c_pend, self.c_loss):
            cards.addWidget(c)
        root.addLayout(cards)

        # table
        tcard = _GoldCard()
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Type", "Credit (g)", "Debit (g)",
            "Loss (g)", "Status", "Actions",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setStyleSheet(
            "QTableWidget{background:#1A1A1A;border:none;}"
            "QHeaderView::section{background:#111;color:#D4AF37;"
            "font-weight:bold;border:none;padding:6px;}"
            "QTableWidget::item{padding:4px;}"
        )
        tcard.inner.addWidget(self.table)
        root.addWidget(tcard, 1)

    # ── load data ─────────────────────────────────────────────────────────────
    def _load(self):
        batches = get_all_batches()
        total_rod = get_total_rod_received()

        pending = sum(1 for b in batches if b["status"] == "pending")
        total_loss = sum(b["loss_g"] for b in batches)

        self.c_rod.set_value(f"{total_rod:.3f}", "#D4AF37")
        self.c_batch.set_value(str(len(batches)))
        self.c_pend.set_value(str(pending), "#FF9800" if pending else "#4CAF50")
        self.c_loss.set_value(f"{total_loss:.3f}")

        self.table.setRowCount(len(batches))
        for row, b in enumerate(batches):
            self.table.setRowHeight(row, 42)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(f"#{b['id']}"))

            # Date
            self.table.setItem(
                row, 1,
                QTableWidgetItem(b["batch_date"].strftime("%d-%m-%Y")),
            )

            # Type — colour-coded badge
            typ = b["batch_type"].capitalize()
            type_item = QTableWidgetItem(typ)
            type_item.setForeground(
                QColor(TYPE_COLOURS.get(b["batch_type"], "#FFF"))
            )
            type_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 2, type_item)

            # Credit
            cr = QTableWidgetItem(f"{b['rod_weight_g']:.3f}")
            cr.setForeground(QColor("#4CAF50"))
            self.table.setItem(row, 3, cr)

            # Debit
            if b["status"] == "pending":
                dr = QTableWidgetItem("Pending")
                dr.setForeground(QColor("#FF9800"))
                dr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            else:
                dr = QTableWidgetItem(f"{b['output_weight_g']:.3f}")
                dr.setForeground(QColor("#F44336"))
            self.table.setItem(row, 4, dr)

            # Loss
            if b["status"] == "pending":
                lo = QTableWidgetItem("Pending")
                lo.setForeground(QColor("#FF9800"))
            else:
                lo = QTableWidgetItem(f"{b['loss_g']:.3f}")
                if b["loss_pct"] <= 2:
                    lo.setForeground(QColor("#4CAF50"))
                elif b["loss_pct"] <= 5:
                    lo.setForeground(QColor("#FF9800"))
                else:
                    lo.setForeground(QColor("#F44336"))
            self.table.setItem(row, 5, lo)

            # Status badge
            st_lbl = QLabel("Pending" if b["status"] == "pending" else "Completed")
            if b["status"] == "pending":
                st_lbl.setStyleSheet(
                    "background:rgba(255,152,0,0.12);color:#FF9800;"
                    "border-radius:10px;border:1px solid #FF9800;padding:2px 8px;"
                )
            else:
                st_lbl.setStyleSheet(
                    "background:rgba(76,175,80,0.12);color:#4CAF50;"
                    "border-radius:10px;border:1px solid #4CAF50;padding:2px 8px;"
                )
            st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 6, st_lbl)

            # Actions
            act = QWidget()
            aly = QHBoxLayout(act)
            aly.setContentsMargins(4, 4, 4, 4)
            aly.setSpacing(6)

            if b["status"] == "pending":
                btn = QPushButton("Complete")
                btn.setStyleSheet(
                    "background:#D4AF37;color:#0D0D0D;padding:4px 10px;"
                    "border-radius:3px;font-weight:bold;"
                )
                btn.clicked.connect(
                    lambda _, bid=b["id"]: self._on_complete(bid)
                )
                aly.addWidget(btn)
            else:
                info = QLabel(f"Loss {b['loss_pct']:.1f}%")
                col = "#4CAF50" if b["loss_pct"] <= 2 else (
                    "#FF9800" if b["loss_pct"] <= 5 else "#F44336"
                )
                info.setStyleSheet(f"color:{col};font-weight:bold;border:none;")
                aly.addWidget(info)

            self.table.setCellWidget(row, 7, act)

    # ── actions ───────────────────────────────────────────────────────────────
    def _on_new(self):
        dlg = _NewBatchDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_complete(self, batch_id):
        dlg = _CompleteBatchDialog(batch_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()


# ═══════════════════════════════════════════════════════════════════════════════
#  NEW BATCH DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class _NewBatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Wire & Sheet Batch")
        self.setFixedSize(480, 380)
        self.setStyleSheet(
            "QDialog{background:#0D0D0D;color:#F5F5F5;}"
            "QLabel{color:#F5F5F5;}"
        )

        ly = QVBoxLayout(self)

        card = _GoldCard("Batch Details")

        # date
        card.inner.addWidget(QLabel("Date"))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(QDate.currentDate())
        card.inner.addWidget(self.dt)

        # type
        card.inner.addWidget(QLabel("Output Type"))
        self.type_cb = QComboBox()
        self.type_cb.addItems(["dye", "wire", "strip"])
        self.type_cb.setStyleSheet(
            "QComboBox{background:#111;border:1px solid #333;padding:6px;"
            "color:#F5F5F5;border-radius:4px;}"
        )
        card.inner.addWidget(self.type_cb)

        # rod weight
        card.inner.addWidget(QLabel("Rod Weight (g)  —  Credit"))
        self.rod = QDoubleSpinBox()
        self.rod.setRange(0.001, 99999.999)
        self.rod.setDecimals(3)
        self.rod.setSuffix("  g")
        self.rod.setStyleSheet(
            "QDoubleSpinBox{background:#111;border:1px solid #333;"
            "padding:6px;color:#F5F5F5;border-radius:4px;}"
        )
        card.inner.addWidget(self.rod)

        # notes
        card.inner.addWidget(QLabel("Notes (optional)"))
        self.notes = QTextEdit()
        self.notes.setFixedHeight(44)
        self.notes.setStyleSheet(
            "QTextEdit{background:#111;border:1px solid #333;"
            "color:#F5F5F5;border-radius:4px;}"
        )
        card.inner.addWidget(self.notes)

        ly.addWidget(card)

        # footer
        ft = QHBoxLayout()
        ft.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "background:#333;color:#FFF;padding:8px 16px;border-radius:4px;"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Batch")
        btn_save.setStyleSheet(
            "background:#D4AF37;color:#0D0D0D;font-weight:bold;"
            "padding:8px 16px;border-radius:4px;"
        )
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
            "batch_type":   self.type_cb.currentText(),
            "rod_weight_g": self.rod.value(),
            "notes":        self.notes.toPlainText(),
        })
        if res.get("success"):
            self.accept()
        else:
            QMessageBox.critical(
                self, "Error", f"Failed to save:\n{res.get('error')}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPLETE BATCH DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class _CompleteBatchDialog(QDialog):
    def __init__(self, batch_id, parent=None):
        super().__init__(parent)
        self.batch_id = batch_id
        self.bd = get_batch_by_id(batch_id)
        self.setWindowTitle(f"Complete Batch #{batch_id}")
        self.setFixedSize(500, 420)
        self.setStyleSheet(
            "QDialog{background:#0D0D0D;color:#F5F5F5;}"
            "QLabel{color:#F5F5F5;}"
        )

        ly = QVBoxLayout(self)

        # summary
        info = _GoldCard("Batch Info")
        rod_val = self.bd["rod_weight_g"]
        typ = self.bd["batch_type"].capitalize()
        col = TYPE_COLOURS.get(self.bd["batch_type"], "#FFF")
        info.inner.addWidget(QLabel(f"Batch #{batch_id}"))
        info.inner.addWidget(QLabel(
            f"Date: {self.bd['batch_date'].strftime('%d-%m-%Y')}"
        ))
        type_lbl = QLabel(f"Type: {typ}")
        type_lbl.setStyleSheet(f"color:{col};font-weight:bold;border:none;")
        info.inner.addWidget(type_lbl)
        rod_lbl = QLabel(f"Rod Weight (Credit): {rod_val:.3f} g")
        rod_lbl.setStyleSheet("color:#D4AF37;font-weight:bold;border:none;")
        info.inner.addWidget(rod_lbl)
        ly.addWidget(info)

        # output weight
        form = _GoldCard("Record Output")
        form.inner.addWidget(QLabel(f"Output Weight (g)  —  Debit"))
        self.out_wt = QDoubleSpinBox()
        self.out_wt.setRange(0.0, 99999.999)
        self.out_wt.setDecimals(3)
        self.out_wt.setSuffix("  g")
        self.out_wt.setStyleSheet(
            "QDoubleSpinBox{background:#111;border:1px solid #333;"
            "padding:6px;color:#F5F5F5;border-radius:4px;}"
        )
        self.out_wt.valueChanged.connect(self._calc)
        form.inner.addWidget(self.out_wt)

        self.lbl_loss   = QLabel("Loss: 0.000 g")
        self.lbl_pct    = QLabel("Loss %: 0.00%")
        for l in (self.lbl_loss, self.lbl_pct):
            l.setStyleSheet("border:none;font-size:13px;")
            form.inner.addWidget(l)
        ly.addWidget(form)

        # footer
        ft = QHBoxLayout()
        ft.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "background:#333;color:#FFF;padding:8px 16px;border-radius:4px;"
        )
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Mark Completed")
        self.btn_save.setStyleSheet(
            "background:#D4AF37;color:#0D0D0D;font-weight:bold;"
            "padding:8px 16px;border-radius:4px;"
        )
        self.btn_save.clicked.connect(self._save)
        ft.addWidget(btn_cancel)
        ft.addWidget(self.btn_save)
        ly.addLayout(ft)

        self._calc()

    def _calc(self):
        rod = self.bd["rod_weight_g"]
        out = self.out_wt.value()
        loss = rod - out
        pct = (loss / rod * 100) if rod > 0 else 0

        self.lbl_loss.setText(f"Loss: {loss:.3f} g")

        if out == 0:
            self.lbl_pct.setText("Loss %: —")
            self.lbl_pct.setStyleSheet("color:#666;border:none;font-size:13px;")
        elif out > rod:
            self.lbl_pct.setText("⚠ Output exceeds rod weight!")
            self.lbl_pct.setStyleSheet(
                "color:#F44336;font-weight:bold;border:none;font-size:13px;"
            )
            self.btn_save.setEnabled(False)
            return
        elif pct <= 2:
            self.lbl_pct.setText(f"Loss %: {pct:.2f}%  ✓ Within limit")
            self.lbl_pct.setStyleSheet(
                "color:#4CAF50;border:none;font-size:13px;"
            )
        elif pct <= 5:
            self.lbl_pct.setText(f"Loss %: {pct:.2f}%  ⚠ Check")
            self.lbl_pct.setStyleSheet(
                "color:#FF9800;border:none;font-size:13px;"
            )
        else:
            self.lbl_pct.setText(f"Loss %: {pct:.2f}%  ⚠ High loss!")
            self.lbl_pct.setStyleSheet(
                "color:#F44336;font-weight:bold;border:none;font-size:13px;"
            )
        self.btn_save.setEnabled(True)

    def _save(self):
        out = self.out_wt.value()
        if out > self.bd["rod_weight_g"]:
            return
        if out <= 0:
            QMessageBox.warning(self, "Error", "Output weight must be > 0")
            return

        res = complete_batch(self.batch_id, out)
        if res.get("success"):
            pct = res.get("loss_pct", 0)
            if pct > 2:
                QMessageBox.warning(
                    self, "Loss Alert",
                    f"Loss is {pct:.2f}% — please verify the weights.",
                )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Error", f"Failed:\n{res.get('error')}"
            )
