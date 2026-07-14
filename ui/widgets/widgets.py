"""Reusable widgets: Toast, LoadingOverlay, ConfirmDialog, StatCard, DataTable, SearchBar."""
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QAbstractItemView, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QSize
)
from PyQt6.QtGui import QFont, QColor, QPalette
from datetime import date


# ─── Toast Notification ───────────────────────────────────────────────────────
class Toast(QWidget):
    """Floating toast notification that auto-dismisses."""

    def __init__(self, parent, message: str, kind: str = "info", duration: int = 3000):
        super().__init__(parent)
        self.setObjectName("Toast")
        kinds = {"success": ("✅", "ToastSuccess"), "error": ("❌", "ToastError"),
                 "info": ("ℹ️", "ToastInfo"), "warning": ("⚠️", "ToastWarning")}
        icon, obj = kinds.get(kind, ("ℹ️", "ToastInfo"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(20, 20)
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color:#F0F4FF; font-size:13px;")

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl, 1)

        self.setObjectName(obj)
        self.setFixedWidth(340)
        self.adjustSize()

        # Position bottom-right of parent
        self._reposition()

        # Fade-in/out
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        self.show()
        self.raise_()

        QTimer.singleShot(duration, self._fade_out)

    def _reposition(self):
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.move(pw - self.width() - 20, ph - self.height() - 20)

    def _fade_out(self):
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

    @staticmethod
    def show_toast(parent, message, kind="info", duration=3000):
        Toast(parent, message, kind, duration)


# ─── Loading Overlay ──────────────────────────────────────────────────────────
class LoadingOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: rgba(10,12,20,0.75);")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("⟳  Loading…")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#F5A623; font-size:18px; font-weight:700; background:transparent;")
        layout.addWidget(lbl)
        self._lbl = lbl

        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._spin)
        self._timer.start(120)
        self.hide()

    def _spin(self):
        spinners = ["⟳", "⟲"]
        self._angle = (self._angle + 1) % 2
        self._lbl.setText(f"{spinners[self._angle]}  Loading…")

    def show_over(self, widget):
        self.setGeometry(widget.rect())
        self.show()
        self.raise_()

    def hide_overlay(self):
        self.hide()


# ─── Confirm Dialog ───────────────────────────────────────────────────────────
class ConfirmDialog(QDialog):
    def __init__(self, parent, title="Confirm", message="Are you sure?"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(360, 160)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("DialogTitle")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color:#8A9BB5; font-size:13px;")
        layout.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("BtnSecondary")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("Confirm")
        confirm.setObjectName("BtnDanger")
        confirm.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        layout.addLayout(btn_row)

    @staticmethod
    def ask(parent, title="Confirm", message="Are you sure?") -> bool:
        dlg = ConfirmDialog(parent, title, message)
        return dlg.exec() == QDialog.DialogCode.Accepted


# ─── Stat Card ────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, label: str, value: str, icon: str = "◆",
                 color: str = "#F5A623", accent: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("CardGold" if accent else "Card")
        self.setFixedHeight(100)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("StatIcon")
        icon_lbl.setFixedWidth(44)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._val_lbl = QLabel(value)
        self._val_lbl.setObjectName("StatValue")
        self._val_lbl.setStyleSheet(f"color:{color}; font-size:24px; font-weight:800;")
        lab_lbl = QLabel(label.upper())
        lab_lbl.setObjectName("StatLabel")
        text_col.addWidget(self._val_lbl)
        text_col.addWidget(lab_lbl)

        layout.addWidget(icon_lbl)
        layout.addLayout(text_col)
        layout.addStretch()

    def set_value(self, value: str, color: str = None):
        self._val_lbl.setText(value)
        if color:
            self._val_lbl.setStyleSheet(f"color:{color}; font-size:24px; font-weight:800;")


# ─── Search Bar ───────────────────────────────────────────────────────────────
class SearchBar(QLineEdit):
    def __init__(self, placeholder="Search…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(f"🔍  {placeholder}")
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QLineEdit {
                background: #0E1525; color: #F0F4FF;
                border: 1px solid #2A3347; border-radius: 8px;
                padding: 6px 14px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #F5A623; }
        """)


# ─── Data Table ───────────────────────────────────────────────────────────────
class DataTable(QTableWidget):
    """Styled sortable table with alternating row colors."""

    def __init__(self, columns: list, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget { alternate-background-color: #0A0F1E; }
        """)
        self.setSortingEnabled(True)

    def populate(self, rows: list):
        """rows: list of lists/tuples matching column count."""
        self.setSortingEnabled(False)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.setItem(r, c, item)
        self.setSortingEnabled(True)
        self.resizeColumnsToContents()

    def get_selected_row_data(self) -> list:
        row = self.currentRow()
        if row < 0:
            return []
        return [self.item(row, c).text() if self.item(row, c) else "" for c in range(self.columnCount())]
