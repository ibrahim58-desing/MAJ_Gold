"""GS-PCS Report page — design-wise piece count per worker per month."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from ui.widgets.widgets import DataTable, Toast, LoadingOverlay
from workers.db_worker import DBWorker
from services.process_service import ProcessService
from services.master_service import MasterService
from utils.formatters import month_year_str
from datetime import date


class GSPCSPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []; self._designs = []; self._logs = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(16)

        title = QLabel("📋  GS-PCS — Goldsmith Design-Wise Piece Report")
        title.setStyleSheet("font-size:20px; font-weight:800; color:#F0F4FF;")
        layout.addWidget(title)

        # Month filter
        bar = QHBoxLayout(); bar.setSpacing(12)
        bar.addWidget(QLabel("Month:"))
        self._month_combo = QComboBox(); self._month_combo.setFixedWidth(120)
        months = []
        d = date.today()
        for i in range(12):
            m = date(d.year, d.month, 1)
            from datetime import timedelta
            m = date(d.year - (1 if d.month - i <= 0 else 0),
                     (d.month - i - 1) % 12 + 1, 1)
            months.append(month_year_str(m))
        self._month_combo.addItems(months)
        bar.addWidget(self._month_combo)
        load_btn = QPushButton("Load Report"); load_btn.setObjectName("BtnPrimary")
        load_btn.clicked.connect(self._load_report)
        bar.addWidget(load_btn); bar.addStretch()
        layout.addLayout(bar)

        # Cross-tab matrix table
        self._matrix = QTableWidget()
        self._matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._matrix.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._matrix.verticalHeader().setVisible(False)
        self._matrix.setStyleSheet("""
            QTableWidget { background:#0D1121; color:#D0D8F0; border:none; font-size:12px;
                           gridline-color:#1A2240; selection-background-color:rgba(245,166,35,0.15);}
            QTableWidget::item { padding:8px 10px; border-bottom:1px solid #151D30; }
            QHeaderView::section { background:#131929; color:#F5A623; font-weight:700;
                                   font-size:11px; padding:8px; border:none;
                                   border-bottom:1px solid #1E2640; letter-spacing:0.8px; }
        """)
        self._matrix.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._matrix.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._matrix, 1)

        # Totals row info
        self._totals_lbl = QLabel("")
        self._totals_lbl.setStyleSheet("color:#F5A623; font-size:13px; font-weight:700; padding:6px 0;")
        layout.addWidget(self._totals_lbl)

        self._overlay = LoadingOverlay(self)
        self._load_masters()

    def _load_masters(self):
        w1 = DBWorker(MasterService.get_workers)
        w1.result.connect(lambda w: setattr(self, '_workers', w))
        w1.start()
        w2 = DBWorker(MasterService.get_design_types)
        w2.result.connect(lambda d: setattr(self, '_designs', d))
        w2.start()

    def _load_report(self):
        month = self._month_combo.currentText()
        self._overlay.show_over(self)
        w = DBWorker(ProcessService.get_design_logs, month_year=month)
        w.result.connect(lambda logs: self._build_matrix(logs, month))
        w.error.connect(lambda m: (self._overlay.hide_overlay(), Toast.show_toast(self, m, "error")))
        w.start()

    def _build_matrix(self, logs, month):
        self._overlay.hide_overlay()
        if not logs:
            self._matrix.setRowCount(0); self._matrix.setColumnCount(0)
            self._totals_lbl.setText(f"No data for {month}")
            return

        design_codes = [d.code for d in self._designs]
        worker_map = {w.id: w.code for w in self._workers}

        # Aggregate: {worker_id: {design_code: pcs}}
        data = {}
        for log in logs:
            wid = log.worker_id
            design_code = next((d.code for d in self._designs if d.id == log.design_type_id), "?")
            if wid not in data: data[wid] = {}
            data[wid][design_code] = data[wid].get(design_code, 0) + log.pieces_count

        worker_ids = sorted(data.keys())
        cols = ["Worker"] + design_codes + ["TOTAL"]
        self._matrix.setColumnCount(len(cols))
        self._matrix.setHorizontalHeaderLabels(cols)
        self._matrix.setRowCount(len(worker_ids) + 1)  # +1 for totals row

        design_totals = {d: 0 for d in design_codes}
        grand_total = 0

        for r, wid in enumerate(worker_ids):
            w_name = worker_map.get(wid, str(wid))
            row_total = 0
            self._matrix.setItem(r, 0, QTableWidgetItem(w_name))
            for c, dc in enumerate(design_codes):
                pcs = data[wid].get(dc, 0)
                item = QTableWidgetItem(str(pcs) if pcs else "—")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if pcs > 0:
                    item.setForeground(Qt.GlobalColor.white)
                self._matrix.setItem(r, c + 1, item)
                row_total += pcs
                design_totals[dc] = design_totals.get(dc, 0) + pcs
            grand_total += row_total
            tot_item = QTableWidgetItem(str(row_total))
            tot_item.setForeground(Qt.GlobalColor.yellow)
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._matrix.setItem(r, len(cols) - 1, tot_item)

        # Totals row
        tr = len(worker_ids)
        tot_lbl = QTableWidgetItem("TOTAL")
        tot_lbl.setForeground(Qt.GlobalColor.yellow)
        self._matrix.setItem(tr, 0, tot_lbl)
        for c, dc in enumerate(design_codes):
            v = design_totals.get(dc, 0)
            item = QTableWidgetItem(str(v))
            item.setForeground(Qt.GlobalColor.yellow)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._matrix.setItem(tr, c + 1, item)
        gt_item = QTableWidgetItem(str(grand_total))
        gt_item.setForeground(Qt.GlobalColor.yellow)
        gt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix.setItem(tr, len(cols) - 1, gt_item)

        self._totals_lbl.setText(
            f"Month: {month}  |  Total Workers: {len(worker_ids)}  |  Grand Total Pieces: {grand_total}")
