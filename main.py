import threading
from flask import Flask
from pynput import keyboard
from core.common import hotkey_manager, get_settings
import webview 
import socket
import time
from core.api import fetch_online_once, check_update_once
from pages import pages_bp
from pages.antiafk import VGAMEPAD_AVAILABLE
import ctypes

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = False
app.config['ENV'] = 'production'
app.register_blueprint(pages_bp)
window = None

class WindowAPI:
    def minimize(self):
        global window
        if window:
            window.minimize()
    
    def close(self):
        global window
        if window:
            window.destroy()
    
    def move(self, x, y):
        global window
        if window:
            window.move(int(x), int(y))
    
    def get_position(self):
        global window
        if window:
            try:
                return {'x': window.x, 'y': window.y}
            except:
                pass
        return {'x': 0, 'y': 0}

window_api = WindowAPI()

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

flask_ready = False

def on_press(key):
    try:
        k = str(key).replace('Key.', '').lower()
        if k in hotkey_manager.actions:
            hotkey_manager.actions[k]()
        else:
            print(f"Неизвестная клавиша: {k}")
    except Exception as e:
        print(f"Ошибка хоткея: {e}")

def start_flask():
    global flask_ready
    app.run(port=5000, use_reloader=False, threaded=True, debug=False)
    flask_ready = True

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
    threading.Thread(target=fetch_online_once, daemon=True).start()
    threading.Thread(target=check_update_once, daemon=True).start()
    if wait_for_port(5000):
        win_width, win_height = 850, 900
        x, y = get_center_position(win_width, win_height)
        window = webview.create_window('Steam Client WebHelper', 'http://127.0.0.1:5000/index', width=win_width, height=win_height, x=x, y=y, frameless=True, easy_drag=False, js_api=window_api, background_color='#000000')
        webview.start(debug=False)
    
    listener.stop()