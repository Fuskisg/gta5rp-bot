import threading
import time
import cv2
import numpy as np
import mss
import os
from flask import render_template, jsonify, Blueprint, request
from core.common import state, add_log, press, auto_detect_region,hotkey_manager, get_settings, update_settings

cow_bp = Blueprint('cow', __name__)
stop_event = threading.Event()
last_registered_hotkey = None

state["modules"]["cow"] = {
    "active": False,
    "settings": get_settings("cow"),
}

try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(max(1, os.cpu_count() - 1))
except Exception:
    pass

auto_e_enabled = False
templates = {}

def load_cow_templates():
    global templates
    templates = {}
    template_dir = os.path.join('static', 'assets', 'cow')
    
    if not os.path.exists(template_dir):
        add_log(f"⚠️ Папка {template_dir} не найдена", level="WARNING", page="cow")
        return
    
    for filename in ['1.png', '2.png']:
        filepath = os.path.join(template_dir, filename)
        if os.path.exists(filepath):
            img = cv2.imread(filepath)
            if img is not None:
                templates[filename.split('.')[0]] = img
                add_log(f"✓ Шаблон {filename} загружен", page="cow")
            else:
                add_log(f"⚠️ Не удалось загрузить {filename}", level="WARNING", page="cow")
        else:
            add_log(f"⚠️ Файл {filepath} не найден", level="WARNING", page="cow")

def toggle_auto_e():
    global auto_e_enabled
    auto_e_enabled = not auto_e_enabled
    status = "включено" if auto_e_enabled else "выключено"
    add_log(f"[⌨️] Автонажатие E {status}", page="cow")

def cow_worker(pause_delay: float):
    global auto_e_enabled, templates
    add_log(">>> Модуль Коровы запущен", page="cow")
    data = state["modules"]["cow"]
    
    if not templates:
        load_cow_templates()
    
    if not templates:
        add_log("❌ Шаблоны не загружены, модуль остановлен", level="ERROR", page="cow")
        data["active"] = False
        return
    
    try:
        monitor = auto_detect_region(width_ratio=1.0, height_ratio=0.65, top_ratio=0.35)
        add_log(f"Область поиска: {monitor}", page="cow")
    except Exception as e:
        add_log(f"Ошибка определения региона: {e}", level="WARNING", page="cow")
        data["active"] = False
        return
    
    try:
        with mss.mss() as sct:
            while data["active"] and not stop_event.is_set():
                frame = np.array(sct.grab(monitor))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                scores = {}
                for key, template in templates.items():
                    res = cv2.matchTemplate(frame_rgb, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val >= 0.92:
                        scores[key] = max_val
                
                found = bool(scores)
                
                if found:
                    if scores.get("1", -1) >= scores.get("2", -1):
                        press('a')
                        add_log("◀ Нажата 'a'", page="cow")
                    else:
                        press('d')
                        add_log("▶ Нажата 'd'", page="cow")
                
                elif auto_e_enabled:
                    press('e')
                
                if stop_event.wait(pause_delay):
                    break
    
    except Exception as exc:
        add_log(f"[Ошибка потока] {str(exc)}", level="ERROR", page="cow")
    finally:
        add_log("<<< Модуль Коровы остановлен", page="cow")
        data["active"] = False

@cow_bp.route('/cow')
def cow_page():
    settings = state["modules"]["cow"]["settings"]
    active = state["modules"]["cow"]["active"]
    return render_template('cow.html', settings=settings, active=active)

@cow_bp.route('/api/cow/toggle', methods=['POST'])
def toggle_cow():
    global last_registered_hotkey
    
    req_data = request.get_json()
    auto_e_hotkey = req_data.get('auto_e_hotkey', 'f5').lower()
    pause = float(req_data.get('pause', 0.07))
    
    data = state["modules"]["cow"]
    
    update_settings("cow", {
        "auto_e_hotkey": auto_e_hotkey,
        "pause": pause
    })
    data["settings"] = get_settings("cow")
    
    if not data["active"]:
        stop_event.clear()
        data["active"] = True
        
        if last_registered_hotkey and last_registered_hotkey in hotkey_manager.actions:
            del hotkey_manager.actions[last_registered_hotkey]
        
        hotkey_manager.register(auto_e_hotkey, toggle_auto_e)
        last_registered_hotkey = auto_e_hotkey
        add_log(f"[⌨️] Хоткей '{auto_e_hotkey.upper()}' зарегистрирован для автонажатия E", page="cow")
        
        t = threading.Thread(target=cow_worker, args=(pause,), daemon=True)
        t.start()
    else:
        data["active"] = False
        stop_event.set()
        
        if last_registered_hotkey and last_registered_hotkey in hotkey_manager.actions:
            del hotkey_manager.actions[last_registered_hotkey]
            add_log(f"[⌨️] Хоткей '{last_registered_hotkey.upper()}' отключен", page="cow")
    
    return jsonify({"active": data["active"]})
