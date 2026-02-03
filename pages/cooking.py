import threading
import pyautogui
import time
import os
from flask import render_template, jsonify, Blueprint, request
from core.common import (
    state, add_log, CommonLogger, 
    get_settings, update_settings
)

cooking_bp = Blueprint('cooking', __name__)
stop_event = threading.Event()

state["modules"]["cooking"] = {
    "active": False,
    "settings": get_settings("cooking")
}

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

def find_and_perform_action(image_filename: str, click_type: str, data: dict) -> bool:
    """Ищет изображение на экране и выполняет действие"""
    full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
    
    try:
        location = pyautogui.locateCenterOnScreen(full_image_path, confidence=0.85)
        if location:
            if click_type == "right":
                pyautogui.rightClick(location)
                add_log(f"[✓] Использован/перетащен: {image_filename}.", page="cooking")
            elif click_type == "left":
                pyautogui.click(location)
                add_log(f"[✓] Клик по кнопке: {image_filename}.", page="cooking")
            return True
        else:
            add_log(f"[!] Изображение не найдено: {image_filename}.", page="cooking")
            return False
    except Exception as e:
        return False

def execute_recipe(dish_name: str, data: dict) -> bool:
    """Выполняет рецепт блюда"""
    recipe_steps = RECIPES.get(dish_name)
    if not recipe_steps:
        return False
    
    for image_filename, action_type in recipe_steps:
        if not data["active"]:
            return False
        
        if not find_and_perform_action(image_filename, action_type, data):
            return False
        
        stop_event.wait(0.1)
    
    add_log(f"[✓] Все шаги для приготовления '{dish_name}' выполнены.", page="cooking")
    return True

def cooking_worker(dish_name: str):
    add_log(f"[→] Скрипт готовки запущен для блюда: {dish_name}", page="cooking")
    data = state["modules"]["cooking"]
    cycles_count = 0
    waiting_for_recipe_elements = False
    
    try:
        while data["active"]:
            if not CommonLogger.wait_for_rage(page="cooking", stop_event=stop_event):
                continue
            
            if execute_recipe(dish_name, data):
                cycles_count += 1
                add_log(f"[✓] Цикл готовки №{cycles_count} для '{dish_name}' завершён.", page="cooking")
                add_log("Ожидание перезарядки (5.5 секунд)...", page="cooking")
                waiting_for_recipe_elements = False
                stop_event.wait(5.5)
            else:
                if not waiting_for_recipe_elements:
                    add_log(f"[!] Ожидание появления всех элементов для '{dish_name}'...", page="cooking")
                    waiting_for_recipe_elements = True
                stop_event.wait(1)
                    
    except Exception as exc:
        add_log(f"[Ошибка потока] {exc}", level="ERROR", page="cooking")
    finally:
        data["active"] = False
        add_log(">>> Модуль Готовка остановлен", page="cooking")

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
    return render_template(
        'cooking.html',
        active=state["modules"]["cooking"]["active"],
        settings=settings,
        recipes=list(RECIPES.keys())
    )

@cooking_bp.route('/api/cooking/toggle', methods=['POST'])
def api_toggle_cooking():
    data = request.get_json() or {}
    dish_name = data.get('dish', 'Фруктовый смузи')
    toggle_cooking(dish_name)
    return jsonify({'active': state["modules"]["cooking"]["active"]})
