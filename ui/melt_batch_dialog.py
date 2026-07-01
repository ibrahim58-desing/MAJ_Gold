# ============================================================
# FILE: ui/melt_batch_dialog.py
# ============================================================
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDoubleSpinBox, QLineEdit, QDateEdit, QTextEdit, QGridLayout,
    QWidget, QFrame, QScrollArea, QSizePolicy, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QCursor, QPalette

from services.master_service import MasterService
from services.melt_service import MeltService

# ── Theme Constants ──────────────────────────────────────────
BG_PRIMARY    = "#0D0D0D"
BG_SECONDARY  = "#1A1A1A"
BG_TERTIARY   = "#242424"
GOLD          = "#D4AF37"
GOLD_LIGHT    = "#F0D060"
TEXT_PRIMARY   = "#F5F5F5"
TEXT_SECONDARY = "#B0B0B0"
TEXT_MUTED     = "#888888"
SUCCESS        = "#4CAF50"
WARNING        = "#FF9800"
DANGER         = "#F44336"


# ── Label Map ────────────────────────────────────────────────
LABEL_MAP = {
    "type_a": {
        "metal_a": "Silver Weight (25%)",
        "metal_b": "Copper Weight (75%)",
    },
    "type_b": {
        "metal_a": "Silver Weight (20%)",
        "metal_b": "Zinc Weight (80%)",
    },
    "type_c": {
        "metal_a": "",
        "metal_b": "Copper Weight",
    },
    "type_d": {
        "metal_a": "",
        "metal_b": "Zinc Weight",
    },
}


# ── Pure Python Formula Functions ────────────────────────────

def calculate_type_a(input_weight, purity_value):
    purity = purity_value / 100.0
    CONSTANT_916 = 0.9160

    if input_weight <= 0:
        return {"base_916": 0.0, "metal_a": 0.0, "metal_b": 0.0, "extra_alloy": 0.0, "final_916": 0.0}

    base_916     = (input_weight * purity) / CONSTANT_916
    alloy_needed = base_916 - input_weight
    silver       = alloy_needed * 0.25
    copper       = alloy_needed * 0.75
    extra_alloy  = base_916 * 0.00022
    final_916    = base_916 + extra_alloy

    return {
        "base_916":    round(base_916, 3),
        "metal_a":     round(silver, 3),
        "metal_b":     round(copper, 3),
        "extra_alloy": round(extra_alloy, 3),
        "final_916":   round(final_916, 3)
    }

def calculate_type_b(input_weight, purity_value):
    """
    NG Melting + Solder
    Alloy split: 20% silver, 80% zinc
    Extra alloy: 0.11% of base_916
    """
    purity = purity_value / 100.0
    CONSTANT_916 = 0.9160

    if input_weight <= 0:
        return {"base_916": 0.0, "metal_a": 0.0, "metal_b": 0.0, "extra_alloy": 0.0, "final_916": 0.0}

    # STEP 1 — base 916 weight
    base_916 = (input_weight * purity) / CONSTANT_916

    # STEP 2 — alloy needed
    alloy_needed = base_916 - input_weight

    # STEP 3 — split into silver and zinc
    silver_weight = alloy_needed * 0.20
    zinc_weight   = alloy_needed * 0.80

    # STEP 4 — extra alloy (0.11% of base)
    extra_alloy = base_916 * 0.0011

    # STEP 5 — final 916 weight
    final_916 = base_916 + extra_alloy

    return {
        "base_916":    round(base_916, 3),
        "metal_a":     round(silver_weight, 3),
        "metal_b":     round(zinc_weight, 3),
        "extra_alloy": round(extra_alloy, 3),
        "final_916":   round(final_916, 3)
    }

def calculate_type_c(input_weight, purity_value):
    """
    Scrap Melting + Ornaments
    Gold is already 916. Add copper only.
    Extra alloy: 0.055% of input weight
    """
    extra_alloy = input_weight * (0.055 / 100)
    final_916   = input_weight + extra_alloy

    return {
        "base_916":    round(input_weight, 3),
        "metal_a":     0.0,
        "metal_b":     round(extra_alloy, 3),
        "extra_alloy": round(extra_alloy, 3),
        "final_916":   round(final_916, 3)
    }

def calculate_type_d(input_weight, purity_value):
    """
    Scrap Melting + Solder
    Gold is already 916. Add zinc only.
    Extra alloy: 0.25% of input weight
    """
    extra_alloy = input_weight * (0.25 / 100)
    final_916   = input_weight + extra_alloy

    return {
        "base_916":    round(input_weight, 3),
        "metal_a":     0.0,
        "metal_b":     round(extra_alloy, 3),
        "extra_alloy": round(extra_alloy, 3),
        "final_916":   round(final_916, 3)
    }


# ── Toggle Button ────────────────────────────────────────────

class ToggleButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style()
        self.toggled.connect(self._apply_style)

    def _apply_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(212,175,55,0.15);
                    color: {GOLD};
                    border: 2px solid {GOLD};
                    font-weight: bold;
                    border-radius: 10px;
                    padding: 14px 32px;
                    font-size: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_TERTIARY};
                    color: {TEXT_SECONDARY};
                    border: 1.5px solid rgba(212,175,55,0.2);
                    border-radius: 10px;
                    padding: 14px 32px;
                    font-size: 14px;
                }}
            """)


# ── Composition Bar (custom paint) ───────────────────────────

class CompositionBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.gold_w = 0.0
        self.metal_a_w = 0.0
        self.metal_b_w = 0.0
        self.extra_w = 0.0
        self.total_w = 0.0
        self.label_a = "Silver"
        self.label_b = "Copper"

    def update_values(self, gold, metal_a, metal_b, extra, total,
                      label_a="Silver", label_b="Copper"):
        self.gold_w    = gold
        self.metal_a_w = metal_a
        self.metal_b_w = metal_b
        self.extra_w   = extra
        self.total_w   = total
        self.label_a   = label_a
        self.label_b   = label_b
        self.update()

    def paintEvent(self, event):
        if self.total_w <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        bar_h = 32
        bar_y = 10
        label_y_start = bar_y + bar_h + 10

        segments = [
            (self.gold_w,    QColor("#D4AF37"), "Gold"),
            (self.metal_a_w, QColor("#C0C0C0"), self.label_a),
            (self.metal_b_w, QColor("#B87333"), self.label_b),
            (self.extra_w,   QColor("#888888"), "Extra"),
        ]

        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        x = 0
        drawn = []
        for weight, color, name in segments:
            if weight < 0.0001:
                continue
            seg_w = int((weight / self.total_w) * w)
            painter.fillRect(x, bar_y, seg_w, bar_h, color)
            drawn.append((x, seg_w, weight, color, name))
            x += seg_w

        painter.setPen(QColor("#1A1A1A"))
        for i in range(1, len(drawn)):
            lx = drawn[i][0]
            painter.drawLine(lx, bar_y, lx, bar_y + bar_h)

        for (sx, sw, weight, color, name) in drawn:
            if sw < 20:
                continue
            cx = sx + sw // 2
            pct = (weight / self.total_w) * 100

            painter.setPen(QColor("#B0B0B0"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                sx, label_y_start, sw, 18,
                Qt.AlignmentFlag.AlignHCenter, name
            )

            painter.setPen(QColor("#F5F5F5"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                sx, label_y_start + 18, sw, 18,
                Qt.AlignmentFlag.AlignHCenter,
                f"{pct:.1f}%"
            )

            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                sx, label_y_start + 34, sw, 16,
                Qt.AlignmentFlag.AlignHCenter,
                f"{weight:.3f}g"
            )

        painter.end()


# ── Add Purity Dialog ────────────────────────────────────────

class AddPurityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Purity")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_SECONDARY}; }}
            QWidget {{ background-color: {BG_SECONDARY}; color: {TEXT_PRIMARY}; }}
        """)

        layout = QVBoxLayout(self)

        self.label = QLabel("Enter purity value (e.g. 99.80)")
        layout.addWidget(self.label)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(0.00, 100.00)
        self.spinbox.setSingleStep(0.01)
        self.spinbox.setValue(99.80)
        self.spinbox.setStyleSheet(
            f"background: {BG_TERTIARY}; color: {TEXT_PRIMARY}; "
            f"padding: 8px; border: 1px solid {GOLD}; border-radius: 4px;"
        )
        layout.addWidget(self.spinbox)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            f"background: {BG_TERTIARY}; color: {TEXT_PRIMARY}; "
            f"padding: 8px; border-radius: 4px;"
        )
        self.cancel_btn.clicked.connect(self.reject)

        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet(
            f"background: {GOLD}; color: {BG_PRIMARY}; "
            f"font-weight: bold; padding: 8px; border-radius: 4px;"
        )
        self.add_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)

    def get_value(self):
        return self.spinbox.value()


# ── Main Dialog ──────────────────────────────────────────────

class NewMeltBatchDialog(QDialog):
    melt_type_changed = pyqtSignal(str)
    subtype_changed = pyqtSignal(str)

    def __init__(self, parent=None, workers=None):
        super().__init__(parent)
        self.setWindowTitle("New Melt Batch")
        
        self.setMinimumSize(800, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1A1A1A; }
            QWidget { background-color: #1A1A1A; color: #F5F5F5; }
        """)
        
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            dialog_h = min(940, geo.height() - 40)
            self.resize(880, dialog_h)
            self.move((geo.width() - 880) // 2, (geo.height() - dialog_h) // 2)
        else:
            self.resize(880, 800)

        self.workers = workers or []
        self.data_payload = {}
        self.current_melt_type = "ng_melting"
        self.current_subtype = "ornaments"

        self.setStyleSheet(self.styleSheet() + """
            QLineEdit#resultField {
                color: #FFFFFF !important;
                background-color: rgba(212,175,55,0.12);
                border: 1.5px solid rgba(212,175,55,0.5);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }
            QLineEdit#resultField:focus {
                border: 1.5px solid #D4AF37;
                background-color: rgba(212,175,55,0.18);
                color: #FFFFFF;
            }
        """)

        # MAIN LAYOUT — zero margins, zero spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # BUILD SCROLL AREA
        scroll_area = self._build_scroll_area()
        
        # BUILD FOOTER
        footer = self._build_footer()

        # ADD TO MAIN — scroll stretches, footer fixed
        main_layout.addWidget(scroll_area, stretch=1)
        main_layout.addWidget(footer, stretch=0)

        # CONNECT SIGNALS AND CALCULATE
        self._connect_signals()
        
        self.ng_melt_btn.setChecked(True)
        self.ornaments_btn.setChecked(True)

        # Set initial labels and calculate
        self.update_field_labels()
        self.run_calculation()

    # ── Type key helper ──────────────────────────────────────
    def get_current_type_key(self):
        if self.current_melt_type == "ng_melting" and self.current_subtype == "ornaments":
            return "type_a"
        elif self.current_melt_type == "ng_melting" and self.current_subtype == "solder":
            return "type_b"
        elif self.current_melt_type == "scrap_melting" and self.current_subtype == "ornaments":
            return "type_c"
        else:
            return "type_d"

    # ── Dynamic label updater ────────────────────────────────
    def update_field_labels(self):
        type_key = self.get_current_type_key()
        labels = LABEL_MAP[type_key]

        self.label_metal_a.setText(labels["metal_a"])
        self.label_metal_b.setText(labels["metal_b"])

        # Hide metal_a row for scrap types
        if type_key in ("type_c", "type_d"):
            self.label_metal_a.hide()
            self.result_metal_a.hide()
        else:
            self.label_metal_a.show()
            self.result_metal_a.show()

        # Hide extra alloy row for scrap types
        # because metal_b == extra_alloy for C and D
        if type_key in ("type_c", "type_d"):
            self.label_extra_alloy.hide()
            self.result_extra_alloy.hide()
        else:
            self.label_extra_alloy.show()
            self.result_extra_alloy.show()

    def force_white_text(self, field):
        palette = field.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 25, 10, 40))
        field.setPalette(palette)

    def make_result_field(self):
        field = QLineEdit()
        field.setObjectName("resultField")
        field.setReadOnly(False)
        field.setPlaceholderText("0.000 g")
        self.force_white_text(field)
        return field

    def _build_scroll_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1A1A1A;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #1A1A1A;
            }
            QScrollBar:vertical {
                background: #111111;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #D4AF37;
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # SCROLL CONTENT WIDGET
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #1A1A1A;")
        scroll_content.setMinimumWidth(860)
        scroll_content.setMinimumHeight(1300)

        # CONTENT LAYOUT
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(14)

        # BUILD ALL SECTIONS
        purity_section    = self._build_purity()
        melt_section      = self._build_melt_type()
        subtype_section   = self._build_subtype()
        weight_section    = self._build_weight()
        self.formula_banner = self._build_banner()
        calc_card         = self._build_calc_card()
        comp_card         = self._build_comp_card()
        batch_card        = self._build_batch_card()

        # ADD ALL TO CONTENT LAYOUT IN ORDER
        content_layout.addWidget(purity_section)
        content_layout.addWidget(melt_section)
        content_layout.addWidget(subtype_section)
        content_layout.addWidget(weight_section)
        content_layout.addWidget(self.formula_banner)
        content_layout.addWidget(calc_card)
        content_layout.addSpacing(4)
        content_layout.addWidget(comp_card)
        content_layout.addSpacing(4)
        content_layout.addWidget(batch_card)
        content_layout.addSpacing(20)
        content_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        
        # SCROLL MUST START FROM THE VERY TOP
        QTimer.singleShot(0, lambda: scroll.verticalScrollBar().setValue(0))
        
        return scroll

    def _build_purity(self):
        section_label_style = "color: #B0B0B0; font-size: 12px; font-weight: normal; background: transparent; margin-bottom: 4px;"
        input_field_style = "background: #242424; color: #F5F5F5; padding: 8px; border: 1px solid rgba(212,175,55,0.2); border-radius: 4px;"
        
        purity_section = QWidget()
        purity_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        purity_layout = QVBoxLayout(purity_section)
        purity_layout.setContentsMargins(0, 0, 0, 0)
        purity_layout.setSpacing(5)
        
        lbl_purity = QLabel("Purity Type")
        lbl_purity.setStyleSheet(section_label_style)
        purity_layout.addWidget(lbl_purity)
        
        self.purity_combo = QComboBox()
        self.purity_combo.addItems(["99.90", "99.50", "99.70"])
        self.purity_combo.setStyleSheet(input_field_style)
        purity_layout.addWidget(self.purity_combo)
        
        self.add_purity_btn = QPushButton("+ Add Custom Purity")
        self.add_purity_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_purity_btn.setStyleSheet("color: #D4AF37; border: none; text-align: left; background: transparent; padding-top: 2px; font-size: 12px;")
        self.add_purity_btn.clicked.connect(self._open_add_purity)
        purity_layout.addWidget(self.add_purity_btn)
        
        return purity_section

    def _build_melt_type(self):
        section_label_style = "color: #B0B0B0; font-size: 12px; font-weight: normal; background: transparent; margin-bottom: 4px;"
        
        melt_type_section = QWidget()
        melt_type_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        melt_layout = QVBoxLayout(melt_type_section)
        melt_layout.setContentsMargins(0, 0, 0, 0)
        melt_layout.setSpacing(10)
        
        lbl_melt = QLabel("Melt Type")
        lbl_melt.setStyleSheet(section_label_style)
        melt_layout.addWidget(lbl_melt)
        
        h_type = QHBoxLayout()
        h_type.setSpacing(12)
        self.ng_melt_btn = ToggleButton("NG Melting")
        self.scrap_melt_btn = ToggleButton("Scrap Melting")
        h_type.addWidget(self.ng_melt_btn)
        h_type.addWidget(self.scrap_melt_btn)
        melt_layout.addLayout(h_type)
        
        return melt_type_section

    def _build_subtype(self):
        section_label_style = "color: #B0B0B0; font-size: 12px; font-weight: normal; background: transparent; margin-bottom: 4px;"
        
        subtype_section = QWidget()
        subtype_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sub_layout = QVBoxLayout(subtype_section)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(10)
        
        lbl_sub = QLabel("Subtype")
        lbl_sub.setStyleSheet(section_label_style)
        sub_layout.addWidget(lbl_sub)
        
        h_sub = QHBoxLayout()
        h_sub.setSpacing(12)
        self.ornaments_btn = ToggleButton("Ornaments")
        self.solder_btn = ToggleButton("Solder")
        h_sub.addWidget(self.ornaments_btn)
        h_sub.addWidget(self.solder_btn)
        sub_layout.addLayout(h_sub)
        
        return subtype_section

    def _build_weight(self):
        section_label_style = "color: #B0B0B0; font-size: 12px; font-weight: normal; background: transparent; margin-bottom: 4px;"
        
        weight_section = QWidget()
        weight_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        weight_layout = QVBoxLayout(weight_section)
        weight_layout.setContentsMargins(0, 0, 0, 0)
        weight_layout.setSpacing(5)
        
        lbl_weight = QLabel("Gold Weight (g)")
        lbl_weight.setStyleSheet(section_label_style)
        weight_layout.addWidget(lbl_weight)
        
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0.001, 99999.999)
        self.weight_input.setDecimals(3)
        self.weight_input.setSingleStep(0.001)
        self.weight_input.setSuffix(" g")
        self.weight_input.setValue(0.000)
        self.weight_input.setStyleSheet("""
            QDoubleSpinBox {
                background: #242424;
                color: #F5F5F5;
                padding: 10px;
                border: 1px solid #D4AF37;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        weight_layout.addWidget(self.weight_input)
        
        return weight_section

    def _build_banner(self):
        banner = QLabel("Formula for this type will be configured soon")
        banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        banner.setStyleSheet("""
            background-color: rgba(255,152,0,0.1);
            border: 1px solid #FF9800;
            border-radius: 8px;
            padding: 10px 16px;
            color: #FF9800;
            font-size: 12px;
        """)
        banner.hide()
        return banner

    def _build_calc_card(self):
        calc_card = QFrame()
        calc_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        calc_card.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid rgba(212,175,55,0.2);
                border-radius: 12px;
            }
        """)
        calc_card_layout = QVBoxLayout(calc_card)
        calc_card_layout.setContentsMargins(16, 12, 16, 12)
        calc_card_layout.setSpacing(8)

        # Header Row
        title_row = QHBoxLayout()
        calc_title = QLabel("Calculated Composition")
        calc_title.setStyleSheet("color: #D4AF37; font-weight: bold; background: transparent; border: none;")
        title_row.addWidget(calc_title)
        title_row.addStretch()
        auto_label = QLabel("auto-calculated — editable")
        auto_label.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        title_row.addWidget(auto_label)
        calc_card_layout.addLayout(title_row)

        calc_card_layout.addSpacing(12)

        # Fields Grid
        calc_grid = QGridLayout()
        calc_grid.setSpacing(8)
        calc_grid.setColumnMinimumWidth(0, 200)
        calc_grid.setColumnStretch(1, 1)

        label_style = "color: #B0B0B0; font-size: 13px; background: transparent; border: none; padding-right: 16px;"

        # Row 0 — Total Gold Weight (static label)
        lbl_base = QLabel("Total Gold Weight")
        lbl_base.setStyleSheet(label_style)
        self.result_base_916 = self.make_result_field()
        calc_grid.addWidget(lbl_base, 0, 0)
        calc_grid.addWidget(self.result_base_916, 0, 1)

        # Row 1 — metal_a (dynamic label)
        self.label_metal_a = QLabel("Silver Weight (25%)")
        self.label_metal_a.setStyleSheet(label_style)
        self.result_metal_a = self.make_result_field()
        calc_grid.addWidget(self.label_metal_a, 1, 0)
        calc_grid.addWidget(self.result_metal_a, 1, 1)

        # Row 2 — metal_b (dynamic label)
        self.label_metal_b = QLabel("Copper Weight (75%)")
        self.label_metal_b.setStyleSheet(label_style)
        self.result_metal_b = self.make_result_field()
        calc_grid.addWidget(self.label_metal_b, 2, 0)
        calc_grid.addWidget(self.result_metal_b, 2, 1)

        # Row 3 — Extra Alloy (static label)
        self.label_extra_alloy = QLabel("Extra Alloy")
        self.label_extra_alloy.setStyleSheet(label_style)
        self.result_extra_alloy = self.make_result_field()
        calc_grid.addWidget(self.label_extra_alloy, 3, 0)
        calc_grid.addWidget(self.result_extra_alloy, 3, 1)

        calc_card_layout.addLayout(calc_grid)
        calc_card_layout.addSpacing(16)

        # Separator Line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(212,175,55,0.2); border: none; max-height: 1px;")
        calc_card_layout.addWidget(sep)
        calc_card_layout.addSpacing(12)

        # Final 916 Weight Display
        final_title = QLabel("Final 916 Weight")
        final_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        final_title.setStyleSheet("color: #B0B0B0; font-size: 12px; background: transparent; border: none;")
        calc_card_layout.addWidget(final_title)

        self.result_final_label = QLabel("0.000 g")
        self.result_final_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_final_label.setStyleSheet("color: #D4AF37; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        calc_card_layout.addWidget(self.result_final_label)
        
        return calc_card

    def _build_comp_card(self):
        comp_card = QFrame()
        comp_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        comp_card.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid rgba(212,175,55,0.2);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        comp_layout = QVBoxLayout(comp_card)
        comp_title = QLabel("Composition Breakdown")
        comp_title.setStyleSheet("color: #D4AF37; font-size: 13px; font-weight: bold; background: transparent; border: none; padding: 0px;")
        comp_layout.addWidget(comp_title)
        comp_layout.addSpacing(8)

        self.composition_bar = CompositionBar()
        comp_layout.addWidget(self.composition_bar)
        
        return comp_card

    def _build_batch_card(self):
        details_card = QFrame()
        details_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        details_card.setMinimumHeight(280)
        details_card.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid rgba(212,175,55,0.2);
                border-radius: 12px;
            }
        """)
        det_layout = QVBoxLayout(details_card)
        det_layout.setContentsMargins(16, 12, 16, 12)
        det_layout.setSpacing(8)

        det_title = QLabel("Batch Details")
        det_title.setStyleSheet("color: #D4AF37; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        det_layout.addWidget(det_title)

        det_grid = QGridLayout()
        det_grid.setSpacing(8)

        det_input_style = "background: #242424; color: #F5F5F5; padding: 6px; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px;"

        def _add_field(title, widget, row):
            lbl = QLabel(title)
            if "*" in title:
                text = title.replace("*", "<span style='color: #F44336;'>*</span>")
                lbl.setText(text)
            lbl.setStyleSheet("color: #F5F5F5; background: transparent; border: none;")
            det_grid.addWidget(lbl, row, 0)
            det_grid.addWidget(widget, row, 1)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setStyleSheet(det_input_style)
        _add_field("Batch Date *", self.date_edit, 0)

        self.supplier_combo = QComboBox()
        dealers = MasterService.get_dealers(active_only=True)
        if dealers:
            self.supplier_combo.addItem("Select Supplier *", userData=None)
            self.supplier_combo.setItemData(0, QColor("#666666"), Qt.ItemDataRole.ForegroundRole)
            for d in dealers:
                self.supplier_combo.addItem(d.name, userData=d.id)
        else:
            self.supplier_combo.addItem("No active suppliers")
            self.supplier_combo.model().item(0).setEnabled(False)
        self.supplier_combo.setStyleSheet(det_input_style)
        _add_field("Supplier *", self.supplier_combo, 1)

        after_weight_layout = QVBoxLayout()
        after_weight_layout.setSpacing(2)
        after_weight_layout.setContentsMargins(0, 0, 0, 0)
        self.after_melt_weight = QDoubleSpinBox()
        self.after_melt_weight.setRange(0.000, 99999.999)
        self.after_melt_weight.setDecimals(3)
        self.after_melt_weight.setSingleStep(0.001)
        self.after_melt_weight.setSuffix(" g")
        self.after_melt_weight.setValue(0.000)
        self.after_melt_weight.setStyleSheet(det_input_style)
        after_weight_layout.addWidget(self.after_melt_weight)

        hint = QLabel("Can be updated later using Edit button")
        hint.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        after_weight_layout.addWidget(hint)
        
        aw_container = QWidget()
        aw_container.setLayout(after_weight_layout)
        _add_field("After Melting Weight (g)", aw_container, 2)

        det_layout.addLayout(det_grid)
        return details_card

    def _build_footer(self):
        footer = QWidget()
        footer.setFixedHeight(64)
        footer.setStyleSheet("""
            QWidget {
                background-color: #111111;
                border-top: 1px solid rgba(212,175,55,0.25);
            }
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self.footer_weight_label = QLabel("Final 916 Weight:  0.000 g")
        self.footer_weight_label.setStyleSheet("""
            color: #D4AF37;
            font-size: 15px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #D4AF37;
                border: 1.5px solid #D4AF37;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(212,175,55,0.1);
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Batch")
        save_btn.setFixedSize(130, 40)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0 y1:0 x2:0 y2:1, stop:0 #F0D060 stop:1 #D4AF37);
                color: #0D0D0D;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0 y1:0 x2:0 y2:1, stop:0 #F5E070 stop:1 #E0C040);
            }
            QPushButton:pressed {
                background: #A0832A;
            }
        """)
        save_btn.clicked.connect(self.save_batch)

        layout.addWidget(self.footer_weight_label)
        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        return footer

    def _connect_signals(self):
        self.ng_melt_btn.clicked.connect(lambda: self._on_melt_type_click("ng_melting"))
        self.scrap_melt_btn.clicked.connect(lambda: self._on_melt_type_click("scrap_melting"))
        self.ornaments_btn.clicked.connect(lambda: self._on_subtype_click("ornaments"))
        self.solder_btn.clicked.connect(lambda: self._on_subtype_click("solder"))

        self.purity_combo.currentTextChanged.connect(self.run_calculation)
        self.weight_input.valueChanged.connect(self.run_calculation)

    def _on_melt_type_click(self, mtype):
        if mtype == "ng_melting":
            self.ng_melt_btn.setChecked(True)
            self.scrap_melt_btn.setChecked(False)
        else:
            self.ng_melt_btn.setChecked(False)
            self.scrap_melt_btn.setChecked(True)

        self.current_melt_type = mtype
        self.ornaments_btn.setChecked(True)
        self.solder_btn.setChecked(False)
        self.current_subtype = "ornaments"
        self.update_field_labels()
        self.run_calculation()

    def _on_subtype_click(self, stype):
        if stype == "ornaments":
            self.ornaments_btn.setChecked(True)
            self.solder_btn.setChecked(False)
        else:
            self.ornaments_btn.setChecked(False)
            self.solder_btn.setChecked(True)

        self.current_subtype = stype
        self.update_field_labels()
        self.run_calculation()

    def _open_add_purity(self):
        dlg = AddPurityDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            val = dlg.get_value()
            txt = f"{val:.2f}"
            if self.purity_combo.findText(txt) == -1:
                self.purity_combo.addItem(txt)
            self.purity_combo.setCurrentText(txt)

    def run_calculation(self):
        input_weight = self.weight_input.value()

        try:
            purity_value = float(
                self.purity_combo.currentText())
        except ValueError:
            return

        if input_weight <= 0:
            return

        type_key = self.get_current_type_key()

        if type_key == "type_a":
            result = calculate_type_a(
                input_weight, purity_value)
        elif type_key == "type_b":
            result = calculate_type_b(
                input_weight, purity_value)
        elif type_key == "type_c":
            result = calculate_type_c(
                input_weight, purity_value)
        elif type_key == "type_d":
            result = calculate_type_d(
                input_weight, purity_value)

        self.formula_banner.hide()

        # Update result fields
        self.result_base_916.setText(
            f"{result['base_916']:.3f} g")
        self.force_white_text(self.result_base_916)

        self.result_metal_a.setText(
            f"{result['metal_a']:.3f} g")
        self.force_white_text(self.result_metal_a)

        self.result_metal_b.setText(
            f"{result['metal_b']:.3f} g")
        self.force_white_text(self.result_metal_b)

        self.result_extra_alloy.setText(
            f"{result['extra_alloy']:.3f} g")
        self.force_white_text(self.result_extra_alloy)

        self.result_final_label.setText(
            f"{result['final_916']:.3f} g")

        self.footer_weight_label.setText(
            f"Final 916 Weight:  "
            f"{result['final_916']:.3f} g")

        # Composition bar labels per type
        label_map_bar = {
            "type_a": ("Silver", "Copper"),
            "type_b": ("Silver", "Zinc"),
            "type_c": ("",       "Copper"),
            "type_d": ("",       "Zinc"),
        }
        la, lb = label_map_bar[type_key]
        self.composition_bar.update_values(
            input_weight,
            result["metal_a"],
            result["metal_b"],
            result["extra_alloy"],
            result["final_916"],
            label_a=la,
            label_b=lb
        )

    def save_batch(self):
        if self.weight_input.value() <= 0:
            self.weight_input.setStyleSheet("""
                QDoubleSpinBox {
                    background: #242424; color: #F5F5F5;
                    padding: 10px; border: 2px solid #F44336;
                    border-radius: 4px; font-size: 14px;
                }
            """)
            return

        self.weight_input.setStyleSheet("""
            QDoubleSpinBox {
                background: #242424; color: #F5F5F5;
                padding: 10px; border: 1px solid #D4AF37;
                border-radius: 4px; font-size: 14px;
            }
        """)

        # Validation
        det_input_style = "background: #242424; color: #F5F5F5; padding: 6px; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px;"
        det_error_style = "background: #242424; color: #F5F5F5; padding: 6px; border: 2px solid #F44336; border-radius: 4px;"

        if not self.supplier_combo.currentData():
            self.supplier_combo.setStyleSheet(det_error_style)
            QMessageBox.warning(self, "Validation Error", "Supplier is required")
            return
        else:
            self.supplier_combo.setStyleSheet(det_input_style)

        def parse_field(field):
            try:
                return float(field.text().replace(" g", "").strip())
            except:
                return 0.0

        def parse_final(field):
            try:
                return float(field.text().replace(" g", "").strip())
            except:
                return 0.0
                
        qdate = self.date_edit.date()
        from datetime import date
        batch_date = date(qdate.year(), qdate.month(), qdate.day())

        self.data_payload = {
            "batch_date":      batch_date,
            "melt_type":       self.current_melt_type,
            "subtype":         self.current_subtype,
            "supplier_id":     self.supplier_combo.currentData(),
            "purity_value":    float(self.purity_combo.currentText()),
            "weight_in_g":     self.weight_input.value(),
            "base_916_g":      parse_field(self.result_base_916),
            "metal_a_g":       parse_field(self.result_metal_a),
            "metal_b_g":       parse_field(self.result_metal_b),
            "extra_alloy_g":   parse_field(self.result_extra_alloy),
            "final_916_g":     parse_final(self.result_final_label),
            "after_melt_weight": self.after_melt_weight.value()
        }
        self.accept()

    def get_data(self):
        return self.data_payload

class EditMeltBatchDialog(QDialog):
    def __init__(self, parent=None, batch_data=None):
        super().__init__(parent)
        self.batch_data = batch_data or {}
        self.setWindowTitle(f"Update Melt Batch #{self.batch_data.get('id', '')}")
        self.setFixedSize(500, 420)
        self.setStyleSheet("""
            QDialog { background-color: #1A1A1A; }
            QWidget { background-color: #1A1A1A; color: #F5F5F5; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Batch Summary Read Only Card
        summary_card = QFrame()
        summary_card.setStyleSheet("QFrame { background-color: #1A1A1A; border: 1px solid rgba(212,175,55,0.2); border-radius: 12px; }")
        sum_layout = QVBoxLayout(summary_card)
        sum_layout.setContentsMargins(16, 12, 16, 12)
        sum_title = QLabel("Batch Summary")
        sum_title.setStyleSheet("color: #D4AF37; font-weight: bold; background: transparent; border: none;")
        sum_layout.addWidget(sum_title)

        grid = QGridLayout()
        grid.setSpacing(6)
        
        def add_summary_row(row, lbl_text, val_text):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("color: #B0B0B0; background: transparent; border: none;")
            val = QLabel(val_text)
            val.setStyleSheet("color: #D4AF37; font-weight: bold; background: transparent; border: none;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)

        add_summary_row(0, "Batch ID:", f"#{self.batch_data.get('id', '')}")
        
        bdate = self.batch_data.get('batch_date')
        date_str = bdate.strftime("%d-%m-%Y") if bdate else "—"
        add_summary_row(1, "Date:", date_str)
        
        m_type = "NG Melting" if self.batch_data.get('melt_type') == "ng_melting" else "Scrap Melting"
        add_summary_row(2, "Type:", m_type)
        add_summary_row(3, "Subtype:", str(self.batch_data.get('subtype', '')).capitalize())
        add_summary_row(4, "Supplier:", str(self.batch_data.get('supplier_name', '')))
        
        in_wt = self.batch_data.get('input_weight_g', 0.0)
        add_summary_row(5, "Gold Weight:", f"{in_wt:.3f} g")
        
        fin_wt = self.batch_data.get('final_916_g', 0.0)
        add_summary_row(6, "Calculated 916:", f"{fin_wt:.3f} g")

        sum_layout.addLayout(grid)
        layout.addWidget(summary_card)

        # Update After Melting Weight Card
        edit_card = QFrame()
        edit_card.setStyleSheet("QFrame { background-color: #1A1A1A; border: 1px solid rgba(212,175,55,0.2); border-radius: 12px; }")
        edit_layout = QVBoxLayout(edit_card)
        edit_layout.setContentsMargins(16, 12, 16, 12)
        edit_layout.setSpacing(8)
        
        etitle_row = QHBoxLayout()
        edit_title = QLabel("Update After Melting Weight")
        edit_title.setStyleSheet("color: #D4AF37; font-weight: bold; background: transparent; border: none;")
        etitle_row.addWidget(edit_title)
        etitle_row.addStretch()

        current_wt = self.batch_data.get('weight_out_916_g', 0.0)
        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if current_wt <= 0:
            self.status_badge.setText("Pending")
            self.status_badge.setStyleSheet("background: rgba(255,152,0,0.15); color: #FF9800; border-radius: 6px; padding: 2px 8px; font-size: 11px;")
        else:
            self.status_badge.setText("Recorded")
            self.status_badge.setStyleSheet("background: rgba(76,175,80,0.15); color: #4CAF50; border-radius: 6px; padding: 2px 8px; font-size: 11px;")
        etitle_row.addWidget(self.status_badge)
        edit_layout.addLayout(etitle_row)

        if current_wt <= 0:
            status_txt = QLabel("After melting weight not yet recorded")
        else:
            status_txt = QLabel(f"Currently: {current_wt:.3f} g")
        status_txt.setStyleSheet("color: #B0B0B0; font-size: 12px; background: transparent; border: none;")
        edit_layout.addWidget(status_txt)
        
        edit_layout.addSpacing(4)
        
        field_layout = QHBoxLayout()
        flbl = QLabel("After Melting Weight (g) *")
        flbl.setStyleSheet("color: #F5F5F5; background: transparent; border: none;")
        field_layout.addWidget(flbl)
        
        self.edit_after_melt = QDoubleSpinBox()
        self.edit_after_melt.setRange(0.001, 99999.999)
        self.edit_after_melt.setDecimals(3)
        self.edit_after_melt.setSingleStep(0.001)
        self.edit_after_melt.setSuffix(" g")
        self.edit_after_melt.setValue(current_wt if current_wt > 0 else 0.001)
        self.edit_after_melt.setStyleSheet("background: #242424; color: #F5F5F5; padding: 6px; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px;")
        self.edit_after_melt.valueChanged.connect(self._update_loss_preview)
        field_layout.addWidget(self.edit_after_melt)
        edit_layout.addLayout(field_layout)

        self.loss_preview = QLabel("Loss: 0.000 g (0.00%)")
        self.loss_preview.setAlignment(Qt.AlignmentFlag.AlignRight)
        edit_layout.addWidget(self.loss_preview)
        
        final_916 = self.batch_data.get('final_916_g', 0.0)
        ghint = QLabel(f"Final 916 weight (before melting): {final_916:.3f} g")
        ghint.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        ghint.setAlignment(Qt.AlignmentFlag.AlignRight)
        edit_layout.addWidget(ghint)

        layout.addWidget(edit_card)
        layout.addStretch()

        # Footer
        footer = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: transparent; color: #D4AF37; border: 1.5px solid #D4AF37; border-radius: 8px; padding: 8px 16px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        
        self.update_btn = QPushButton("Update")
        self.update_btn.setStyleSheet("background: qlineargradient(x1:0 y1:0 x2:0 y2:1, stop:0 #F0D060 stop:1 #D4AF37); color: #0D0D0D; border: none; border-radius: 8px; padding: 8px 16px; font-weight: bold;")
        self.update_btn.clicked.connect(self._do_update)
        
        footer.addStretch()
        footer.addWidget(cancel_btn)
        footer.addWidget(self.update_btn)
        layout.addLayout(footer)
        
        self._update_loss_preview()

    def _update_loss_preview(self):
        final_916 = self.batch_data.get('final_916_g', 0.0)
        after = self.edit_after_melt.value()
        loss = final_916 - after
        pct = (loss / final_916 * 100) if final_916 > 0 else 0.0
        
        self.loss_preview.setText(f"Loss: {loss:.3f} g ({pct:.2f}%)")
        
        if pct < 2.0:
            self.loss_preview.setStyleSheet("color: #4CAF50; font-weight: bold; background: transparent; border: none;")
        elif pct <= 5.0:
            self.loss_preview.setStyleSheet("color: #FF9800; font-weight: bold; background: transparent; border: none;")
        else:
            self.loss_preview.setStyleSheet("color: #F44336; font-weight: bold; background: transparent; border: none;")

    def _do_update(self):
        if self.edit_after_melt.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "After melting weight must be > 0")
            return
        self.accept()

    def get_after_melt_weight(self):
        return self.edit_after_melt.value()
