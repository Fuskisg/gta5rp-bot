import threading
import time
import cv2
import numpy as np
import mss
import os
import keyboard
import win32gui
import win32con
import pyautogui
from flask import render_template, jsonify, Blueprint, request
from core.common import (state, add_log, press, get_settings, update_settings, init_module, AutoEToggle, AutoHold, hotkey_manager)
import random

cow_bp = Blueprint('cow', __name__)
stop_event = threading.Event()
auto_e = AutoEToggle(page="cow")
walker = AutoHold(keys=["shift", "w"], page="cow")
last_registered_walker_hotkey = None

init_module("cow")

try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(max(1, os.cpu_count() - 1))
except Exception:
    pass

MIN_RADIUS = 30
MAX_RADIUS = 150
FILL_THRESHOLD = 0.9
SCALE = 0.5
WINDOW_TITLE = "multi"

DANGER_COLOR = np.array([0x55, 0x69, 0xff])
DANGER_COLOR_RANGE = 20
DANGER_MIN_WIDTH = 10
DANGER_MIN_HEIGHT = 40
DANGER_PAUSE_SECONDS = 5

hwnd = None
window_rect = {"left": 0, "top": 0, "width": 0, "height": 0}
last_key_time = 0

class WindowFinder:
    _last_check = 0
    _last_result = None
    _was_missing = True
    _REPLACEMENTS = {
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
        "у": "y", "х": "x", "м": "m", "т": "t", "н": "h",
        "в": "b", "к": "k",
    }
    _CHECK_INTERVAL = 0.5

    @staticmethod
    def _normalize_title(title: str) -> str:
        title = title.casefold()
        return "".join(WindowFinder._REPLACEMENTS.get(c, c) for c in title)

    @staticmethod
    def find() -> bool:
        global hwnd, window_rect
        current_time = time.time()
        
        if current_time - WindowFinder._last_check < WindowFinder._CHECK_INTERVAL:
            if WindowFinder._last_result is False and not WindowFinder._was_missing:
                return False
            if WindowFinder._last_result is not None:
                hwnd = WindowFinder._last_result
                update_window_rect()
                return True
        
        WindowFinder._last_check = current_time
        
        def enum_callback(hwnd_found, extra):
            if win32gui.IsWindowVisible(hwnd_found):
                title = win32gui.GetWindowText(hwnd_found)
                normalized = WindowFinder._normalize_title(title)
                window_normalized = WindowFinder._normalize_title(WINDOW_TITLE)
                if window_normalized in normalized:
                    found_windows.append((hwnd_found, title))
        
        found_windows = []
        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            add_log(f"Error enumerating windows: {e}", level="WARNING", page="cow")
            WindowFinder._last_result = None
            WindowFinder._was_missing = True
            return False
        
        if not found_windows:
            if WindowFinder._was_missing is False:
                add_log(f"Window '{WINDOW_TITLE}' lost", level="WARNING", page="cow")
            WindowFinder._was_missing = True
            WindowFinder._last_result = None
            return False
        
        hwnd, title = found_windows[0]
        WindowFinder._last_result = hwnd
        WindowFinder._was_missing = False
        
        if not WindowFinder._was_missing:
            add_log(f"Found window: '{title}'", page="cow")
        
        update_window_rect()
        return True

def auto_detect_region(width_ratio=None, height_ratio=None, top_ratio=None, reference_height=None, reference_top=None):
    base_width = window_rect["width"]
    base_height = window_rect["height"]

    if width_ratio is None: width_ratio = 1.0
    if height_ratio is None: height_ratio = 0.5
    if top_ratio is None: top_ratio = 0.5

    if reference_height is not None and reference_top is not None:
        top_ratio = reference_top / reference_height

    region_width = int(base_width * width_ratio)
    region_height = int(base_height * height_ratio)

    region = {
        "left": window_rect["left"] + int((base_width - region_width) / 2),
        "top": window_rect["top"] + int(base_height * top_ratio),
        "width": region_width,
        "height": region_height,
    }
    return region

def update_window_rect():
    global hwnd, window_rect
    if not hwnd: 
        return False
    
    try:
        rect = win32gui.GetClientRect(hwnd)
        left, top = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
        right, bottom = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
        window_rect = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        return True
    except Exception as e:
        error_code = getattr(e, 'winerror', None) or getattr(e, 'args', [None])[0]
        if error_code == 1400 or 'GetClientRect' in str(e):
            add_log(f"Окно потеряно (ошибка {error_code}), начинаю поиск...", level="WARNING", page="cow")
            hwnd = None
            WindowFinder._last_result = None
            WindowFinder._was_missing = True
        else:
            add_log(f"Error updating rect: {e}", level="WARNING", page="cow")
        return False

def capture_region():
    global sct
    update_window_rect()
    
    if window_rect["width"] <= 0 or window_rect["height"] <= 0:
        return None

    original_h = window_rect["height"]
    capture_top = window_rect["top"] + (original_h // 2)
    capture_height = original_h // 2
    
    monitor = {
        "left": window_rect["left"],
        "top": capture_top,
        "width": window_rect["width"],
        "height": capture_height
    }
    
    return np.array(sct.grab(monitor))


def check_danger_color(img):
    if img is None or img.size == 0:
        return False
    
    if img.shape[2] == 4:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    else:
        img_bgr = img
    
    h, w = img_bgr.shape[:2]
    lower_bound = np.clip(DANGER_COLOR - DANGER_COLOR_RANGE, 0, 255)
    upper_bound = np.clip(DANGER_COLOR + DANGER_COLOR_RANGE, 0, 255)
    
    mask = cv2.inRange(img_bgr, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw >= DANGER_MIN_WIDTH and ch >= DANGER_MIN_HEIGHT:
            if ch > cw:
                return True
    
    return False

def find_circles(img):
    if img is None or img.size == 0: return []
    h, w = img.shape[:2]
    
    if SCALE != 1.0:
        new_w, new_h = int(w * SCALE), int(h * SCALE)
        small = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        small = img

    gray = cv2.cvtColor(small, cv2.COLOR_BGRA2GRAY)
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8,8))
    contrast_gray = clahe.apply(gray)
    _, binary = cv2.threshold(contrast_gray, 245, 255, cv2.THRESH_BINARY)
    
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid = []
    scale_back = 1.0 / SCALE
    
    for cnt in contours:
        if len(cnt) < 5: continue
        (x, y), r = cv2.minEnclosingCircle(cnt)
        r = r * scale_back
        if r < MIN_RADIUS or r > MAX_RADIUS: continue
        
        area = cv2.contourArea(cnt) * (scale_back ** 2)
        circle_area = 3.14159 * r * r
        if circle_area == 0: continue
        
        if (area / circle_area) < 0.4: continue 
        
        x_i, y_i, r_i = int(x * scale_back), int(y * scale_back), int(r)
        
        white_count = 0
        total = 0
        for dy in [-0.5, 0, 0.5]:
            for dx in [-0.5, 0, 0.5]:
                px, py = int(x_i + dx * r_i), int(y_i + dy * r_i)
                if 0 <= px < w and 0 <= py < h:
                    if img[py, px, 0] > 240:
                        white_count += 1
                    total += 1
        
        fill = white_count / total if total > 0 else 0
        if fill > FILL_THRESHOLD:
            valid.append([x_i, y_i, r_i, fill])
            
    return valid

def press_key(side):
    if side == "left":
        press('a')
        add_log("◀ Нажата 'a'", page="cow")
    else:
        press('d')
        add_log("▶ Нажата 'd'", page="cow")
    return True

def cow_worker(pause_delay: float):
    global sct
    add_log(">>> Модуль Коровы запущен", page="cow")
    data = state["modules"]["cow"]

    try:
        if not WindowFinder.find():
            return
        
        sct = mss.mss()
        add_log(f"Область поиска инициализирована", page="cow")
    except Exception as e:
        add_log(f"Ошибка инициализации: {e}", level="WARNING", page="cow")
        data["active"] = False
        return

    window_search_delay = 2.0
    last_window_search = 0

    try:
        while data["active"] and not stop_event.is_set():
            try:
                if hwnd is None:
                    current_time = time.time()
                    if current_time - last_window_search >= window_search_delay:
                        add_log("Поиск окна...", page="cow")
                        if WindowFinder.find():
                            add_log("Окно найдено, возобновляю работу", page="cow")
                        last_window_search = current_time
                    
                    stop_event.wait(0.1)
                    continue
                
                img = capture_region()
                if img is None:
                    time.sleep(0.1)
                    continue
                
                if check_danger_color(img):
                    add_log(f"Обнаружен опасный цвет!", level="WARNING", page="cow")
                    stop_event.wait(random.uniform(0.005, 0.015))
                    continue
                
                img_middle_x = img.shape[1] // 2
                circles = find_circles(img)
                if circles:
                    best = max(circles, key=lambda x: x[3])
                    x, y, r, fill = best
                    side = "left" if x < img_middle_x else "right"
                    add_log(f"Circle: x={x:4d} | side={side.upper()} | fill={fill:.0%}", page="cow")
                    press_key(side)
                else:
                    if auto_e.enabled:
                        press('e')
                
                if stop_event.wait(pause_delay):
                    break
                    
            except Exception as e:
                add_log(f"Loop Error: {e}", level="WARNING", page="cow")
                time.sleep(0.1)

    except Exception as exc:
        add_log(f"[Ошибка потока] {str(exc)}", level="ERROR", page="cow")
    finally:
        if sct:
            sct.close()
        walker.force_disable()
        add_log("<<< Модуль Коровы остановлен", page="cow")
        data["active"] = False

@cow_bp.route('/cow')
def cow_page():
    settings = state["modules"]["cow"]["settings"]
    active = state["modules"]["cow"]["active"]
    return render_template('cow.html', settings=settings, active=active)

@cow_bp.route('/api/cow/toggle', methods=['POST'])
def toggle_cow():
    global last_registered_walker_hotkey
    req_data = request.get_json()
    auto_e_hotkey = req_data.get('auto_e_hotkey', 'f5').lower()
    walker_hotkey = req_data.get('walker_hotkey', 'f6').lower().strip()
    pause = float(req_data.get('pause', 0.07))

    data = state["modules"]["cow"]

    update_settings("cow", {
        "auto_e_hotkey": auto_e_hotkey,
        "walker_hotkey": walker_hotkey,
        "pause": pause
    })
    data["settings"] = get_settings("cow")

    if not data["active"]:
        stop_event.clear()
        data["active"] = True

        auto_e.register_hotkey(auto_e_hotkey)

        if last_registered_walker_hotkey:
            hotkey_manager.unregister(last_registered_walker_hotkey)
        hotkey_manager.register(walker_hotkey, walker.toggle)
        last_registered_walker_hotkey = walker_hotkey
        add_log(f"[🐄] Хоткей автобега установлен: {walker_hotkey}", page="cow")

        t = threading.Thread(target=cow_worker, args=(pause,), daemon=True)
        t.start()
    else:
        data["active"] = False
        stop_event.set()
        auto_e.unregister_hotkey()
        if last_registered_walker_hotkey:
            hotkey_manager.unregister(last_registered_walker_hotkey)
            last_registered_walker_hotkey = None
        add_log("выключен", page="cow")

    return jsonify({"active": data["active"]})


@cow_bp.route('/api/cow/walker', methods=['POST'])
def api_cow_walker():
    walker.toggle()
    return jsonify({"status": "ok", "walker_active": walker.enabled})


def register_hotkeys(hm):
    hotkey = state["modules"]["cow"]["settings"].get("hotkey", "f4")
    hm.register(hotkey, lambda: toggle_cow())

