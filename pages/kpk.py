import threading
import time
import os
import ctypes
import pyautogui
from flask import render_template, jsonify, Blueprint, request
from core.common import state, add_log, hotkey_manager, get_settings, update_settings, auto_detect_region

kpk_bp = Blueprint('kpk', __name__)
stop_event = threading.Event()
last_registered_hotkey = None

TARGET_COLOR = (48, 67, 104)
TOLERANCE = 10
CHECK_RADIUS = 20
POLL_DELAY = 0.01

_saved = get_settings("kpk")
if _saved:
    state["modules"]["kpk"]["settings"] = _saved

if "sound_type" not in state["modules"]["kpk"]["settings"]:
    state["modules"]["kpk"]["settings"]["sound_type"] = "normal"

if "volume" not in state["modules"]["kpk"]["settings"]:
    state["modules"]["kpk"]["settings"]["volume"] = 100

def play_notification(sound_type=None, volume=None):
    try:
        import winsound
        if sound_type is None:
            sound_type = state["modules"]["kpk"]["settings"].get("sound_type", "normal")
        if volume is None:
            volume = state["modules"]["kpk"]["settings"].get("volume", 100)
        
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
                    add_log(f"Вызов взят! ({target_x}, {target_y})", page="kpk")
                    play_notification()
                    return True
    return False

def kpk_worker():
    add_log(">>> КПК запущен", page="kpk")
    data = state["modules"]["kpk"]
    try:
        monitor = auto_detect_region()
        region = tuple(monitor.values())
        while data["active"] and not stop_event.is_set():
            scan(region)
            if stop_event.wait(POLL_DELAY):
                break
    except Exception as e:
        add_log(f"Ошибка: {e}", level="ERROR", page="kpk")
    finally:
        data["active"] = False
        add_log(">>> КПК остановлен", page="kpk")

def toggle_kpk():
    global last_registered_hotkey
    data = state["modules"]["kpk"]
    if not data["active"]:
        data["active"] = True
        stop_event.clear()
        threading.Thread(target=kpk_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()

@kpk_bp.route('/kpk')
def render_kpk():
    return render_template(
        'kpk.html',
        active=state["modules"]["kpk"]["active"],
        settings=state["modules"]["kpk"]["settings"],
        logs=state["page_logs"].get("kpk", [])
    )

@kpk_bp.route('/api/kpk/toggle', methods=['POST'])
def api_toggle():
    global last_registered_hotkey
    data = request.get_json() or {}
    hotkey = data.get('hotkey', '').lower().strip()

    if hotkey:
        state["modules"]["kpk"]["settings"]["hotkey_kpk"] = hotkey
        update_settings("kpk", state["modules"]["kpk"]["settings"], page="kpk")
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        hotkey_manager.register(hotkey, toggle_kpk)
        last_registered_hotkey = hotkey

    toggle_kpk()
    return jsonify({"status": "ok", "active": state["modules"]["kpk"]["active"]})

@kpk_bp.route('/api/kpk/sound', methods=['POST'])
def api_update_sound():
    data = request.get_json() or {}
    sound_type = data.get('sound_type', 'normal')
    state["modules"]["kpk"]["settings"]["sound_type"] = sound_type
    update_settings("kpk", state["modules"]["kpk"]["settings"], page="kpk")
    return jsonify({"status": "ok", "sound_type": sound_type})

@kpk_bp.route('/api/kpk/test_sound', methods=['POST'])
def api_test_sound():
    data = request.get_json() or {}
    sound_type = data.get('sound_type', state["modules"]["kpk"]["settings"].get("sound_type", "normal"))
    volume = data.get('volume', state["modules"]["kpk"]["settings"].get("volume", 100))
    play_notification(sound_type, volume)
    return jsonify({"status": "ok"})

@kpk_bp.route('/api/kpk/volume', methods=['POST'])
def api_update_volume():
    data = request.get_json() or {}
    volume = int(data.get('volume', 100))
    volume = max(0, min(100, volume))
    state["modules"]["kpk"]["settings"]["volume"] = volume
    update_settings("kpk", state["modules"]["kpk"]["settings"], page="kpk")
    return jsonify({"status": "ok", "volume": volume})

def register_hotkeys(hm):
    hotkey = state["modules"]["kpk"]["settings"].get("hotkey_kpk", "f5")
    hm.register(hotkey, toggle_kpk)