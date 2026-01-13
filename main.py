import sys
import os
import threading
import time
import urllib.request
import webview
from blueprints.github_version_file import VERSION as APP_VERSION

FLASK_URL = "http://127.0.0.1:5000"


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def start_flask():
    from app import app, app_startup_tasks
    app_startup_tasks()
    app.run(debug=False, use_reloader=False, threaded=True)


def wait_for_flask_and_load(window, timeout=30):
    """Wait for Flask server to be ready, then load the URL."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(FLASK_URL, timeout=1)
            window.load_url(FLASK_URL)
            return
        except Exception:
            time.sleep(0.1)


def on_loaded(window):
    """Called when loading screen DOM is ready."""
    # Unsubscribe immediately to prevent being called again when Flask page loads
    window.events.loaded -= on_loaded
    # Start polling Flask in a separate thread
    threading.Thread(target=wait_for_flask_and_load, args=(window,), daemon=True).start()


def load_loading_html():
    """Load the loading screen HTML from file."""
    loading_path = os.path.join(get_base_dir(), "loading.html")
    with open(loading_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Create window with dark background color (shown before WebView loads)
    # and loading HTML (shown once WebView initializes)

    version_string = f" - {APP_VERSION.strip()}" if APP_VERSION else ""

    window = webview.create_window(
        title=f"OP-1Z Sample Manager{version_string}",
        html=load_loading_html(),
        width=1280,
        height=800,
        background_color="#1a1a1a",  # Matches loading screen - no white flash
        text_select=True
    )

    # Wait for loading screen DOM to be ready, then start polling Flask
    window.events.loaded += on_loaded

    # Start the webview (blocks until window is closed)
    webview.start()
