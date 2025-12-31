from PyQt5 import QtWidgets, QtCore
from widgets.common import CommonLogger, ScriptController, load_images, CommonUI, SettingsManager, AutoHold
from pynput.keyboard import Controller
import time
import threading
import keyboard

from pynput import keyboard as pynput_keyboard, mouse as pynput_mouse
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController, Listener as KeyboardListener

class StroykaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Стройка | Шахта", "⛏️")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()
        hotkey_layout, self.hotkey_input = CommonUI.create_hotkey_input(default="f5", description="— вкл/выкл автонажатие Shift+W")
        self.counter = CommonUI.create_counter()

        settings_layout.addLayout(hotkey_layout)
        settings_layout.addWidget(self.counter)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)

    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("stroyka", "hotkey_stroyka", "f5"))

    def _save_settings(self):
        self.settings.save_group("stroyka", {
            "hotkey_stroyka": self.hotkey_input.text()
        })

    def handle_toggle(self):
        self._save_settings()
        worker_factory = lambda: StroykaWorker(self.hotkey_input.text())
        extra_signals = {
            "counter_signal": self._update_counter
        }
        ScriptController.toggle_script(
            widget=self,
            worker_factory=worker_factory,
            log_output=self.log_output,
            extra_signals=extra_signals
        )

    def _update_counter(self, value: int):
        self.counter.setText(f"Счётчик: {value}")

class StroykaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self, hotkey: str = "f5"):
        super().__init__()
        self.running = False
        self.count = 0
        self.current_actions = 0
        self.img_key = load_images("stroyka", mapping={
            "image1.png": {"code": 0x45},
            "image2.png": {"code": 0x89},
            "image3.png": {"code": 0x46},
            "image4.png": {"code": 0x48},
        })
        self._stop = threading.Event()
        self._shown = {p: False for p in self.img_key}
        self._visible = {p: False for p in self.img_key}
        self.keyboard_controller = Controller()
        self.detection_cache = {}
        self._toggle_requested = False
        self.auto_move = AutoHold(
            keys=["shift", "w"],
            logger=self.log
        )
        self.hotkey = hotkey or "f5"

        keyboard.add_hotkey(self.hotkey, lambda: setattr(self, "_toggle_requested", True))

    def log(self, message: str):
        self.log_signal.emit(message)

    def safe_locate(self, path: str, ttl=0.1):
        now = time.time()
        cached = self.detection_cache.get(path)
        if cached:
            result, ts = cached
            if now - ts < ttl:
                return result
        result = CommonLogger.safe_locate(path, 0.90, self.log_signal)

        if result is not None:
            self.detection_cache[path] = (result, now)

        return result

    def run(self):
        self.running = True
        self.log("Поиск начат.")
        try:
            while self.running:
                if not CommonLogger.wait_for_rage(log=self.log,auto_move=getattr(self, "auto_move", None)):
                    continue

                if self._toggle_requested and hasattr(self, "auto_move"):
                    self.auto_move.toggle()
                    self._toggle_requested = False

                for path, keys in self.img_key.items():
                    if self.safe_locate(path):
                        self._handle_visible_image(path, keys)
                        break

                self._stop.wait(0.01)

        except Exception as e:
            self.log(f"[Критическая ошибка]\n{str(e)}")

        finally:
            self.auto_move.force_disable()
            self.running = False

    def _handle_visible_image(self, path: str, keys: dict):
        if not self._visible[path]:
            self._visible[path] = True
            self._shown[path] = False
            self.count += 1
            self.counter_signal.emit(self.count)
            self.log(f"[✓] Найдено → спам '{keys['code']}'")
            self.current_actions = self.count

        press_count = 0
        while self.running and press_count < 60:
            #self.keyboard_controller.tap(keys['en'])
            #self.keyboard_controller.tap(keys['ru'])
            controller = KeyboardController()
            controller.press(pynput_keyboard.KeyCode.from_vk(keys['code']))  
            time.sleep(0.03)
            controller.release(pynput_keyboard.KeyCode.from_vk(keys['code']))
            press_count += 1
            if press_count % 5 == 0:
                self._stop.wait(0.001)

        if not self.safe_locate(path):
            self._visible[path] = False
            