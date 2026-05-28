import threading
import queue
import time
import logging
import json
import os
from typing import Dict, List, Callable, Any, Optional, Tuple, Union
from logging.handlers import RotatingFileHandler
import pygetwindow as gw
import traceback
import pyautogui
from pyautogui import ImageNotFoundException
import pydirectinput
import cv2
import numpy as np
import mss

cached_online = "загрузка..."
version="4.5"
cached_update = {"needs_update": False, "remote_version": "", "local_version": version}

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

config_dir = os.path.join('configs')
CONFIG_FILE = os.path.join(config_dir, 'config.json')
log_file = os.path.join(config_dir, 'log.txt')

if not os.path.exists(config_dir):
    os.makedirs(config_dir)

file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)
logging.getLogger().handlers[0].flush()

clients: List[queue.Queue] = []
_clients_lock = threading.Lock()
_config_lock = threading.Lock()
_config_cache: Optional[dict] = None


class ModuleState(dict):
    def __init__(self, active: bool = False, settings: Optional[Dict[str, Any]] = None):
        super().__init__()
        self['active'] = active
        self['settings'] = settings or {}

    @property
    def active(self) -> bool:
        return self['active']

    @active.setter
    def active(self, value: bool):
        self['active'] = value

    @property
    def settings(self) -> Dict[str, Any]:
        return self['settings']

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        self['settings'] = value

state = {
    "current_page": "index",
    "modules": {
        "antiafk": ModuleState(
            active=False,
            settings={"min_delay": 1.0, "max_delay": 1.0, "min_pause": 1.0, "max_pause": 1.0}
        ),
        "port": ModuleState(
            active=False,
            settings={"hotkey_port": "f5"}
        ),
        "demorgan": ModuleState(
            active=False,
            settings={"tokar_pause": 65, "shveika_pause": 85, "shveika_exe": 0.1}
        ),
        "kpk": ModuleState(
            active=False,
            settings={"hotkey_kpk": "f5"}
        )
    },
    "logs": [],
    "page_logs": {}
}

DEFAULT_CONFIG = {
    "settings": {
        "switch_hover": True,
        "switch_click": True,
        "volume_hover": 35,
        "volume_click": 45,
        "background": "bot"
    },
    "antiafk": {
        "min_delay": 1.0,
        "max_delay": 3.0,
        "min_pause": 5.0,
        "max_pause": 10.0
    },
    "port": {
        "hotkey_port": "f5"
    },
    "demorgan": {
        "tokar_pause": 65,
        "shveika_pause": 85,
        "shveika_exe": 0.1
    },
    "keybinds": {
        "binds": []
    },
    "kpk": {
        "hotkey_kpk": "f5"
    }
}

def add_log(msg: str, level: str = "INFO", page: str = "global"):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] [{page}] {msg}"

    state["logs"].append(formatted_msg)
    if len(state["logs"]) > 100:
        state["logs"].pop(0)

    if page not in state["page_logs"]:
        state["page_logs"][page] = []
    state["page_logs"][page].append(formatted_msg)
    if len(state["page_logs"][page]) > 50:  # Ограничение на 50 логов на страницу
        state["page_logs"][page].pop(0)

    with _clients_lock:
        for q in clients[:]:
            try:
                q.put_nowait(formatted_msg)
            except Exception:
                clients.remove(q)

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(formatted_msg)

def load_config():
    global _config_cache
    with _config_lock:
        if _config_cache is not None:
            return _config_cache
        if not os.path.exists(CONFIG_FILE):
            _config_cache = DEFAULT_CONFIG.copy()
            return _config_cache
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
                return _config_cache
        except (json.JSONDecodeError, IOError):
            add_log(f"{CONFIG_FILE} повреждён, загружены стандартные настройки", level="WARNING", page="system")
            _config_cache = DEFAULT_CONFIG.copy()
            return _config_cache

def save_config(config: dict, page: str = "system"):
    global _config_cache
    try:
        temp_file = CONFIG_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        os.replace(temp_file, CONFIG_FILE)
        with _config_lock:
            _config_cache = config.copy()
        return True
    except Exception as e:
        add_log(f"Ошибка при сохранении: {str(e)}", level="ERROR", page=page)
        return False

def get_settings(section: str):
    config = load_config()
    return config.get(section, DEFAULT_CONFIG.get(section, {})).copy()

def update_settings(section: str, settings: dict, page: str = "system"):
    config = load_config()
    config[section] = settings
    return save_config(config, page=page)

class HotkeyManager:
    def __init__(self):
        self.actions: Dict[str, Callable[[], None]] = {}
        self.suspended = False

    def register(self, key: str, callback: Callable[[], None]):
        if not callable(callback):
            raise ValueError(f"Callback for key '{key}' must be callable")
        self.actions[key.lower()] = callback
        logger.info(f"Зарегистрирован хоткей: {key}")

    def unregister(self, key: str):
        key_lower = key.lower()
        if key_lower in self.actions:
            del self.actions[key_lower]
            logger.info(f"Хоткей удалён: {key}")

    def clear(self):
        self.actions.clear()
        logger.info("Все хоткеи очищены")

    def get_action(self, key: str) -> Optional[Callable[[], None]]:
        return self.actions.get(key.lower())

hotkey_manager = HotkeyManager()

def press(key: str):
    pydirectinput.PAUSE = 0 
    pydirectinput.FAILSAFE = False
    pydirectinput.press(key)

class CommonLogger:
    _last_check = 0
    _last_result = False
    _was_missing = True
    _REPLACEMENTS = {
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
        "у": "y", "х": "x", "м": "m", "т": "t", "н": "h",
        "в": "b", "к": "k",
    }

    @staticmethod
    def is_rage_active() -> bool:
        try:
            active = gw.getActiveWindow()
            if not active or not active.title:
                return False

            title = active.title.casefold()
            normalized = "".join(CommonLogger._REPLACEMENTS.get(c, c) for c in title)
            return "multi" in normalized
        except Exception:
            return False

    @staticmethod
    def is_rage_active_cached(interval: float = 0.5) -> bool:
        now = time.time()
        if now - CommonLogger._last_check >= interval:
            CommonLogger._last_check = now
            CommonLogger._last_result = CommonLogger.is_rage_active()
        return CommonLogger._last_result

    @staticmethod
    def safe_locate(path: str, confidence: float = 0.95) -> Any:
        try:
            return pyautogui.locateOnScreen(path, confidence=confidence)
        except ImageNotFoundException:
            return None
        except Exception as e:
            logger.info(f"[Ошибка] locate {os.path.basename(path)}: {traceback.format_exc()}")
            return None

    @staticmethod
    def wait_for_rage(page: str = "global", auto_move: Optional[Any] = None, 
                      sleep_time: float = 1.0, force_log: bool = False,
                      stop_event: Optional[threading.Event] = None) -> bool:
        active = CommonLogger.is_rage_active_cached()

        if active:
            if CommonLogger._was_missing or force_log:
                add_log("Окно RAGE Multiplayer найдено. Скрипт активен.", level="INFO", page=page)
                CommonLogger._was_missing = False
            return True
        
        if auto_move:
            try:
                auto_move.force_disable()
            except Exception as e:
                logger.error(f"Ошибка при попытке force_disable: {e}")

        if not CommonLogger._was_missing or force_log:
            add_log("Окно RAGE Multiplayer не активно. Ожидание...", level="WARNING", page=page)
            CommonLogger._was_missing = True

        if stop_event:
            stop_event.wait(sleep_time)
        else:
            time.sleep(sleep_time)
            
        return False

    @staticmethod
    def reset_flags():
        CommonLogger._was_missing = True
        CommonLogger._last_check = 0
        CommonLogger._last_result = False

def auto_detect_region(width_ratio=None, height_ratio=None, top_ratio=None, reference_height=None, reference_top=None):
    screen_width, screen_height = pyautogui.size()

    if width_ratio is None:
        width_ratio = 0.5
    if height_ratio is None:
        height_ratio = 0.7
    if top_ratio is None:
        top_ratio = 0.25

    if reference_height is not None and reference_top is not None:
        top_ratio = reference_top / reference_height

    region_width = int(screen_width * width_ratio)
    region_height = int(screen_height * height_ratio)

    region = {
        "left": int((screen_width - region_width) / 2),
        "top": int(screen_height * top_ratio),
        "width": region_width,
        "height": region_height,
    }
    return region

class AutoHold:
    def __init__(self, keys: List[str], page: str = "antiafk"):
        self.keys = keys
        self.enabled = False
        self.page = page

    def toggle(self):
        if not self.enabled:
            if not CommonLogger.is_rage_active_cached():
                add_log("Не удалось включить: окно RAGE не активно", level="WARNING", page=self.page)
                return
            
            self.enabled = True
            self.press_all()
            add_log(f"[→] Движение ВКЛ ({'+'.join(self.keys)} зажаты)", page=self.page)
        else:
            self.force_disable()

    def press_all(self):
        for key in self.keys:
            try:
                pydirectinput.keyDown(key)
            except Exception as e:
                logger.error(f"Ошибка keyDown {key}: {e}")

    def release_all(self):
        for key in self.keys:
            try:
                pydirectinput.keyUp(key)
            except Exception as e:
                logger.error(f"Ошибка keyUp {key}: {e}")

    def force_disable(self):
        if self.enabled:
            self.release_all()
            self.enabled = False
            add_log(f"[■] Движение ВЫКЛ ({'+'.join(self.keys)} отпущены)", page=self.page)

    def update(self):
        if self.enabled and not CommonLogger.is_rage_active_cached():
            add_log("Окно потеряно, отключаю удержание клавиш", level="WARNING", page=self.page)
            self.force_disable()

class DetectionCache:
    def __init__(self, ttl: float = 0.1):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl
    
    def get(self, path: str) -> Optional[Any]:
        now = time.time()
        cached = self._cache.get(path)
        if cached:
            result, ts = cached
            if now - ts < self._ttl:
                return result
            del self._cache[path]
        return None
    
    def set(self, path: str, result: Any):
        if result is not None:
            self._cache[path] = (result, time.time())
    
    def clear(self):
        self._cache.clear()

def create_daemon_thread(target: Callable, args: tuple = (), name: str = None,on_error: Optional[Callable[[Exception], None]] = None) -> threading.Thread:
    def wrapper():
        try:
            target(*args)
        except Exception as e:
            if on_error:
                on_error(e)
            else:
                logger.error(f"Ошибка в потоке {name or target.__name__}: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True, name=name)
    return thread

class AutoEToggle:
    def __init__(self, page: str):
        self.enabled = False
        self.page = page
        self._last_hotkey = None

    def toggle(self):
        self.enabled = not self.enabled
        status = "включено" if self.enabled else "выключено"
        add_log(f"[⌨️] Автонажатие E {status}", page=self.page)

    def reset(self):
        self.enabled = False

    def register_hotkey(self, hotkey: str):
        if self._last_hotkey:
            hotkey_manager.unregister(self._last_hotkey)
        hotkey_manager.register(hotkey, self.toggle)
        self._last_hotkey = hotkey
        add_log(f"[⌨️] Хоткей '{hotkey.upper()}' зарегистрирован для автонажатия E", page=self.page)

    def unregister_hotkey(self):
        if self._last_hotkey:
            hotkey_manager.unregister(self._last_hotkey)
            add_log(f"[⌨️] Хоткей '{self._last_hotkey.upper()}' отключен", page=self.page)
            self._last_hotkey = None

def init_module(name: str, extra_fields: dict = None) -> dict:
    module = {
        "active": False,
        "settings": get_settings(name)
    }
    if extra_fields:
        module.update(extra_fields)
    state["modules"][name] = module
    return state["modules"][name]

class WalkerModule:
    def __init__(self, module_name: str, page: str = None, walker_keys: list = None):
        self.module_name = module_name
        self.page = page or module_name
        self.stop_event = threading.Event()
        self.walker = AutoHold(keys=walker_keys or ["shift", "w"], page=self.page)
        self._last_hotkey = None

    @property
    def data(self):
        return state["modules"][self.module_name]

    def toggle(self, worker_fn, worker_args=(), hotkey_setting="walker_hotkey", default_hotkey="f5"):
        data = self.data
        if not data["active"]:
            data["active"] = True
            self.stop_event.clear()

            if self._last_hotkey:
                hotkey_manager.unregister(self._last_hotkey)

            hotkey = data["settings"].get(hotkey_setting, default_hotkey)
            hotkey_manager.register(hotkey, self.walker.toggle)
            self._last_hotkey = hotkey

            create_daemon_thread(
                target=worker_fn, args=worker_args,
                name=f"{self.module_name}_worker"
            ).start()
        else:
            data["active"] = False
            self.stop_event.set()
            if self._last_hotkey:
                hotkey_manager.unregister(self._last_hotkey)
            self._last_hotkey = None

    def cleanup(self):
        self.walker.force_disable()
        self.data["active"] = False
        add_log(f">>> Модуль {self.module_name.capitalize()} остановлен", page=self.page)