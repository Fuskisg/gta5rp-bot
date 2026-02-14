import threading
import time
import cv2
import numpy as np
import mss
from flask import render_template, jsonify, Blueprint, request
from core.common import (state, add_log, press, auto_detect_region,hotkey_manager, get_settings, update_settings)

gym_bp = Blueprint('gym', __name__)
stop_event = threading.Event()
last_registered_hotkey = None

state["modules"]["gym"] = {
    "active": False,
    "settings": get_settings("gym"),
    "counter": 0
}

TARGET_RGB = (120, 255, 166)
H_TOL = 10
S_TOL = 15
V_TOL = 20
MIN_AREA = 50

def rgb_to_hsv_bounds(rgb, h_tol, s_tol, v_tol):
    bgr = np.uint8([[[rgb[2], rgb[1], rgb[0]]]])
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    
    lower = np.array([max(0, h - h_tol), max(0, s - s_tol), max(0, v - v_tol)], dtype=np.uint8)
    upper = np.array([min(179, h + h_tol), min(255, s + s_tol), min(255, v + v_tol)], dtype=np.uint8)
    return lower, upper

def found_circle_by_color(frame_bgr, lower, upper):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue

        perim = cv2.arcLength(cnt, True)
        if perim == 0:
            continue

        return True
    return False

auto_e_enabled = False

def toggle_auto_e():
    global auto_e_enabled
    auto_e_enabled = not auto_e_enabled
    status = "включено" if auto_e_enabled else "выключено"
    add_log(f"[⌨️] Автонажатие E {status}", page="gym")

def gym_worker(pause_delay: float, key_food: str, auto_e_pause: float = 5.0):
    global auto_e_enabled
    add_log(">>> Модуль Качалка запущен", page="gym")
    data = state["modules"]["gym"]
    data["counter"] = 0
    
    try:
        monitor = auto_detect_region(reference_height=1440, reference_top=560)
        add_log(f"Область поиска: {monitor}", page="gym")
    except Exception as e:
        add_log(f"Ошибка определения региона: {e}", level="WARNING", page="gym")
        monitor = None
    
    lower, upper = rgb_to_hsv_bounds(TARGET_RGB, H_TOL, S_TOL, V_TOL)
    was_found = False
    last_e_time = time.time()
    last_k_time = time.time()
    
    try:
        with mss.mss() as sct:
            while data["active"] and not stop_event.is_set():
                if monitor:
                    img = np.array(sct.grab(monitor))
                    frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    found = found_circle_by_color(frame_bgr, lower, upper)
                else:
                    found = False
                
                if found and not was_found:
                    press('space')
                    add_log("✓ Круг найден, нажат пробел", page="gym")
                    data["counter"] += 1
                    last_e_time = time.time()
                
                if not found:
                    now = time.time()
                    
                    if now - last_k_time >= pause_delay:
                        press(key_food)
                        last_k_time = now
                        add_log(f"🍔 Нажата '{key_food}' (еда)", page="gym")
                    
                    if auto_e_enabled:
                        if now - last_e_time >= auto_e_pause:
                            press('e')
                            last_e_time = now
                            add_log("⚙️ Нажата 'E' (авто)", page="gym")
                
                was_found = found
                    
    except Exception as e:
        add_log(f"Критическая ошибка качалки: {e}", level="ERROR", page="gym")
    finally:
        auto_e_enabled = False
        data["active"] = False
        add_log(">>> Модуль Качалка остановлен", page="gym")

def toggle_gym():
    global last_registered_hotkey, auto_e_enabled
    data = state["modules"]["gym"]
    
    if not data["active"]:
        data["active"] = True
        auto_e_enabled = False
        stop_event.clear()
        
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        
        hotkey = data["settings"].get("auto_e_hotkey", "f5")
        hotkey_manager.register(hotkey, toggle_auto_e)
        last_registered_hotkey = hotkey
        
        pause_delay = data["settings"].get("food_pause", 1800)
        key_food = data["settings"].get("food_key", "k")
        auto_e_pause = data["settings"].get("auto_e_pause", 5.0)
        
        threading.Thread(target=gym_worker, args=(pause_delay, key_food, auto_e_pause), daemon=True).start()
    else:
        data["active"] = False
        auto_e_enabled = False
        stop_event.set()
        
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
            last_registered_hotkey = None

@gym_bp.route('/gym')
def render_gym():
    settings = state["modules"]["gym"]["settings"]
    return render_template(
        'gym.html',
        active=state["modules"]["gym"]["active"],
        settings=settings,
        counter=state["modules"]["gym"]["counter"]
    )

@gym_bp.route('/api/gym/toggle', methods=['POST'])
def api_toggle_gym():
    data = request.get_json() or {}
    
    settings = state["modules"]["gym"]["settings"]
    settings["auto_e_hotkey"] = data.get('auto_e_hotkey', 'f5')
    settings["food_key"] = data.get('food_key', 'k')
    settings["food_pause"] = int(data.get('food_pause', 1800))
    settings["auto_e_pause"] = float(data.get('auto_e_pause', 5.0))
    update_settings("gym", settings)
    
    toggle_gym()
    return jsonify({
        'active': state["modules"]["gym"]["active"],
        'counter': state["modules"]["gym"]["counter"]
    })

@gym_bp.route('/api/gym/counter', methods=['GET'])
def api_gym_counter():
    return jsonify({'counter': state["modules"]["gym"]["counter"]})
