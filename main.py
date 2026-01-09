import sys
import os
import threading
import webview

FLASK_URL = "http://127.0.0.1:5000"


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def start_flask():
    from app import app, app_startup_tasks
    app_startup_tasks()
    app.run(debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Create window with pywebview
    window = webview.create_window(
        title="OP-1Z Sample Manager",
        url=FLASK_URL,
        width=1280,
        height=720,
    )

    # Start the webview (blocks until window is closed)
    webview.start()
