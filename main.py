"""
MAJ GOLD — Application Entry Point
Splash screen → DB init → Main Window
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont, QPixmap, QPainter, QLinearGradient, QGradient

from ui.styles.theme import apply_theme
from config.settings import COMPANY_NAME, COMPANY_TAGLINE, APP_VERSION


class DBInitWorker(QThread):
    done = pyqtSignal(bool, str)

    def run(self):
        try:
            from database.models.base import init_db
            init_db()
            self.done.emit(True, "")
        except Exception as e:
            self.done.emit(False, str(e))


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 300)
        self._center()
        self._build_ui()

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 36)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel(COMPANY_NAME)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            "color:#F5A623; font-size:42px; font-weight:900; "
            "letter-spacing:6px; background:transparent;"
        )
        tagline = QLabel(COMPANY_TAGLINE.upper())
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(
            "color:#4A5568; font-size:11px; letter-spacing:3px; background:transparent;"
        )

        sep = QLabel("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet("color:#1E2640; background:transparent; font-size:10px;")

        self._status = QLabel("Initialising database…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color:#8A9BB5; font-size:12px; background:transparent;")

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet("""
            QProgressBar { background:#1A2035; border:none; border-radius:2px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #F5A623, stop:1 #E8C547);
                border-radius:2px;
            }
        """)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color:#2A3347; font-size:10px; background:transparent;")

        layout.addWidget(logo)
        layout.addWidget(tagline)
        layout.addWidget(sep)
        layout.addStretch()
        layout.addWidget(self._status)
        layout.addWidget(self._bar)
        layout.addSpacing(8)
        layout.addWidget(ver)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#0E1220"))
        grad.setColorAt(1, QColor("#07090F"))
        painter.setBrush(grad)
        painter.setPen(QColor("#2A3347"))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

    def set_status(self, msg: str):
        self._status.setText(msg)

    def set_progress_done(self):
        self._bar.setRange(0, 100)
        self._bar.setValue(100)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(COMPANY_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Apply global theme
    apply_theme(app)

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Splash
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # DB init worker
    db_worker = DBInitWorker()

    def on_db_done(success: bool, err: str):
        if not success:
            splash.set_status(f"❌ DB Error: {err}")
            QTimer.singleShot(3000, app.quit)
            return

        splash.set_status("✅ Database ready. Launching…")
        splash.set_progress_done()
        app.processEvents()

        QTimer.singleShot(600, lambda: _launch(splash))

    def _launch(splash):
        from ui.main_window import MainWindow
        splash.close()
        win = MainWindow()
        win.show()
        # Keep reference
        app._main_window = win

    db_worker.done.connect(on_db_done)
    db_worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
