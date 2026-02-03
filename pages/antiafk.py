import random
import threading
from flask import render_template, jsonify, request, Blueprint
from core.common import state, add_log, get_settings, update_settings

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except (ImportError, Exception):
    VGAMEPAD_AVAILABLE = False
    vg = None

stop_event = threading.Event()
gamepad = None
antiafk_bp = Blueprint('antiafk', __name__)

DIRECTIONS = {'up': (0, 32767),'down': (0, -32767),'left': (-32767, 0),'right': (32767, 0),'up_right': (20000, 20000),'up_left': (-20000, 20000),'down_right': (20000, -20000),'down_left': (-20000, -20000),'center': (0, 0)}

state["modules"]["antiafk"]["settings"] = get_settings("antiafk")

def anti_afk_worker():
    global gamepad
    stop_event.clear()
    data = state["modules"]["antiafk"]
    
    try:
        if not gamepad: 
            gamepad = vg.VX360Gamepad()
        
        add_log(">>> Anti-AFK запущен", page="antiafk")
        
        while data["active"]:
            direction = random.choice(list(DIRECTIONS.keys()))
            x, y = DIRECTIONS[direction]
            
            hold = random.uniform(
                float(data['settings']['min_delay']), 
                float(data['settings']['max_delay'])
            )
            
            add_log(f"Движение: {direction.upper()} ({hold:.1f} сек.)", page="antiafk")
            
            gamepad.left_joystick(x_value=x, y_value=y)
            gamepad.update()
            
            if stop_event.wait(timeout=hold): 
                break

            gamepad.reset()
            gamepad.update()
            
            if not data["active"]:
                break
                
            pause = random.uniform(
                float(data['settings']['min_pause']), 
                float(data['settings']['max_pause'])
            )
            
            add_log(f"Пауза: {pause:.1f} сек.", page="antiafk")
            
            if stop_event.wait(timeout=pause): 
                break
                
    except Exception as e:
        add_log(f"Ошибка воркера: {e}", level="ERROR", page="antiafk")
    finally:
        if gamepad:
            gamepad.reset()
            gamepad.update()
        data["active"] = False
        add_log(">>> Anti-AFK остановлен", page="antiafk")

def toggle_antiafk():
    if not VGAMEPAD_AVAILABLE:
        return
    data = state["modules"]["antiafk"]
    if not data["active"]:
        data["active"] = True
        threading.Thread(target=anti_afk_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()

@antiafk_bp.route('/antiafk')
def render_antiafk():
    return render_template('antiafk.html', **state["modules"]["antiafk"], logs=state["page_logs"].get("antiafk", []), vgamepad_available=VGAMEPAD_AVAILABLE)

def register_hotkeys(hm):
    if VGAMEPAD_AVAILABLE:
        hm.register('f5', toggle_antiafk)


if VGAMEPAD_AVAILABLE:
    @antiafk_bp.route('/api/antiafk/toggle', methods=['POST'])
    def api_toggle():
        data = request.get_json()
        
        if data and 'settings' in data:
            s = data['settings']
            settings = {
                'min_delay': float(s.get('min_delay', 0.5)),
                'max_delay': float(s.get('max_delay', 2.0)),
                'min_pause': float(s.get('min_pause', 5.0)),
                'max_pause': float(s.get('max_pause', 15.0))
            }
            state["modules"]["antiafk"]["settings"] = settings
            update_settings("antiafk", settings, page="antiafk")
        
        toggle_antiafk()
        return jsonify({
            "status": "ok", 
            "active": state["modules"]["antiafk"]["active"]
        })