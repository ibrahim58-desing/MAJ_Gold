"""Melt Batches page — NG Melting and Scrap Melting."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from ui.widgets.widgets import SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.melt_batch_service import get_all_batches, create_batch
from services.master_service import MasterService
from ui.melt_batch_dialog import NewMeltBatchDialog

class MeltPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._batches = []
        self._workers = []
        self._setup_ui()
        self._load_masters()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("🔥  MELT BATCHES")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        hdr.addWidget(title)
        hdr.addStretch()
        
        self._search = SearchBar("Search…")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._filter)
        hdr.addWidget(self._search)

        filt = QComboBox()
        filt.addItems(["All", "ng_melting", "scrap_melting"])
        filt.setFixedWidth(160)
        filt.currentTextChanged.connect(self.load_batches)
        self._type_filter = filt
        hdr.addWidget(filt)

        add_btn = QPushButton("＋  New Batch")
        add_btn.setObjectName("BtnPrimary")
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        # REBUILD THE TABLE
        self._table = QTableWidget()
        self._table.setColumnCount(12)
        cols = [
            "ID", "DATE", "TYPE", "LOT", "WORKER", "PURITY",
            "INPUT (g)", "METAL A (g)", "METAL B (g)", "EXTRA ALLOY (g)",
            "FINAL 916 (g)", "NOTES"
        ]
        self._table.setHorizontalHeaderLabels(cols)
        
        # Column Widths
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 90)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(3, 80)
        self._table.setColumnWidth(4, 100)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 90)
        self._table.setColumnWidth(7, 90)
        self._table.setColumnWidth(8, 90)
        self._table.setColumnWidth(9, 100)
        self._table.setColumnWidth(10, 100)
        self._table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch)
        
        # Styling
        self._table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: #242424;
                color: #D4AF37;
                font-weight: bold;
                font-size: 12px;
                padding: 10px 8px;
                border-bottom: 2px solid #D4AF37;
            }
        """)
        self._table.verticalHeader().setDefaultSectionSize(40) # minimum 40px height
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #1F1F1F;
                background-color: #1A1A1A;
                selection-background-color: rgba(212,175,55,0.2);
                border: none;
                color: #F5F5F5;
            }
        """)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        root.addWidget(self._table, 1)

        act = QHBoxLayout()
        self._cnt = QLabel("")
        self._cnt.setStyleSheet("color:#4A5568; font-size:12px;")
        act.addWidget(self._cnt)
        act.addStretch()
        
        root.addLayout(act)
        self._overlay = LoadingOverlay(self)

    def _load_masters(self):
        w = DBWorker(MasterService.get_workers)
        w.result.connect(lambda workers: setattr(self, '_workers', workers) or self.load_batches())
        w.start()

    def load_batches(self, *_):
        self._overlay.show_over(self)
        w = DBWorker(get_all_batches)
        w.result.connect(self._on_data)
        w.error.connect(self._on_err)
        w.start()

    def _on_data(self, batches):
        self._overlay.hide_overlay()
        melt_type_filter = self._type_filter.currentText()
        if melt_type_filter != "All":
            batches = [b for b in batches if b["melt_type"] == melt_type_filter]
            
        self._batches = batches
        self._table.setRowCount(0)
        
        for i, b in enumerate(batches):
            self._table.insertRow(i)
            
            # Formatter helper
            def fmt(val):
                return f"{val:.3f}" if val is not None else "—"

            # Format TYPE
            type_map = {
                ("ng_melting", "ornaments"): "NG / Ornaments",
                ("ng_melting", "solder"): "NG / Solder",
                ("scrap_melting", "ornaments"): "Scrap / Ornaments",
                ("scrap_melting", "solder"): "Scrap / Solder"
            }
            key = (b["melt_type"], b["subtype"])
            type_str = type_map.get(key, f"{b['melt_type']} / {b['subtype']}")
            
            # Format PURITY
            is_scrap = b["melt_type"] == "scrap_melting"
            purity_str = "916 (Scrap)" if is_scrap else (str(b["purity_value"]) if b["purity_value"] else "—")
            
            # Format Metal A
            metal_a_str = "—" if is_scrap else fmt(b["metal_a_g"])
            
            # Notes truncate
            notes_str = str(b["notes"] or "")
            if len(notes_str) > 30:
                notes_str = notes_str[:27] + "..."
                
            items = [
                QTableWidgetItem(str(b["id"])),
                QTableWidgetItem(str(b["batch_date"].strftime("%d-%m-%Y") if b["batch_date"] else "—")),
                QTableWidgetItem(type_str),
                QTableWidgetItem(b["lot_display"] or "—"),
                QTableWidgetItem(str(b["worker_name"])),
                QTableWidgetItem(purity_str),
                QTableWidgetItem(fmt(b["input_weight_g"])),
                QTableWidgetItem(metal_a_str),
                QTableWidgetItem(fmt(b["metal_b_g"])),
                QTableWidgetItem(fmt(b["extra_alloy_g"])),
                QTableWidgetItem(fmt(b["final_916_g"])),
                QTableWidgetItem(notes_str),
            ]
            
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col not in (2, 4, 11) else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if col == 10:  # FINAL 916
                    item.setForeground(QColor("#D4AF37"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                self._table.setItem(i, col, item)
                
        self._cnt.setText(f"{len(batches)} batches")

    def _filter(self, text):
        t = text.lower()
        for row in range(self._table.rowCount()):
            match = False
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item and t in item.text().lower():
                    match = True
                    break
            self._table.setRowHidden(row, not match)

    def _add(self):
        dlg = NewMeltBatchDialog(self, self._workers)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                DBWorker(lambda: create_batch(d)).start()
                Toast.show_toast(self, "Melt batch created.", "success")
                self.load_batches()
            except Exception as e:
                Toast.show_toast(self, str(e), "error")

    def _on_err(self, msg): 
        self._overlay.hide_overlay()
        Toast.show_toast(self, msg, "error")
