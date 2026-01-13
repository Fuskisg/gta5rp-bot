from PyQt5 import QtWidgets, QtCore
import random
import threading
import os
import pyautogui
import keyboard
from typing import Optional, Tuple, Callable
import time
from widgets.common import CommonLogger, ScriptController, SettingsManager, CheckWithTooltip, CommonUI,Log
import vgamepad as vg

BASE_ASSETS_PATH = "assets/spin/"

class AntiAfkPage(QtWidgets.QWidget):
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

        header, self.switch = CommonUI.create_switch_header("Анти-АФК", "🕹️")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        min_delay_row, self.min_delay_slider, self.get_min_delay_slider = CommonUI.create_slider_row("Мин. время зажатие:", 0.5, 10, 0.5, step=0.1)
        max_delay_row, self.max_delay_slider, self.get_max_delay_slider = CommonUI.create_slider_row("Макс. время зажатие:", 0.5, 10, 2.5, step=0.1)
        settings_layout.addLayout(min_delay_row)
        settings_layout.addLayout(max_delay_row)

        min_pause_row, self.min_pause_slider, self.get_min_pause = CommonUI.create_slider_row("Мин. пауза между движениями:", 0.5, 10, 8)
        max_pause_row, self.max_pause_slider, self.get_max_pause = CommonUI.create_slider_row("Макс. пауза между движениями:", 0.5, 10, 10)
        settings_layout.addLayout(min_pause_row)
        settings_layout.addLayout(max_pause_row)

        self.checkwheel = CheckWithTooltip("Авто Колесо", "Раз в 5 мин.")
        settings_layout.addWidget(self.checkwheel)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)

    def _load_settings(self):
        self.min_delay_slider.setValue(self.settings.get("anti_afk", "min_delay", 5))
        self.max_delay_slider.setValue(self.settings.get("anti_afk", "max_delay", 25))
        self.min_pause_slider.setValue(self.settings.get("anti_afk", "min_pause", 80))
        self.max_pause_slider.setValue(self.settings.get("anti_afk", "max_pause", 100))
        self.checkwheel.setChecked(self.settings.get("anti_afk", "auto_wheel", False))

    def _save_settings(self):
        self.settings.save_group("anti_afk", {
            "min_delay": self.min_delay_slider.value(),
            "max_delay": self.max_delay_slider.value(),
            "min_pause": self.min_pause_slider.value(),
            "max_pause": self.max_pause_slider.value(),
            "auto_wheel": self.checkwheel.isChecked()
        })

    def handle_toggle(self):
        self._save_settings()
        def worker_factory():
            worker = AntiAfkWorker(
                self.min_delay_slider.value() / 10.0,
                self.max_delay_slider.value() / 10.0,
                self.min_pause_slider.value() / 10.0,
                self.max_pause_slider.value() / 10.0,
                self.checkwheel.isChecked(),
            )
            return worker

        ScriptController.toggle_script(
            widget=self,
            worker_factory=worker_factory,
            log_output=self.log_output,
            status_signal=self.statusChanged
        )
class AntiAfkWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, min_delay=1.0, max_delay=3.5, min_pause=0.5, max_pause=2.0, checkwheel=False):
        super().__init__()
        self.log = Log(self.log_signal)
        self.running = True
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.checkwheel = checkwheel
        self.gamepad = vg.VX360Gamepad()
        print("Создан gamepad с PID:", self.gamepad.get_pid())
        print("Создан gamepad с VID:", self.gamepad.get_vid())
        self.gamepad.reset()
        self.gamepad.update()
        self._stop = threading.Event()
        self.confidence = 0.85
        self.last_roulette_spin_time = time.time()

        self.DIRECTIONS = {
            'up': (0, 32767),
            'down': (0, -32767),
            'left': (-32767, 0),
            'right': (32767, 0),
            'up_right': (20000, 20000),
            'up_left': (-20000, 20000),
            'down_right': (20000, -20000),
            'down_left': (-20000, -20000),
            'center': (0, 0)
        }
        if self.checkwheel:
            self.roulette_thread = RouletteThread(interval=300)
            self.roulette_thread.trigger.connect(self.perform_roulette_spin)
        else:
            self.roulette_thread = None

    def close(self):
        if self.roulette_thread:
            self.roulette_thread.stop()
            self.roulette_thread.wait()
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass
            self.gamepad = None

    def click_image_in_region(self,image_filename: str,region: Optional[Tuple[int, int, int, int]] = None,confidence: float = 0.85,click: Optional[Callable[[int, int], None]] = pyautogui.click) -> bool:
        full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
        if not os.path.exists(full_image_path):
            print(f"Ошибка: Файл изображения '{full_image_path}' не найден.")
            return False
        try:
            location = pyautogui.locateOnScreen(full_image_path, region=region, confidence=confidence)

            if location:
                if click is not None:
                    center_x, center_y = pyautogui.center(location)
                    click(center_x, center_y)
                    print(f"Изображение '{image_filename}' найдено и был выполнен клик по координатам ({center_x}, {center_y}).")
                else:
                    print(f"Изображение '{image_filename}' найдено, но клик не выполнялся (click=None).")
                return True
            else:
                print(f"Изображение '{image_filename}' не найдено.")
                return False
        except Exception as e:
            return False

    def perform_roulette_spin(self):
        screen_width, screen_height = pyautogui.size()
        left_half_region = (0, 0, screen_width // 2, screen_height)
        right_half_region = (screen_width // 2, 0, screen_width // 2, screen_height)
        top_half_region = (0, 0, screen_width, screen_height // 2)
        bottom_half_region = (0, screen_height // 2, screen_width, screen_height // 2)

        pos = self.click_image_in_region("cols.jpg", region=top_half_region, click=None)
        if pos:
            self.log(f"[✓] Открываю телефон.")
            keyboard.press_and_release('up')
            self._stop.wait(2)

            if self.click_image_in_region("casinoIcon.png", region=right_half_region,confidence=0.55):
                self.log(f"[✓] Открыл казино.")
                self._stop.wait(2)
            else: 
                return

            if self.click_image_in_region('kasspin.jpg', region=left_half_region):
                self.log(f"[✓] Открываю колесо удачи.")
                self._stop.wait(2)
            else:
                return

            if self.click_image_in_region("spinbutton.jpg", region=bottom_half_region):
                self.log(f"[✓] Кручу.")
                self._stop.wait(3)
            else: 
                return

            self._stop.wait(0.5)
            keyboard.press_and_release('esc')
            self._stop.wait(0.5)
            keyboard.press_and_release('esc')
            self._stop.wait(0.5)
            keyboard.press_and_release('backspace')
        else:
            self.log("[→] пропускаем колесо")

    def run(self):
        self.log("[→] Скрипт анти-АФК запущен.")
        try:
            if self.roulette_thread:
                self.roulette_thread.start()
            self.gamepad.reset()
            self.gamepad.update()
            while self.running and not self._stop.is_set():
                direction = random.choice(list(self.DIRECTIONS.keys()))
                hold_time = random.uniform(self.min_delay, self.max_delay)
                pause_time = random.uniform(self.min_pause, self.max_pause)
                x, y = self.DIRECTIONS[direction]

                self.log(f"[•] Направление: {direction}, зажатие: {hold_time:.2f} сек.")
                self.gamepad.left_joystick(x_value=x, y_value=y)
                self.gamepad.update()

                if self._stop.wait(hold_time):
                    break

                self.gamepad.left_joystick(x_value=0, y_value=0)
                self.gamepad.update()

                self.log(f"[…] Пауза между: {pause_time:.2f} сек.")
                if self._stop.wait(pause_time):
                    break

        except Exception as e:
            self.log(f"[Ошибка] {e}")
        finally:
            try:
                self.gamepad.left_joystick(x_value=0, y_value=0)
                self.gamepad.update()
            except Exception:
                pass
            self.close()

class RouletteThread(QtCore.QThread):
    trigger = QtCore.pyqtSignal()

    def __init__(self, interval=10, parent=None):
        super().__init__(parent)
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.interval):
                break
            self.trigger.emit()

    def stop(self):
        self._stop_event.set()
