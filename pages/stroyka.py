import threading
import time
import os
from flask import render_template, jsonify, Blueprint, request
from core.common import (
    state, add_log, press,
    CommonLogger, AutoHold, hotkey_manager,
    get_settings, update_settings
)

stroyka_bp = Blueprint('stroyka', __name__)
stop_event = threading.Event()
walker = AutoHold(keys=["shift", "w"], page="stroyka")
last_registered_hotkey = None
toggle_requested = False

state["modules"]["stroyka"] = {
    "active": False,
    "settings": get_settings("stroyka"),
    "counter": 0
}

ASSETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'assets', 'stroyka')
IMG_KEY_MAPPING = {
    "image1.png": {"en": "e"},
    "image2.png": {"en": "y"},
    "image3.png": {"en": "f"},
    "image4.png": {"en": "h"},
}

def safe_locate(path: str, detection_cache: dict, ttl: float = 0.1):
    now = time.time()
    cached = detection_cache.get(path)
    if cached:
        result, ts = cached
        if now - ts < ttl:
            return result
    
    result = CommonLogger.safe_locate(path, 0.90)
    
    if result is not None:
        detection_cache[path] = (result, now)
    
    return result

def handle_visible_image(path: str, keys: dict, visible_state: dict, data: dict):
    if not visible_state[path]:
        visible_state[path] = True
        data["counter"] += 1
        add_log(f"[✓] Найдено → спам '{keys['en']}'", page="stroyka")
    
    press_count = 0
    while data["active"] and press_count < 60:
        press(keys['en'])
        press_count += 1
        if press_count % 5 == 0:
            stop_event.wait(0.001)
    
    if not CommonLogger.safe_locate(path, 0.90):
        visible_state[path] = False

def stroyka_worker():
    global toggle_requested
    
    add_log("Поиск начат.", page="stroyka")
    data = state["modules"]["stroyka"]
    data["counter"] = 0
    
    img_key = {}
    for img_name, keys in IMG_KEY_MAPPING.items():
        img_path = os.path.join(ASSETS_PATH, img_name)
        img_key[img_path] = keys
    
    visible_state = {path: False for path in img_key}
    detection_cache = {}
    
    try:
        while data["active"]:
            if not CommonLogger.wait_for_rage(page="stroyka", auto_move=walker, stop_event=stop_event):
                continue
            
            for path, keys in img_key.items():
                if safe_locate(path, detection_cache):
                    handle_visible_image(path, keys, visible_state, data)
                    break
            
            stop_event.wait(0.01)
    
    except Exception as e:
        add_log(f"[Критическая ошибка]\n{str(e)}", level="ERROR", page="stroyka")
    finally:
        walker.force_disable()
        data["active"] = False
        add_log(">>> Модуль Стройка остановлен", page="stroyka")

def toggle_stroyka():
    global last_registered_hotkey
    data = state["modules"]["stroyka"]
    
    if not data["active"]:
        data["active"] = True
        data["counter"] = 0
        stop_event.clear()
        
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
        
        hotkey = data["settings"].get("walker_hotkey", "f5")
        hotkey_manager.register(hotkey, walker.toggle)
        last_registered_hotkey = hotkey
        
        threading.Thread(target=stroyka_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()
        
        if last_registered_hotkey:
            hotkey_manager.unregister(last_registered_hotkey)
            last_registered_hotkey = None

@stroyka_bp.route('/stroyka')
def render_stroyka():
    settings = state["modules"]["stroyka"]["settings"]
    return render_template(
        'stroyka.html',
        active=state["modules"]["stroyka"]["active"],
        settings=settings,
        counter=state["modules"]["stroyka"]["counter"]
    )

@stroyka_bp.route('/api/stroyka/toggle', methods=['POST'])
def api_toggle_stroyka():
    data = request.get_json() or {}
    
    settings = state["modules"]["stroyka"]["settings"]
    settings["walker_hotkey"] = data.get('walker_hotkey', 'f5')
    update_settings("stroyka", settings)
    
    toggle_stroyka()
    return jsonify({
        'active': state["modules"]["stroyka"]["active"],
        'counter': state["modules"]["stroyka"]["counter"]
    })

@stroyka_bp.route('/api/stroyka/counter', methods=['GET'])
def api_stroyka_counter():
    return jsonify({'counter': state["modules"]["stroyka"]["counter"]})
