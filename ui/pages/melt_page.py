"""Melt Batches page — NG Melting and Scrap Melting."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QCursor
from ui.widgets.widgets import SearchBar, Toast, LoadingOverlay, ConfirmDialog
from workers.db_worker import DBWorker
from services.melt_batch_service import get_all_batches, create_batch, delete_batch, update_after_melt
from services.master_service import MasterService
from ui.melt_batch_dialog import NewMeltBatchDialog, EditMeltBatchDialog

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
        self._table.setColumnCount(11)
        cols = [
            "ID", "DATE", "TYPE", "SUBTYPE", "SUPPLIER", "INPUT (g)",
            "FINAL 916 (g)", "AFTER MELT (g)", "LOSS (g)", "ALLOYS", "ACTIONS"
        ]
        self._table.setHorizontalHeaderLabels(cols)
        
        # Column Widths
        self._table.setColumnWidth(0, 55)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 95)
        self._table.setColumnWidth(4, 120)
        self._table.setColumnWidth(5, 100)
        self._table.setColumnWidth(6, 110)
        self._table.setColumnWidth(7, 120)
        self._table.setColumnWidth(8, 90)
        self._table.setColumnWidth(9, 170)
        self._table.setColumnWidth(10, 180)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        
        # Styling
        self._table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: #242424;
                color: #D4AF37;
                font-weight: bold;
                font-size: 13px;
                padding: 12px 10px;
                border-bottom: 2px solid #D4AF37;
            }
        """)
        self._table.verticalHeader().setDefaultSectionSize(72)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #1F1F1F;
                background-color: #1A1A1A;
                selection-background-color: rgba(212,175,55,0.2);
                border: none;
                color: #F5F5F5;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px 10px;
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
            
            def fmt(val):
                return f"{val:.3f}" if val is not None else "—"

            type_map = {
                "ng_melting": "NG Melting",
                "scrap_melting": "Scrap Melting"
            }
            type_str = type_map.get(b["melt_type"], b["melt_type"])
            subtype_str = b["subtype"].capitalize()
            
            items = [
                QTableWidgetItem(str(b["id"])),
                QTableWidgetItem(str(b["batch_date"].strftime("%d-%m-%Y") if b["batch_date"] else "—")),
                QTableWidgetItem(type_str),
                QTableWidgetItem(subtype_str),
                QTableWidgetItem(str(b["supplier_name"])),
                QTableWidgetItem(fmt(b["input_weight_g"])),
                QTableWidgetItem(fmt(b["final_916_g"]))
            ]
            
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col not in (2, 3, 4) else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(i, col, item)
            
            # Column 7: After Melt (g)
            after_melt_val = b.get("weight_out_916_g", 0.0)
            aw_widget = QWidget()
            aw_layout = QHBoxLayout(aw_widget)
            aw_layout.setContentsMargins(4, 4, 4, 4)
            aw_lbl = QLabel()
            aw_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if after_melt_val <= 0:
                aw_lbl.setText("Pending")
                aw_lbl.setStyleSheet("background: rgba(255,152,0,0.15); color: #FF9800; border-radius: 6px; padding: 2px 8px;")
            else:
                aw_lbl.setText(f"{after_melt_val:.3f} g")
                aw_lbl.setStyleSheet("color: #FFFFFF;")
            aw_layout.addWidget(aw_lbl)
            aw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(i, 7, aw_widget)

            # Column 8: Loss (g) — loss = final_916 - after_melt
            loss_val = b.get("loss_g", 0.0)
            final_916 = b.get("final_916_g", 0.0)
            pct = (loss_val / final_916 * 100) if final_916 > 0 else 0.0
            
            loss_item = QTableWidgetItem()
            if after_melt_val <= 0:
                loss_item.setText("—")
                loss_item.setForeground(QColor("#666666"))
            else:
                loss_item.setText(f"{loss_val:.3f}")
                if pct < 2.0:
                    loss_item.setForeground(QColor("#4CAF50"))
                elif pct <= 5.0:
                    loss_item.setForeground(QColor("#FF9800"))
                else:
                    loss_item.setForeground(QColor("#F44336"))
            loss_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 8, loss_item)

            # Column 9: Alloys — multi-line breakdown
            alloy_widget = QWidget()
            alloy_vlayout = QVBoxLayout(alloy_widget)
            alloy_vlayout.setContentsMargins(6, 4, 6, 4)
            alloy_vlayout.setSpacing(1)

            melt_type = b.get("melt_type", "")
            subtype = b.get("subtype", "")
            metal_a = b.get("metal_a_g", 0.0)
            metal_b = b.get("metal_b_g", 0.0)
            extra   = b.get("extra_alloy_g", 0.0)

            # Determine labels based on type
            if subtype == "ornaments":
                label_a, label_b = "Silver", "Copper"
            else:
                label_a, label_b = "Silver", "Zinc"

            alloy_lines = []
            if metal_a > 0:
                alloy_lines.append((label_a, metal_a, "#C0C0C0"))
            if metal_b > 0:
                alloy_lines.append((label_b, metal_b, "#B87333" if label_b == "Copper" else "#A8A8A8"))
            if extra > 0:
                alloy_lines.append(("Extra", extra, "#888888"))

            if not alloy_lines:
                none_lbl = QLabel("None")
                none_lbl.setStyleSheet("color: #666666; font-size: 11px;")
                alloy_vlayout.addWidget(none_lbl)
            else:
                for name, wt, color in alloy_lines:
                    line_lbl = QLabel(f'<span style="color:{color};">{name}:</span> <span style="color:#F5F5F5;">{wt:.3f}g</span>')
                    line_lbl.setStyleSheet("font-size: 11px; background: transparent;")
                    alloy_vlayout.addWidget(line_lbl)

            self._table.setCellWidget(i, 9, alloy_widget)

            # Column 10: Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            
            btn_edit = QPushButton("✏ Edit")
            btn_edit.setFixedSize(70, 30)
            btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_edit.setStyleSheet("""
                QPushButton {
                    background: rgba(212,175,55,0.1);
                    color: #D4AF37;
                    border: 1.5px solid rgba(212,175,55,0.5);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background: rgba(212,175,55,0.25); }
            """)
            btn_edit.clicked.connect(lambda checked, bd=b: self._edit_batch(bd))
            
            btn_delete = QPushButton("🗑 Del")
            btn_delete.setFixedSize(65, 30)
            btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_delete.setStyleSheet("""
                QPushButton {
                    background: rgba(244,67,54,0.1);
                    color: #F44336;
                    border: 1.5px solid rgba(244,67,54,0.5);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background: rgba(244,67,54,0.25); }
            """)
            btn_delete.clicked.connect(lambda checked, bid=b["id"]: self._delete_batch(bid))
            
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_delete)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(i, 10, action_widget)

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
            self._overlay.show_over(self)
            
            def handle_result(res):
                self._overlay.hide_overlay()
                if isinstance(res, dict) and not res.get("success"):
                    Toast.show_toast(self, res.get("error", "Failed to save"), "error")
                else:
                    Toast.show_toast(self, "Melt batch created.", "success")
                    self.load_batches()
                    
            w = DBWorker(lambda: create_batch(d))
            w.result.connect(handle_result)
            w.error.connect(self._on_err)
            w.start()

    def _edit_batch(self, batch_data):
        dlg = EditMeltBatchDialog(self, batch_data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            after_melt = dlg.get_after_melt_weight()
            self._overlay.show_over(self)
            
            def handle_result(res):
                self._overlay.hide_overlay()
                if isinstance(res, dict) and not res.get("success"):
                    Toast.show_toast(self, res.get("error", "Failed to update"), "error")
                else:
                    Toast.show_toast(self, "Batch updated successfully.", "success")
                    self.load_batches()
                    
            w = DBWorker(lambda: update_after_melt(batch_data["id"], after_melt))
            w.result.connect(handle_result)
            w.error.connect(self._on_err)
            w.start()

    def _delete_batch(self, batch_id):
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Delete Batch #{batch_id}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._overlay.show_over(self)
            
            def handle_result(res):
                self._overlay.hide_overlay()
                if isinstance(res, dict) and not res.get("success"):
                    Toast.show_toast(self, res.get("error", "Failed to delete"), "error")
                else:
                    Toast.show_toast(self, "Batch deleted.", "success")
                    self.load_batches()
                    
            w = DBWorker(lambda: delete_batch(batch_id))
            w.result.connect(handle_result)
            w.error.connect(self._on_err)
            w.start()

    def _on_err(self, msg): 
        self._overlay.hide_overlay()
        Toast.show_toast(self, msg, "error")
