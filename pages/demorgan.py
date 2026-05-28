import threading
import time
import cv2
import numpy as np
import mss
import os
import pyautogui
from flask import render_template, jsonify, request, Blueprint
from core.common import state, add_log, get_settings, update_settings, auto_detect_region

stop_event = threading.Event()
demorgan_bp = Blueprint('demorgan', __name__)

state["modules"]["demorgan"]["settings"] = get_settings("demorgan") or {
    "tokar_pause": 65,
    "shveika_pause": 85,
    "shveika_exe": 0.1
}


def play_beep():
    try:
        import winsound
        wav_path = os.path.join(os.path.dirname(__file__), '..', "static", "wav", "beep.wav")
        if os.path.exists(wav_path):
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass


def load_template_image(filename: str) -> np.ndarray:
    template_path = os.path.join(os.path.dirname(__file__), f'../static/assets/{filename}')
    if os.path.exists(template_path):
        img = cv2.imread(template_path, cv2.IMREAD_COLOR)
        return img
    else:
        add_log(f"⚠️ Шаблон {filename} не найден", page="demorgan")
        return None

def start_timer(seconds: int, label: str, page_name: str = "demorgan") -> dict:
    cancel = {"active": True}

    def _run():
        start = time.time()
        while cancel["active"] and not stop_event.is_set() and (time.time() - start) < seconds:
            left = seconds - int(time.time() - start)
            mins, secs = divmod(left, 60)
            add_log(f"[timer] {label}: {mins:02d}:{secs:02d}", page=page_name)
            stop_event.wait(1)

        if cancel["active"] and not stop_event.is_set():
            add_log(f"[✔] {label} завершён!", page=page_name)
            play_beep()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    cancel["thread"] = t
    return cancel


def demorgan_worker():
    stop_event.clear()
    data = state["modules"]["demorgan"]
    settings = data["settings"]

    try:
        add_log(">>> Деморган запущен", page="demorgan")

        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                smoothing, _ = winreg.QueryValueEx(key, "FontSmoothing")

            if str(smoothing) == "0":
                add_log("⚠️ Сглаживание шрифтов: выключено", page="demorgan")
        except Exception:
            pass

        tokar_pause = settings.get("tokar_pause", 65)
        shveika_pause = settings.get("shveika_pause", 85)
        shveika_exe = settings.get("shveika_exe", 0.1)
        monitor_tokar = auto_detect_region(0.5,0.6,0.25)
        monitor = auto_detect_region(0.4,1,0)

        tokar_template = load_template_image("tokar/i3.png")
        shveika_templates = [load_template_image(f"shveika/{i+1}.png") for i in range(20)]

        if tokar_template is None or any(t is None for t in shveika_templates):
            add_log("[⚠️] Не все шаблоны загружены", page="demorgan")
            none_count = sum(1 for t in shveika_templates if t is None)
            add_log(f"[⚠️] Токарь: {tokar_template is not None}, Швейка: {20 - none_count}/20", page="demorgan")
            add_log("[⚠️] Возможно по пути к боту есть русские символы", page="demorgan")
            return

        add_log(f"[✓] Шаблоны загружены. Токарь: {tokar_template.shape}, Швейка: {shveika_templates[0].shape if shveika_templates[0] is not None else 'None'}", page="demorgan")
        is_tokar_found = False
        last_known_position = None
        tokar_timer_active = False
        tokar_timer_start = 0
        tokar_processed = False

        def run_tokar():
            nonlocal is_tokar_found, last_known_position, tokar_timer_active, tokar_timer_start, tokar_processed
            h, w = tokar_template.shape[:2]
            last_full_scan = 0.0
            is_tracking = False
            
            with mss.mss() as sct:
                while data["active"]:
                    try:
                        found = False
                        
                        if last_known_position:
                            cx, cy = last_known_position
                            region = {
                                "left": max(cx - 100, monitor_tokar["left"]),
                                "top": max(cy - 100 - h // 2, monitor_tokar["top"]),
                                "width": min(cx + 100, monitor_tokar["left"] + monitor_tokar["width"]) - max(cx - 100, monitor_tokar["left"]),
                                "height": min(cy + 100 - h // 2, monitor_tokar["top"] + monitor_tokar["height"]) - max(cy - 100 - h // 2, monitor_tokar["top"]),
                            }
                            found = search_in_region_tokar(sct, region, tokar_template, h, w)
                        
                        if not found and time.time() - last_full_scan > 0.3:
                            found = search_in_region_tokar(sct, monitor, tokar_template, h, w)
                            last_full_scan = time.time()
                        
                        if found:
                            if not is_tracking:
                                is_tokar_found = True
                                tokar_timer_active = True
                                tokar_timer_start = time.time()
                                if not tokar_processed:
                                    add_log(f"[✓] Токарь найден | ожидание {tokar_pause}с", page="demorgan")
                                    start_timer(tokar_pause, "Токарь", page_name="demorgan")
                                    tokar_processed = True
                                is_tracking = True
                        else:
                            if is_tracking:
                                is_tracking = False
                                last_known_position = None
                                is_tokar_found = False
                                tokar_processed = False
                            stop_event.wait(0.02)
                    
                    except Exception as e:
                        add_log(f"[Ошибка потока токаря] {str(e)[:80]}", page="demorgan")
                        stop_event.wait(0.1)

        def run_shveika():
            nonlocal tokar_timer_active, is_tokar_found
            last_wait_logged = 0.0
            sentinel_template = shveika_templates[0]
            
            with mss.mss() as sct:
                while data["active"]:
                    try:
                        if is_tokar_found:
                            stop_event.wait(0.05)
                            continue

                        frame = np.array(sct.grab(monitor))
                        image_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                        sentinel_center, _ = locate_one(image_bgr, sentinel_template, 0.85)
                        if sentinel_center is None:
                            if time.time() - last_wait_logged > 1.5:
                                last_wait_logged = time.time()
                            stop_event.wait(0.01)
                            continue

                        coords = locate_all_20(image_bgr, shveika_templates, 0.85)

                        if not all(coords):
                            if time.time() - last_wait_logged > 1.5:
                                missing = [i + 1 for i, c in enumerate(coords) if c is None]
                                add_log(f"[~] Ожидание элементов... отсутствуют: "f"{missing[:6]}{'...' if len(missing) > 6 else ''}", page="demorgan")
                                last_wait_logged = time.time()
                            stop_event.wait(0.03)
                            continue

                        add_log("[✓] Все 20 точек найдены. Начинаю клик.", page="demorgan")
                        start_timer(shveika_pause, "Швейка", page_name="demorgan")

                        for i, pos in enumerate(coords):
                            if not data["active"]:
                                break
                            
                            abs_pos = (pos[0] + monitor["left"], pos[1] + monitor["top"])
                            pyautogui.click(abs_pos)
                            if i != 0:
                                stop_event.wait(shveika_exe)
                                pyautogui.click(abs_pos)

                            add_log(f"[Клик] {i + 1}/20: {abs_pos} ({'1' if i == 0 else '2'} раз)", page="demorgan")
                        stop_event.wait(0.03)

                    
                    except Exception as e:
                        add_log(f"[Ошибка потока швейки] {str(e)[:80]}", page="demorgan")
                        stop_event.wait(0.1)

        def search_in_region_tokar(sct, region, template, h, w):
            nonlocal last_known_position
            try:
                screenshot = np.array(sct.grab(region))
                screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                
                result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if float(max_val) > 0.88:
                    found_x = region["left"] + max_loc[0] + w // 2
                    found_y = region["top"] + max_loc[1] + h
                    last_known_position = (found_x, found_y)
                    pyautogui.moveTo(found_x, found_y + 30)
                    return True
                return False
            except:
                return False

        def locate_one(image_bgr, templ_bgr, threshold):
            res = cv2.matchTemplate(image_bgr, templ_bgr, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if float(max_val) >= threshold:
                h, w = templ_bgr.shape[:2]
                center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                return center, max_val
            return None, max_val

        def locate_all_20(image_bgr, templates, threshold):
            coords = []
            for templ in templates:
                c, _ = locate_one(image_bgr, templ, threshold)
                coords.append(c)
            return coords

        t_tokar = threading.Thread(target=run_tokar, daemon=True)
        t_shveika = threading.Thread(target=run_shveika, daemon=True)
        
        t_tokar.start()
        t_shveika.start()
        t_tokar.join()
        t_shveika.join()

    except Exception as e:
        add_log(f"[Ошибка воркера] {str(e)}", page="demorgan")
    finally:
        data["active"] = False
        add_log(">>> Деморган остановлен", page="demorgan")

def toggle_demorgan():
    data = state["modules"]["demorgan"]
    if not data["active"]:
        data["active"] = True
        threading.Thread(target=demorgan_worker, daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()

@demorgan_bp.route('/demorgan')
def render_demorgan():
    return render_template('demorgan.html', **state["modules"]["demorgan"])

def register_hotkeys(hm):
    hm.register('f6', toggle_demorgan)

@demorgan_bp.route('/api/demorgan/toggle', methods=['POST'])
def api_toggle():
    data = request.get_json()
    if data and 'settings' in data:
        s = data['settings']
        settings = {
            'tokar_pause': int(s.get('tokar_pause', 65)),
            'shveika_pause': int(s.get('shveika_pause', 85)),
            'shveika_exe': float(s.get('shveika_exe', 0.1))
        }
        state["modules"]["demorgan"]["settings"] = settings
        update_settings("demorgan", settings, page="demorgan")
    
    toggle_demorgan()
    return jsonify({
        "status": "ok",
        "active": state["modules"]["demorgan"]["active"]
    })
