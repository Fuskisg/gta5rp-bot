import threading
import time
import os
import ctypes
import pyautogui
from flask import render_template, jsonify, Blueprint, request
from core.common import state, add_log, hotkey_manager, get_settings, update_settings, auto_detect_region

taxi_bp = Blueprint('taxi', __name__)
stop_event = threading.Event()
last_registered_hotkey = None

TARGET_COLOR = (48, 67, 104)
TOLERANCE = 10
CHECK_RADIUS = 20
POLL_DELAY = 0.01

_saved = get_settings("taxi")
if _saved:
    state["modules"]["taxi"]["settings"] = _saved

if "sound_type" not in state["modules"]["taxi"]["settings"]:
    state["modules"]["taxi"]["settings"]["sound_type"] = "normal"

if "volume" not in state["modules"]["taxi"]["settings"]:
    state["modules"]["taxi"]["settings"]["volume"] = 100

def play_notification(sound_type=None, volume=None):
    try:
        import winsound
        if sound_type is None:
            sound_type = state["modules"]["taxi"]["settings"].get("sound_type", "normal")
        if volume is None:
            volume = state["modules"]["taxi"]["settings"].get("volume", 100)
        
        if sound_type == "yandex":
            wav_name = "taxi_yandex.wav"
        else:
            wav_name = "taxi.wav"
        
        wav_path = os.path.join(os.path.dirname(__file__), '..', "static", "wav", wav_name)
        if not os.path.exists(wav_path):
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return
        
        vol = max(0, min(100, int(volume)))
        if vol <= 0:
            return
        
        level = int(0xFFFF * vol / 100)
        ctypes.windll.winmm.waveOutSetVolume(0, level | (level << 16))
        winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass

def is_color_match(c1, c2, tol):
    return all(abs(c1[i] - c2[i]) < tol for i in range(3))

def check_area(img, start_x, start_y):
    width, height = img.size
    for x in range(start_x, min(start_x + CHECK_RADIUS, width)):
        for y in range(start_y, min(start_y + CHECK_RADIUS, height)):
            if not is_color_match(img.getpixel((x, y)), TARGET_COLOR, TOLERANCE):
                return False
    return True

def scan(region):
    reg_left, reg_top = region[0], region[1]
    screenshot = pyautogui.screenshot(region=region)
    rgb_img = screenshot.convert('RGB')
    w, h = rgb_img.size

    for x in range(0, w - CHECK_RADIUS, 3):
        if stop_event.is_set():
            return False
        for y in range(0, h - CHECK_RADIUS, 3):
            pixel = rgb_img.getpixel((x, y))
            if is_color_match(pixel, TARGET_COLOR, TOLERANCE):
                if check_area(rgb_img, x, y):
                    target_x = reg_left + x + (CHECK_RADIUS // 2)
                    target_y = reg_top + y + (CHECK_RADIUS // 2)
                    pyautogui.click(target_x, target_y)
                    add_log(f"Вызов взят! ({target_x}, {target_y})", page="taxi")
                    play_notification()
                    return True
    return False

def taxi_worker():
    add_log(">>> Такси запущен", page="taxi")
    data = state["modules"]["taxi"]
    try:
        monitor = auto_detect_region()
        region = tuple(monitor.values())
        while data["active"] and not stop_event.is_set():
            scan(region)
            if stop_event.wait(POLL_DELAY):
                break
    except Exception as e:
        add_log(f"Ошибка: {e}", level="ERROR", page="taxi")
    finally:
        data["active"] = False
        add_log(">>> Такси остановлен", page="taxi")

def toggle_taxi():
    global last_registered_hotkey
    data = state["modules"]["taxi"]
    if not data["active"]:
        data["active"] = True
        stop_event.clear()
        threading.Thread(target=taxi_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()

@taxi_bp.route('/taxi')
def render_taxi():
    return render_template(
        'taxi.html',
        active=state["modules"]["taxi"]["active"],
        settings=state["modules"]["taxi"]["settings"],
        logs=state["page_logs"].get("taxi", [])
    )

@taxi_bp.route('/api/taxi/toggle', methods=['POST'])
def api_toggle():
    global last_registered_hotkey
    data = request.get_json() or {}
    hotkey = data.get('hotkey', '').lower().strip()

    if hotkey:
        state["modules"]["taxi"]["settings"]["hotkey_taxi"] = hotkey
        update_settings("taxi", state["modules"]["taxi"]["settings"], page="taxi")
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        hotkey_manager.register(hotkey, toggle_taxi)
        last_registered_hotkey = hotkey

    toggle_taxi()
    return jsonify({"status": "ok", "active": state["modules"]["taxi"]["active"]})

@taxi_bp.route('/api/taxi/sound', methods=['POST'])
def api_update_sound():
    data = request.get_json() or {}
    sound_type = data.get('sound_type', 'normal')
    state["modules"]["taxi"]["settings"]["sound_type"] = sound_type
    update_settings("taxi", state["modules"]["taxi"]["settings"], page="taxi")
    return jsonify({"status": "ok", "sound_type": sound_type})

@taxi_bp.route('/api/taxi/test_sound', methods=['POST'])
def api_test_sound():
    data = request.get_json() or {}
    sound_type = data.get('sound_type', state["modules"]["taxi"]["settings"].get("sound_type", "normal"))
    volume = data.get('volume', state["modules"]["taxi"]["settings"].get("volume", 100))
    play_notification(sound_type, volume)
    return jsonify({"status": "ok"})

@taxi_bp.route('/api/taxi/volume', methods=['POST'])
def api_update_volume():
    data = request.get_json() or {}
    volume = int(data.get('volume', 100))
    volume = max(0, min(100, volume))
    state["modules"]["taxi"]["settings"]["volume"] = volume
    update_settings("taxi", state["modules"]["taxi"]["settings"], page="taxi")
    return jsonify({"status": "ok", "volume": volume})

def register_hotkeys(hm):
    hotkey = state["modules"]["taxi"]["settings"].get("hotkey_taxi", "f5")
    hm.register(hotkey, toggle_taxi)