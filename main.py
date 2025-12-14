import sys
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from PyQt5 import QtGui
import os

FLASK_URL = "http://127.0.0.1:5000"


def start_flask():
    from app import app, app_startup_tasks
    app_startup_tasks()
    app.run(debug=False, use_reloader=False)


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OP-Z Sample Manager")
        self.setWindowIcon(QtGui.QIcon(os.path.join(get_base_dir(), 'static', 'favicon.png')))
        self.setGeometry(100, 100, 1280, 720)

        self.browser = QWebEngineView()
        self.browser.loadFinished.connect(self.on_load_finished)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.browser, stretch=1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Start loading after a brief delay to let Flask initialize
        QTimer.singleShot(100, self.load_flask_url)

    def load_flask_url(self):
        self.browser.setUrl(QUrl(FLASK_URL))

    def on_load_finished(self, ok):
        if not ok:
            # Flask not ready yet, retry after 200ms
            QTimer.singleShot(200, self.load_flask_url)

    def closeEvent(self, event):
        event.accept()

if __name__ == "__main__":
    # Create QApplication first (required for frozen apps)
    qt_app = QApplication(sys.argv)

    # Start Flask after QApplication exists
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    window = MainWindow()
    window.show()
    sys.exit(qt_app.exec_())
