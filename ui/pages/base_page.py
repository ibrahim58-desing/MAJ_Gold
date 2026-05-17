"""Base page class with shared CRUD patterns."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDateEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QTextEdit, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt, QDate
from ui.widgets.widgets import DataTable, SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from utils.formatters import fmt_date


class BasePage(QWidget):
    """Base class providing standard CRUD table layout."""

    PAGE_TITLE  = "Page"
    PAGE_ICON   = "📋"
    COLUMNS     = []
    ADD_LABEL   = "Add New"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        self._all_rows = []
        self._setup_base_ui()
        self._setup_page()
        self._load()

    def _setup_base_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel(f"{self.PAGE_ICON}  {self.PAGE_TITLE}")
        title.setObjectName("SectionTitle")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title)
        hdr.addStretch()

        self._search = SearchBar(f"Search {self.PAGE_TITLE}…")
        self._search.setFixedWidth(260)
        self._search.textChanged.connect(self._filter)
        hdr.addWidget(self._search)

        self._add_btn = QPushButton(f"＋  {self.ADD_LABEL}")
        self._add_btn.setObjectName("BtnPrimary")
        self._add_btn.clicked.connect(self._on_add)
        hdr.addWidget(self._add_btn)
        root.addLayout(hdr)

        # Table
        self._table = DataTable(self.COLUMNS)
        root.addWidget(self._table, 1)

        # Action bar
        act = QHBoxLayout()
        self._count_lbl = QLabel("0 records")
        self._count_lbl.setStyleSheet("color:#4A5568; font-size:12px;")
        act.addWidget(self._count_lbl)
        act.addStretch()

        self._edit_btn = QPushButton("✏  Edit")
        self._edit_btn.setObjectName("BtnSecondary")
        self._edit_btn.clicked.connect(self._on_edit)
        self._del_btn = QPushButton("🗑  Delete")
        self._del_btn.setObjectName("BtnDanger")
        self._del_btn.clicked.connect(self._on_delete)
        act.addWidget(self._edit_btn)
        act.addWidget(self._del_btn)
        root.addLayout(act)

        self._overlay = LoadingOverlay(self)
        self.setLayout(root)

    def _setup_page(self):
        """Override to add extra UI elements above/below table."""
        pass

    def _load(self):
        self._overlay.show_over(self)
        w = DBWorker(self._fetch_data)
        w.result.connect(self._on_loaded)
        w.error.connect(self._on_error)
        w.start()
        self._workers.append(w)

    def _fetch_data(self):
        """Override: return list of rows for populate()."""
        return []

    def _on_loaded(self, rows):
        self._overlay.hide_overlay()
        self._all_rows = rows
        self._table.populate(rows)
        self._count_lbl.setText(f"{len(rows)} records")

    def _filter(self, text: str):
        if not text.strip():
            self._table.populate(self._all_rows)
            return
        t = text.lower()
        filtered = [r for r in self._all_rows if any(t in str(v).lower() for v in r)]
        self._table.populate(filtered)

    def _on_add(self):
        """Override to show add dialog."""
        pass

    def _on_edit(self):
        """Override to show edit dialog."""
        pass

    def _on_delete(self):
        """Override to handle delete."""
        pass

    def _on_error(self, msg: str):
        self._overlay.hide_overlay()
        Toast.show_toast(self, f"Error: {msg}", "error")

    def _get_selected_id(self):
        """Return the ID from column 0 of the selected row."""
        row = self._table.currentRow()
        if row < 0:
            Toast.show_toast(self, "Please select a row first.", "warning")
            return None
        item = self._table.item(row, 0)
        return int(item.text()) if item else None
