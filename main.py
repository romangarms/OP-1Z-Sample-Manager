import sys
import os
import threading
import time
import webview
from urllib.request import urlopen
from urllib.error import URLError

# Disable GPU acceleration for WebKit (may fix rendering issues on ARM64)
os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'
os.environ['WEBKIT_DISABLE_DMABUF_RENDERER'] = '1'

FLASK_URL = "http://127.0.0.1:5000"


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def start_flask():
    from app import app, app_startup_tasks
    app_startup_tasks()
    app.run(debug=False, use_reloader=False, threaded=True)


def wait_for_flask(timeout=10):
    """Wait for Flask server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urlopen(FLASK_URL, timeout=1)
            print("Flask server is ready")
            return True
        except (URLError, ConnectionRefusedError):
            time.sleep(0.1)
    print("Flask server failed to start in time")
    return False


if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Wait for Flask to be ready before creating the window
    if not wait_for_flask():
        print("Error: Flask server did not start")
        sys.exit(1)

    # Create window with pywebview
    window = webview.create_window(
        title="OP-Z Sample Manager",
        url=FLASK_URL,
        width=1280,
        height=720,
    )

    # Start the webview (blocks until window is closed)
    webview.start()
