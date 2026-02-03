import threading
import pyautogui
import time
from flask import render_template, jsonify, Blueprint, request
from core.common import (
    state, add_log, press, auto_detect_region, 
    CommonLogger, AutoHold, hotkey_manager, 
    get_settings, update_settings
)

port_bp = Blueprint('port', __name__)
stop_event = threading.Event()
walker = AutoHold(keys=["shift", "w"], page="port")
last_registered_hotkey = None

state["modules"]["port"]["settings"] = get_settings("port")

GREEN = (126, 211, 33)
RED = (231, 33, 57)
TOLERANCE = 20
STEP_X = 4
STEP_Y = 10

def is_color_close(c1, c2, tol):
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def port_worker():
    add_log(">>> Модуль Порт запущен", page="port")
    data = state["modules"]["port"]
    count = 0
    
    try:
        monitor = auto_detect_region()
    except Exception as e:
        add_log(f"Ошибка определения региона: {e}", level="WARNING", page="port")
        monitor = None

    try:
        while data["active"] and not stop_event.is_set():
            if not CommonLogger.wait_for_rage(page="port", auto_move=walker, stop_event=stop_event):
                if stop_event.wait(1.0): break
                continue

            region = tuple(monitor.values()) if monitor else None
            screenshot = pyautogui.screenshot(region=region)
            pixels = screenshot.load()
            width, height = screenshot.size
            found = False

            for y in range(0, height, STEP_Y):
                for x in range(0, width, STEP_X):
                    if is_color_close(pixels[x, y], RED, TOLERANCE):
                        for dx in range(-10, 11):
                            nx = x + dx
                            if 0 <= nx < width and is_color_close(pixels[nx, y], GREEN, TOLERANCE):
                                found = True
                                break
                    if found: break
                if found: break

            if found:
                count += 1
                add_log(f"Найдена мини-игра! Нажимаем E (#{count})", page="port")
                press('e')
                if stop_event.wait(0.5): break

            if stop_event.wait(0.05): break
                
    except Exception as e:
        add_log(f"Критическая ошибка порта: {e}", level="ERROR", page="port")
    finally:
        walker.force_disable()
        data["active"] = False
        add_log(">>> Модуль Порт остановлен", page="port")

def toggle_port():
    global last_registered_hotkey
    data = state["modules"]["port"]
    if not data["active"]:
        data["active"] = True
        stop_event.clear()
        
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        
        hotkey = data["settings"].get("walker_hotkey", "f5")
        hotkey_manager.register(hotkey, walker.toggle)
        last_registered_hotkey = hotkey
        threading.Thread(target=port_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        last_registered_hotkey = None

@port_bp.route('/port')
def render_port():
    return render_template('port.html', active=state["modules"]["port"]["active"],settings=state["modules"]["port"]["settings"])

@port_bp.route('/api/port/toggle', methods=['POST'])
def api_toggle():
    data = request.json or {}
    hotkey = data.get('hotkey', 'f5').lower().strip()
    state["modules"]["port"]["settings"]["walker_hotkey"] = hotkey
    update_settings("port", state["modules"]["port"]["settings"], page="port")
    
    if not state["modules"]["port"]["active"]:
        add_log(f"[⚓] Хоткей автобега установлен: {hotkey}", page="port")
    
    toggle_port()
    return jsonify({"status": "ok", "active": state["modules"]["port"]["active"], "hotkey": hotkey})

@port_bp.route('/api/port/walker', methods=['POST'])
def api_walker():
    walker.toggle()
    return jsonify({"status": "ok", "walker_active": walker.enabled})

def register_hotkeys(hm):
    hotkey = state["modules"]["port"]["settings"].get("hotkey", "f5")
    hm.register(hotkey, toggle_port)
    hm.register("f6", walker.toggle)