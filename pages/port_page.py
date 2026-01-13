from PyQt5 import QtWidgets, QtCore
import keyboard
import pyautogui
from pynput.keyboard import Controller
from widgets.common import CommonLogger, ScriptController, SettingsManager, auto_detect_region, CommonUI, AutoHold, Log, press
import threading

class PortPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: PortWorker | None = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Порт", "⚓")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        hotkey_layout, self.hotkey_input = CommonUI.create_hotkey_input(default="f5", description="— вкл/выкл автонажатие Shift+W")
        self.counter_label = CommonUI.create_counter()

        settings_layout.addLayout(hotkey_layout)
        settings_layout.addWidget(self.counter_label)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)

    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("port", "hotkey_port", "f5"))

    def _save_settings(self):
        self.settings.save_group("port", {
            "hotkey_port": self.hotkey_input.text()
        })

    def handle_toggle(self):
        self._save_settings()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: PortWorker(self.hotkey_input.text()),
            log_output=self.log_output,
            extra_signals={
                "counter_signal": self._update_counter
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class PortWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    GREEN = (126, 211, 33)
    RED = (231, 33, 57)
    TOLERANCE = 20
    STEP_X = 4
    STEP_Y = 10

    def __init__(self, hotkey: str = "f5"):
        super().__init__()
        self.log = Log(self.log_signal)
        self.running = True
        self._count = 0
        self._toggle_requested = False
        self.hotkey = hotkey or "f5"
        self.monitor = auto_detect_region()
        self._stop = threading.Event()
        self.auto_move = AutoHold(
            keys=["shift", "w"],
            logger=self.log
        )

        keyboard.add_hotkey(self.hotkey, lambda: setattr(self, "_toggle_requested", True))

    @staticmethod
    def _is_color_close(c1: tuple[int, int, int], c2: tuple[int, int, int], tol: int) -> bool:
        return all(abs(a - b) <= tol for a, b in zip(c1, c2))

    def run(self):
        self.log("[→] Скрипт порта запущен.")
        try:
            while self.running:
                if not CommonLogger.wait_for_rage(log=self.log,auto_move=getattr(self, "auto_move", None)):
                    continue

                if self._toggle_requested and hasattr(self, "auto_move"):
                    self.auto_move.toggle()
                    self._toggle_requested = False

                screenshot = pyautogui.screenshot(region=tuple(self.monitor.values()))
                pixels = screenshot.load()
                width, height = screenshot.size
                found = False

                for y in range(0, height, self.STEP_Y):
                    for x in range(0, width, self.STEP_X):
                        if self._is_color_close(pixels[x, y], self.RED, self.TOLERANCE):
                            for dx in range(-10, 11):
                                nx = x + dx
                                if 0 <= nx < width and self._is_color_close(pixels[nx, y], self.GREEN, self.TOLERANCE):
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break

                if found:
                    self._count += 1
                    self.log(f"[✓] Найдена мини-игра — нажимаем E (#{self._count})")
                    self.counter_signal.emit(self._count)
                    self.current_actions = self._count
                    press('e')
                    self._stop.wait(0.5)

                self._stop.wait(0.01)

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
            self.auto_move.force_disable()
