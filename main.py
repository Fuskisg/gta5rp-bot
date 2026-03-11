import sys
import os
import threading
from flask import Flask
from pynput import keyboard
from core.common import hotkey_manager, get_settings
import socket
import time
from core.api import fetch_online_once, check_update_once
from pages import pages_bp
from pages.antiafk import VGAMEPAD_AVAILABLE
import ctypes

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QUrl, QObject, Slot, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = False
app.config['ENV'] = 'production'
app.register_blueprint(pages_bp)

class WindowBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self._window = window

    @Slot()
    def minimize(self):
        self._window.showMinimized()

    @Slot()
    def closeWindow(self):
        self._window.close()

    @Slot(int, int)
    def moveWindow(self, x, y):
        self._window.move(x, y)

    @Slot(result='QVariantMap')
    def getPosition(self):
        pos = self._window.pos()
        return {'x': int(pos.x()), 'y': int(pos.y())}

class ExternalPage(QWebEnginePage):
    def createWindow(self, window_type):
        temp_page = QWebEnginePage(self)
        temp_page.urlChanged.connect(self._open_external)
        return temp_page

    def _open_external(self, url):
        QDesktopServices.openUrl(url)
        self.sender().deleteLater()


class MainWindow(QMainWindow):
    def __init__(self, url, width, height, x, y):
        super().__init__()
        self.setWindowTitle('Steam Client WebHelper')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(width, height)
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.move(x, y)

        self.browser = QWebEngineView(self)
        self._page = ExternalPage(self.browser)
        self.browser.setPage(self._page)
        self.setCentralWidget(self.browser)
        self._page.setBackgroundColor(QColor(0, 0, 0))
        self.browser.setUrl(QUrl(url))
        self.setFocusProxy(self.browser)

        self._bridge = WindowBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject('windowBridge', self._bridge)
        self._page.setWebChannel(self._channel)
        self._page.lifecycleStateChanged.connect(self._on_state_changed)

    def _on_state_changed(self, state):
        if state == QWebEnginePage.LifecycleState.Active:
            self.browser.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.browser.setFocus()

    def _force_update(self):
        self.browser.update()
        QApplication.processEvents()

@app.context_processor
def inject_ui_sounds():
    conf = get_settings("settings")
    return dict(
        vgamepad_available=VGAMEPAD_AVAILABLE,
        ui_sounds={
            "switch_hover": conf.get("switch_hover", True),
            "switch_click": conf.get("switch_click", True),
            "volume_hover": conf.get("volume_hover", 35),
            "volume_click": conf.get("volume_click", 45),
            "background": conf.get("background", "bot")
        }
    )

def on_press(key):
    try:
        if hotkey_manager.suspended:
            return
        k = str(key).replace('Key.', '').replace("'", '').lower()
        if k in hotkey_manager.actions:
            hotkey_manager.actions[k]()
        else:
            print(f"Неизвестная клавиша: {k}")
    except Exception as e:
        print(f"Ошибка хоткея: {e}")

def start_flask():
    app.run(port=5000, use_reloader=False, threaded=True, debug=False)

def wait_for_port(port, timeout=5.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                return True
        except:
            time.sleep(0.02)
    return False

def get_center_position(width, height):
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    return x, y

if __name__ == '__main__':
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()

    threading.Thread(target=start_flask, daemon=True).start()

    online_thread = threading.Thread(target=fetch_online_once, daemon=True)
    update_thread = threading.Thread(target=check_update_once, daemon=True)
    online_thread.start()
    update_thread.start()
    online_thread.join(timeout=10)
    update_thread.join(timeout=10)

    if wait_for_port(5000):
        win_width, win_height = 850, 900
        x, y = get_center_position(win_width, win_height)

        qt_app = QApplication(sys.argv)
        window = MainWindow(url='http://127.0.0.1:5000/index',width=win_width,height=win_height,x=x,y=y)
        window.show()
        qt_app.exec()

    listener.stop()