"""
MAJ GOLD — Futuristic Dark Theme (QSS)
Gold-accented space-tech aesthetic.
"""

THEME = """
/* ═══════════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════════ */
QMainWindow, QDialog, QWidget {
    background-color: #0A0C14;
    color: #F0F4FF;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical {
    background: #0F1420; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2A3347; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #F5A623; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal {
    background: #0F1420; height: 8px; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #2A3347; border-radius: 4px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #F5A623; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ═══════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════ */
#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #07090F, stop:1 #0E1220);
    border-right: 1px solid #1E2640;
    min-width: 220px; max-width: 220px;
}
#SidebarLogo {
    color: #F5A623;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 20px 16px 8px 16px;
}
#SidebarTagline {
    color: #4A5568;
    font-size: 10px;
    letter-spacing: 1px;
    padding: 0 16px 16px 16px;
}
#SidebarSep {
    color: #1E2640;
    font-size: 9px;
    padding: 4px 12px;
}
QPushButton#NavBtn {
    background: transparent;
    color: #8A9BB5;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#NavBtn:hover {
    background: rgba(245,166,35,0.08);
    color: #F0F4FF;
}
QPushButton#NavBtn[active="true"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(245,166,35,0.18), stop:1 rgba(245,166,35,0.04));
    color: #F5A623;
    border-left: 3px solid #F5A623;
    font-weight: 700;
}

/* ═══════════════════════════════════════════════════
   HEADER BAR
═══════════════════════════════════════════════════ */
#HeaderBar {
    background: rgba(10,12,20,0.98);
    border-bottom: 1px solid #1E2640;
    min-height: 56px; max-height: 56px;
}
#PageTitle {
    color: #F0F4FF;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
#PageSubtitle { color: #4A5568; font-size: 11px; }
#HeaderDate { color: #F5A623; font-size: 11px; font-weight: 600; }

/* ═══════════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════════ */
#Card {
    background: rgba(17,24,39,0.95);
    border: 1px solid #1E2640;
    border-radius: 12px;
}
#Card:hover { border-color: #2A3347; }
#CardGold {
    background: rgba(17,24,39,0.95);
    border: 1px solid rgba(245,166,35,0.3);
    border-radius: 12px;
}
#StatValue {
    color: #F5A623;
    font-size: 28px;
    font-weight: 800;
}
#StatLabel {
    color: #8A9BB5;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
#StatIcon { font-size: 32px; }

/* ═══════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════ */
QPushButton#BtnPrimary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #F5A623, stop:1 #E8C547);
    color: #0A0C14;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 700;
    font-size: 13px;
    min-height: 36px;
}
QPushButton#BtnPrimary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #FFB84D, stop:1 #F0D060);
}
QPushButton#BtnPrimary:pressed { background: #C8881A; }
QPushButton#BtnPrimary:disabled { background: #2A3347; color: #4A5568; }

QPushButton#BtnSecondary {
    background: rgba(42,51,71,0.6);
    color: #8A9BB5;
    border: 1px solid #2A3347;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 36px;
}
QPushButton#BtnSecondary:hover {
    background: rgba(42,51,71,0.9);
    color: #F0F4FF;
    border-color: #3A4560;
}

QPushButton#BtnDanger {
    background: rgba(255,71,87,0.12);
    color: #FF4757;
    border: 1px solid rgba(255,71,87,0.3);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 36px;
}
QPushButton#BtnDanger:hover { background: rgba(255,71,87,0.22); }

QPushButton#BtnSuccess {
    background: rgba(46,213,115,0.12);
    color: #2ED573;
    border: 1px solid rgba(46,213,115,0.3);
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 36px;
}
QPushButton#BtnSuccess:hover { background: rgba(46,213,115,0.22); }

QPushButton#BtnIcon {
    background: transparent;
    border: none;
    padding: 4px;
    font-size: 16px;
    color: #8A9BB5;
    border-radius: 6px;
    min-width: 32px; max-width: 32px;
    min-height: 32px; max-height: 32px;
}
QPushButton#BtnIcon:hover { background: rgba(42,51,71,0.6); color: #F5A623; }

/* ═══════════════════════════════════════════════════
   TABLE
═══════════════════════════════════════════════════ */
QTableWidget {
    background: #0D1121;
    gridline-color: #1A2240;
    color: #D0D8F0;
    border: none;
    border-radius: 0px;
    selection-background-color: rgba(245,166,35,0.15);
    selection-color: #F5A623;
    font-size: 12px;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #151D30;
}
QTableWidget::item:hover { background: rgba(30,42,70,0.6); }
QTableWidget::item:selected {
    background: rgba(245,166,35,0.15);
    color: #F5A623;
}
QHeaderView { background: #0A0C14; }
QHeaderView::section {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #131929, stop:1 #0E1420);
    color: #F5A623;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.8px;
    padding: 10px 10px;
    border: none;
    border-bottom: 1px solid #1E2640;
    border-right: 1px solid #1A2035;
    text-transform: uppercase;
}
QHeaderView::section:hover { background: #1A2640; }

/* ═══════════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════════ */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #0E1525;
    color: #F0F4FF;
    border: 1px solid #2A3347;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: rgba(245,166,35,0.3);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #F5A623;
    background: #111827;
}
QLineEdit:disabled { background: #0A0C14; color: #4A5568; }
QLineEdit::placeholder { color: #4A5568; }

QSpinBox, QDoubleSpinBox {
    background: #0E1525;
    color: #F0F4FF;
    border: 1px solid #2A3347;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #F5A623; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: #1A2035; border: none; width: 20px;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: none; color: #F5A623; }

QComboBox {
    background: #0E1525;
    color: #F0F4FF;
    border: 1px solid #2A3347;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}
QComboBox:focus { border-color: #F5A623; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { color: #F5A623; }
QComboBox QAbstractItemView {
    background: #111827;
    color: #F0F4FF;
    border: 1px solid #2A3347;
    selection-background-color: rgba(245,166,35,0.2);
    selection-color: #F5A623;
    outline: none;
}

QDateEdit {
    background: #0E1525;
    color: #F0F4FF;
    border: 1px solid #2A3347;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
}
QDateEdit:focus { border-color: #F5A623; }
QDateEdit::drop-down { border: none; width: 24px; }
QCalendarWidget QAbstractItemView {
    background: #111827;
    color: #F0F4FF;
    selection-background-color: #F5A623;
    selection-color: #0A0C14;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: #1A2035;
}

/* ═══════════════════════════════════════════════════
   LABELS & MISC
═══════════════════════════════════════════════════ */
QLabel#SectionTitle {
    color: #F0F4FF;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#FieldLabel {
    color: #8A9BB5;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#BadgeGold {
    background: rgba(245,166,35,0.15);
    color: #F5A623;
    border: 1px solid rgba(245,166,35,0.3);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#BadgeSuccess {
    background: rgba(46,213,115,0.12);
    color: #2ED573;
    border: 1px solid rgba(46,213,115,0.3);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
}
QLabel#BadgeDanger {
    background: rgba(255,71,87,0.12);
    color: #FF4757;
    border: 1px solid rgba(255,71,87,0.3);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
}

/* ═══════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════ */
QTabWidget::pane {
    border: 1px solid #1E2640;
    border-radius: 8px;
    background: #0D1121;
    top: -1px;
}
QTabBar::tab {
    background: #0A0C14;
    color: #8A9BB5;
    border: 1px solid #1E2640;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #111827;
    color: #F5A623;
    border-color: #2A3347;
    border-bottom: 2px solid #F5A623;
}
QTabBar::tab:hover { color: #F0F4FF; background: #111827; }

/* ═══════════════════════════════════════════════════
   DIALOGS
═══════════════════════════════════════════════════ */
QDialog {
    background: #0E1220;
    border: 1px solid #2A3347;
    border-radius: 12px;
}
#DialogTitle {
    color: #F5A623;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
#DialogSep {
    background: #1E2640;
    max-height: 1px;
    min-height: 1px;
}
QMessageBox {
    background: #0E1220;
    color: #F0F4FF;
}

/* ═══════════════════════════════════════════════════
   CHECKBOXES & RADIO
═══════════════════════════════════════════════════ */
QCheckBox { color: #8A9BB5; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    background: #0E1525;
    border: 1px solid #2A3347;
    border-radius: 4px;
}
QCheckBox::indicator:checked {
    background: #F5A623;
    border-color: #F5A623;
}

/* ═══════════════════════════════════════════════════
   PROGRESS / LOADING
═══════════════════════════════════════════════════ */
QProgressBar {
    background: #111827;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #F5A623, stop:1 #E8C547);
    border-radius: 4px;
}

/* ═══════════════════════════════════════════════════
   TOAST NOTIFICATION
═══════════════════════════════════════════════════ */
#Toast {
    background: rgba(17,24,39,0.97);
    border-radius: 10px;
    border: 1px solid #2A3347;
}
#ToastSuccess { border-left: 4px solid #2ED573; }
#ToastError   { border-left: 4px solid #FF4757; }
#ToastInfo    { border-left: 4px solid #1E90FF; }
#ToastWarning { border-left: 4px solid #F5A623; }
"""


def apply_theme(app):
    """Apply the dark theme to the QApplication."""
    app.setStyleSheet(THEME)
