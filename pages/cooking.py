import cv2
import numpy as np
import pyautogui
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import render_template, jsonify, Blueprint, request
from core.common import (state, add_log, CommonLogger, get_settings, update_settings, init_module)
import win32api
import win32con

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

cooking_bp = Blueprint('cooking', __name__)
stop_event = threading.Event()

init_module("cooking")

BASE_ASSETS_PATH = "static/assets/cook/"
RECIPES = {
    "Фруктовый смузи": [
        ("frukti.png", "right"),
        ("voda2.png", "right"),
        ("whisk2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Фруктовый салат": [
        ("frukti.png", "right"),
        ("knife2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Овощной салат": [
        ("ovoshi.png", "right"),
        ("knife2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Овощной смузи": [
        ("ovoshi.png", "right"),
        ("voda2.png", "right"),
        ("whisk2.png", "right"),
        ("startCoocking.png", "left")
    ],
    "Рагу": [
        ("myaso.png", "right"),
        ("ovoshi.png", "right"),
        ("voda2.png", "right"),
        ("fire2.png", "right"),
        ("startCoocking.png", "left")
    ]
}

_template_cache = {}
_image_scales = {}
_last_screenshot = None
_last_screenshot_time = 0

SCALES = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]

def instant_click(x, y, click_type="left"):
    win32api.SetCursorPos((x, y))
    if click_type == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)
    else:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

def get_screenshot(force_new=False, max_age=0.1):
    global _last_screenshot, _last_screenshot_time
    current_time = time.time()
    if force_new or _last_screenshot is None or (current_time - _last_screenshot_time) > max_age:
        _last_screenshot = pyautogui.screenshot()
        _last_screenshot_time = current_time
    return _last_screenshot

def load_template(image_filename: str):
    if image_filename not in _template_cache:
        full_path = os.path.join(os.path.dirname(__file__), '..', BASE_ASSETS_PATH, image_filename)
        template = cv2.imread(full_path)
        if template is None:
            add_log(f"[Ошибка] Не удалось загрузить: {image_filename}", page="cooking")
            return None
        _template_cache[image_filename] = template
    return _template_cache[image_filename]

def find_scale_single(args):
    screenshot_cv, template, scale, screen_w, screen_h = args
    template_h, template_w = template.shape[:2]
    
    new_w = int(template_w * scale)
    new_h = int(template_h * scale)
    
    if new_w < 20 or new_h < 20 or new_w > screen_w or new_h > screen_h:
        return (scale, 0)
    
    resized = cv2.resize(template, (new_w, new_h))
    result = cv2.matchTemplate(screenshot_cv, resized, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    
    return (scale, max_val)

def find_best_scale_fast(template, screenshot_cv, confidence=0.75):
    screen_h, screen_w = screenshot_cv.shape[:2]
    template_h, template_w = template.shape[:2]
    
    args_list = [(screenshot_cv, template, s, screen_w, screen_h) for s in SCALES]
    
    best_conf = 0
    best_scale = None
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for scale, max_val in executor.map(find_scale_single, args_list):
            if max_val > best_conf:
                best_conf = max_val
                best_scale = scale
            if max_val >= 0.95:
                break
    
    if best_conf >= confidence:
        return best_scale, best_conf
    return None, best_conf

def calibrate_all_parallel(images: list[str], confidence=0.75):
    screenshot = get_screenshot(force_new=True)
    screenshot_np = np.array(screenshot)
    screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    
    results = {}
    failed = []
    
    def calibrate_one(img_name):
        template = load_template(img_name)
        if template is None:
            return (img_name, None, 0)
        scale, conf = find_best_scale_fast(template, screenshot_cv, confidence)
        return (img_name, scale, conf)
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(calibrate_one, img): img for img in images}
        
        for future in as_completed(futures):
            img_name, scale, conf = future.result()
            if scale:
                results[img_name] = scale
                add_log(f"[✓] {img_name}: {scale:.2f} ({conf:.2f})", page="cooking")
            else:
                failed.append(f"{img_name}({conf:.2f})")
    
    if failed:
        add_log(f"[✗] Не откалибровано: {', '.join(failed)}", page="cooking")
    
    return results if len(results) == len(images) else None

def find_with_scale(image_filename: str, scale: float, confidence=0.7):
    template = load_template(image_filename)
    if template is None or scale is None:
        return None
    
    screenshot = get_screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    
    h, w = template.shape[:2]
    new_w, new_h = int(w * scale), int(h * scale)
    
    if new_w < 10 or new_h < 10:
        return None
    
    screen_h, screen_w = screenshot_cv.shape[:2]
    if new_w > screen_w or new_h > screen_h:
        return None
    
    resized = cv2.resize(template, (new_w, new_h))
    result = cv2.matchTemplate(screenshot_cv, resized, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if max_val >= confidence:
        return (max_loc[0] + new_w // 2, max_loc[1] + new_h // 2)
    
    return None

def calibrate_recipe_scales(dish_name: str) -> bool:
    global _image_scales
    
    recipe_steps = RECIPES.get(dish_name, [])
    if not recipe_steps:
        return False
    
    seen = set()
    unique_images = [x for x in [img for img, _ in recipe_steps] if not (x in seen or seen.add(x))]
    
    add_log(f"[🔧] Параллельная калибровка '{dish_name}': {len(unique_images)} картинок", page="cooking")
    
    start_time = time.time()
    _image_scales = calibrate_all_parallel(unique_images)
    elapsed = time.time() - start_time
    
    if _image_scales:
        add_log(f"[✓] Калибровка за {elapsed:.2f}s: {_image_scales}", page="cooking")
        return True
    
    add_log(f"[✗] Калибровка провалена ({elapsed:.2f}s)", page="cooking")
    return False

def execute_recipe_fast(dish_name: str, data: dict) -> tuple[bool, list[str]]:
    recipe_steps = RECIPES.get(dish_name)
    if not recipe_steps:
        return False, ["Рецепт не найден"]
    
    if not _image_scales:
        return False, ["Нет калибровки"]
    
    not_found = []
    get_screenshot(force_new=True)
    
    for image_filename, action_type in recipe_steps:
        if not data["active"]:
            return False, not_found
        
        scale = _image_scales.get(image_filename)
        location = find_with_scale(image_filename, scale) if scale else None
        
        if location:
            instant_click(location[0], location[1], action_type)
        else:
            add_log(f"[!] {image_filename} не найден, перекалибровка...", page="cooking")
            return False, [image_filename]
    
    return True, []

def reset_scales():
    global _image_scales
    _image_scales = {}
    add_log("[↺] Масштабы сброшены", page="cooking")

def cooking_worker(dish_name: str):
    global _image_scales
    
    reset_scales()
    add_log(f"[→] Запущен: {dish_name}", page="cooking")
    
    data = state["modules"]["cooking"]
    cycles_count = 0
    last_not_found = []
    calibrated = False
    
    try:
        while data["active"]:
            if not CommonLogger.wait_for_rage(page="cooking", stop_event=stop_event):
                continue
            
            if not calibrated:
                if calibrate_recipe_scales(dish_name):
                    calibrated = True
                else:
                    stop_event.wait(0.5)
                    continue
            
            success, not_found = execute_recipe_fast(dish_name, data)
            
            if success:
                cycles_count += 1
                add_log(f"[✓] Цикл №{cycles_count}", page="cooking")
                last_not_found = []
                stop_event.wait(5.5)
            else:
                if not_found != last_not_found:
                    items_str = ", ".join(not_found)
                    add_log(f"[!] Не найдено: {items_str}", page="cooking")
                    last_not_found = not_found.copy()
                
                if not_found:
                    calibrated = False
                    reset_scales()
                
                stop_event.wait(0.5)
                    
    except Exception as exc:
        add_log(f"[Ошибка] {exc}", level="ERROR", page="cooking")
    finally:
        data["active"] = False
        reset_scales()
        add_log(">>> Остановлен", page="cooking")

def toggle_cooking(dish_name: str):
    data = state["modules"]["cooking"]
    if not data["active"]:
        data["active"] = True
        data["settings"]["selected_dish"] = dish_name
        update_settings("cooking", data["settings"])
        stop_event.clear()
        threading.Thread(target=cooking_worker, args=(dish_name,), daemon=True).start()
    else:
        data["active"] = False
        stop_event.set()

@cooking_bp.route('/cooking')
def render_cooking():
    settings = state["modules"]["cooking"]["settings"]
    return render_template('cooking.html',active=state["modules"]["cooking"]["active"],settings=settings,recipes=list(RECIPES.keys()),current_scale=None)

@cooking_bp.route('/api/cooking/toggle', methods=['POST'])
def api_toggle_cooking():
    data = request.get_json() or {}
    dish_name = data.get('dish', 'Фруктовый смузи')
    toggle_cooking(dish_name)
    return jsonify({
        'active': state["modules"]["cooking"]["active"],
        'scale': list(_image_scales.values())[0] if _image_scales else None
    })