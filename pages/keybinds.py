import threading
import time
from flask import render_template, jsonify, request, Blueprint
from core.common import state, add_log, get_settings, update_settings
import pydirectinput

pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

keybinds_bp = Blueprint('keybinds', __name__)

state["modules"]["keybinds"] = state["modules"].get("keybinds", {
    "active": False,
    "settings": get_settings("keybinds")
})

if "binds" not in state["modules"]["keybinds"]["settings"]:
    state["modules"]["keybinds"]["settings"]["binds"] = []

active_threads = {}

def execute_bind(bind_data):
    bind_id = bind_data.get("id")
    keys = bind_data.get("keys", [])
    action_type = bind_data.get("action_type", "hold")
    hold_duration = bind_data.get("hold_duration", 2)
    cooldown = bind_data.get("cooldown", 5)
    repeat = bind_data.get("repeat", False)
    
    if not keys:
        return
    
    if bind_id in active_threads:
        active_threads[bind_id]["stop"] = True
        time.sleep(0.1)
    
    def worker():
        thread_data = {"stop": False}
        active_threads[bind_id] = thread_data
        name = bind_data.get('name', 'Без названия')
        try:
            add_log(f">>> Бинд '{name}' активирован", page="keybinds")
            
            while True:
                if thread_data["stop"]:
                    return
                
                if action_type == "hold":
                    for key in keys:
                        if thread_data["stop"]:
                            return
                        pydirectinput.keyDown(key.lower())
                    add_log(f"Зажаты клавиши: {', '.join(k.upper() for k in keys)} на {hold_duration} сек.", page="keybinds")
                    
                    elapsed = 0.0
                    while elapsed < hold_duration and not thread_data["stop"]:
                        time.sleep(0.05)
                        elapsed += 0.05
                    
                    for key in reversed(keys):
                        try:
                            pydirectinput.keyUp(key.lower())
                        except:
                            pass
                    
                    if thread_data["stop"]:
                        return
                        
                else:
                    for key in keys:
                        if thread_data["stop"]:
                            return
                        pydirectinput.press(key.lower())
                    add_log(f"Нажаты клавиши: {', '.join(k.upper() for k in keys)}", page="keybinds")
                
                if not repeat:
                    break
                
                add_log(f"Ожидание {cooldown} сек...", page="keybinds")
                elapsed = 0.0
                while elapsed < cooldown and not thread_data["stop"]:
                    time.sleep(0.05)
                    elapsed += 0.05
                    
        except Exception as e:
            add_log(f"Ошибка выполнения бинда: {e}", level="ERROR", page="keybinds")
        finally:
            for key in reversed(keys):
                try:
                    pydirectinput.keyUp(key.lower())
                except:
                    pass
            
            if bind_id in active_threads:
                del active_threads[bind_id]
            
            add_log(f">>> Бинд '{name}' остановлен", page="keybinds")
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

def toggle_bind(bind_id):
    if bind_id in active_threads:
        active_threads[bind_id]["stop"] = True
    else:
        binds = state["modules"]["keybinds"]["settings"].get("binds", [])
        bind = next((b for b in binds if b.get("id") == bind_id), None)
        if bind:
            execute_bind(bind)

def register_hotkeys(hm):
    binds = state["modules"]["keybinds"]["settings"].get("binds", [])
    for bind in binds:
        hotkey = bind.get("hotkey", "").lower()
        bind_id = bind.get("id")
        if hotkey and bind_id:
            hm.register(hotkey, lambda bid=bind_id: toggle_bind(bid))

@keybinds_bp.route('/keybinds')
def render_keybinds():
    loaded_settings = get_settings("keybinds")
    if not loaded_settings:
        loaded_settings = {"binds": []}
    if "binds" not in loaded_settings:
        loaded_settings["binds"] = []
    
    state["modules"]["keybinds"]["settings"] = loaded_settings
    
    print(f"[DEBUG] Loaded binds: {loaded_settings.get('binds', [])}")
    
    return render_template('keybinds.html', 
                         settings=loaded_settings,
                         active=state["modules"]["keybinds"].get("active", False),
                         logs=state["page_logs"].get("keybinds", []))

@keybinds_bp.route('/api/keybinds/save', methods=['POST'])
def api_save_binds():
    data = request.get_json()
    
    if data and 'binds' in data:
        binds = data['binds']
        state["modules"]["keybinds"]["settings"] = {"binds": binds}
        update_settings("keybinds", {"binds": binds}, page="keybinds")
        print(f"[DEBUG] Saved binds: {binds}")
        from core.common import hotkey_manager
        
        for bind in binds:
            hotkey = bind.get("hotkey", "").lower()
            if hotkey:
                hotkey_manager.unregister(hotkey)
        
        register_hotkeys(hotkey_manager)
        add_log("Биндлы сохранены и перезагружены", page="keybinds")
        return jsonify({"status": "ok", "message": "Биндлы сохранены"})

    return jsonify({"status": "error", "message": "Неверные данные"})

@keybinds_bp.route('/api/keybinds/test', methods=['POST'])
def api_test_bind():
    data = request.get_json()
    
    if data:
        bind_id = data.get("id")
        if bind_id:
            was_active = bind_id in active_threads
            toggle_bind(bind_id)
            if was_active:
                time.sleep(0.15)
                is_active = False
            else:
                time.sleep(0.05)
                is_active = bind_id in active_threads
            
            return jsonify({"status": "ok", "active": is_active})
    
    return jsonify({"status": "error"})

@keybinds_bp.route('/api/keybinds/active', methods=['GET'])
def api_active_binds():
    return jsonify({"active": list(active_threads.keys())})

@keybinds_bp.route('/api/keybinds/suspend', methods=['POST'])
def suspend_hotkeys():
    from core.common import hotkey_manager
    data = request.get_json() or {}
    hotkey_manager.suspended = bool(data.get('suspended', False))
    return jsonify(ok=True)

@keybinds_bp.route('/api/keybinds/stop_all', methods=['POST'])
def api_stop_all():
    for bind_id in list(active_threads.keys()):
        active_threads[bind_id]["stop"] = True
    
    add_log("Все биндлы остановлены", page="keybinds")
    return jsonify({"status": "ok"})
