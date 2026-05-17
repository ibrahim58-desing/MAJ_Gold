"""Sidebar navigation widget."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from config.settings import NAV_ITEMS, COMPANY_NAME, COMPANY_TAGLINE


class Sidebar(QWidget):
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Logo
        logo_lbl = QLabel(COMPANY_NAME)
        logo_lbl.setObjectName("SidebarLogo")
        tagline_lbl = QLabel(COMPANY_TAGLINE.upper())
        tagline_lbl.setObjectName("SidebarTagline")
        outer.addWidget(logo_lbl)
        outer.addWidget(tagline_lbl)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1E2640; margin:0 12px;")
        outer.addWidget(sep)
        outer.addSpacing(8)

        # Scrollable nav area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        nav_widget = QWidget()
        nav_widget.setStyleSheet("background:transparent;")
        self._nav_layout = QVBoxLayout(nav_widget)
        self._nav_layout.setContentsMargins(8, 4, 8, 8)
        self._nav_layout.setSpacing(2)

        self._buttons = {}
        self._active_key = None

        for label, icon, key in NAV_ITEMS:
            if key is None:
                # Separator label
                sep_lbl = QLabel(label)
                sep_lbl.setObjectName("SidebarSep")
                sep_lbl.setStyleSheet("color:#1E2640; font-size:9px; padding:6px 8px 2px 8px;")
                self._nav_layout.addWidget(sep_lbl)
            else:
                btn = QPushButton(f"  {icon}  {label}")
                btn.setObjectName("NavBtn")
                btn.setProperty("active", "false")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, k=key: self._on_nav(k))
                self._nav_layout.addWidget(btn)
                self._buttons[key] = btn

        self._nav_layout.addStretch()
        scroll.setWidget(nav_widget)
        outer.addWidget(scroll, 1)

        # Version label
        ver = QLabel("v1.0.0")
        ver.setStyleSheet("color:#2A3347; font-size:10px; padding:8px 16px;")
        outer.addWidget(ver)

    def _on_nav(self, key: str):
        self.set_active(key)
        self.page_changed.emit(key)

    def set_active(self, key: str):
        if self._active_key and self._active_key in self._buttons:
            btn = self._buttons[self._active_key]
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._active_key = key
        if key in self._buttons:
            btn = self._buttons[key]
            btn.setProperty("active", "true")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
