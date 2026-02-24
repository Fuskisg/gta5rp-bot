import os
from flask import render_template, jsonify, Blueprint, request
from core.common import (state, add_log, press,CommonLogger,update_settings, DetectionCache,init_module, WalkerModule)

stroyka_bp = Blueprint('stroyka', __name__)
module = WalkerModule("stroyka")
init_module("stroyka", extra_fields={"counter": 0})

ASSETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'assets', 'stroyka')
IMG_KEY_MAPPING = {
    "image1.png": {"en": "e"},
    "image2.png": {"en": "y"},
    "image3.png": {"en": "f"},
    "image4.png": {"en": "h"},
}

def handle_visible_image(path: str, keys: dict, visible_state: dict, data: dict, detection_cache: DetectionCache):
    if not visible_state[path]:
        visible_state[path] = True
        data["counter"] += 1
        add_log(f"[✓] Найдено → спам '{keys['en']}'", page="stroyka")

    press_count = 0
    while data["active"] and press_count < 60:
        press(keys['en'])
        press_count += 1
        if press_count % 5 == 0:
            module.stop_event.wait(0.001)

    if not detection_cache.get(path):
        visible_state[path] = False

def stroyka_worker():
    add_log("Поиск начат.", page="stroyka")
    data = state["modules"]["stroyka"]
    data["counter"] = 0

    img_key = {}
    for img_name, keys in IMG_KEY_MAPPING.items():
        img_path = os.path.join(ASSETS_PATH, img_name)
        img_key[img_path] = keys

    visible_state = {path: False for path in img_key}
    detection_cache = DetectionCache(ttl=0.1)

    try:
        while data["active"]:
            if not CommonLogger.wait_for_rage(page="stroyka", auto_move=module.walker, stop_event=module.stop_event):
                continue

            for path, keys in img_key.items():
                result = CommonLogger.safe_locate(path, 0.90)
                if result is not None:
                    detection_cache.set(path, result)
                    handle_visible_image(path, keys, visible_state, data, detection_cache)
                    break

            module.stop_event.wait(0.01)

    except Exception as e:
        add_log(f"[Критическая ошибка]\n{str(e)}", level="ERROR", page="stroyka")
    finally:
        module.cleanup()

def toggle_stroyka():
    if not state["modules"]["stroyka"]["active"]:
        state["modules"]["stroyka"]["counter"] = 0
    module.toggle(stroyka_worker)

@stroyka_bp.route('/stroyka')
def render_stroyka():
    settings = state["modules"]["stroyka"]["settings"]
    return render_template('stroyka.html',active=state["modules"]["stroyka"]["active"],settings=settings,counter=state["modules"]["stroyka"]["counter"])

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
