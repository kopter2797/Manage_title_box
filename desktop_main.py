import webview
import threading
import time
import sys
import warnings
from app import app

# Suppress pywebview deprecation warning for FOLDER_DIALOG
warnings.filterwarnings('ignore', message='.*FOLDER_DIALOG.*')

class Api:
    """API class exposed to JavaScript in the webview"""
    
    def __init__(self):
        self._window = None
    
    def set_window(self, window):
        self._window = window
    
    def select_folder(self):
        """Opens a folder selection dialog and returns the selected path"""
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False
        )
        if result and len(result) > 0:
            return result[0]
        return None
    
    def select_folders(self):
        """Opens a folder selection dialog that allows multiple selections"""
        if self._window is None:
            return []
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=True
        )
        if result:
            return list(result)
        return []

def start_server():
    """
    Starts the Flask application in a separate thread.
    """
    # Run Flask app with debug=False to avoid reloader issues in a thread
    app.run(port=5000, threaded=True, debug=False, use_reloader=False)

if __name__ == '__main__':
    # 1. Start Flask in a background thread
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. Wait a moment for the server to start
    time.sleep(1)
    
    # 3. Create API instance
    api = Api()

    # 4. Create the window with js_api
    window = webview.create_window(
        'Manage Title Box',
        'http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True,
        js_api=api
    )
    
    # 5. Set window reference in API
    api.set_window(window)

    # 6. Start the GUI loop
    webview.start()
    
    # Ensure clean exit
    sys.exit()