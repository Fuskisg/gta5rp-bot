import time
import traceback
import os
import pyautogui
from pyautogui import ImageNotFoundException
import pygetwindow as gw
from typing import Optional, Union, Callable, Any, Dict, List
from PyQt5.QtCore import pyqtSignal, QRect
from PyQt5 import QtWidgets, QtCore,QtGui
from PyQt5.QtWidgets import QTextEdit
import keyboard
import json
import types
import ctypes
import cv2
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QGridLayout, QLabel, QGraphicsDropShadowEffect, QFrame
)
from widgets.switch_button import SwitchButton
import threading
import pydirectinput

def press(key: str):
    pydirectinput.PAUSE = 0 
    pydirectinput.FAILSAFE = False
    pydirectinput.press(key)

class Log:
    def __init__(self, log_target=None, log_file="logs.txt", do_write=False):
        self.log_target = log_target
        self.log_file = log_file
        self.do_write = do_write

    def __call__(self, message: str):
        timestamp = time.strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}"

        if self.do_write:
            try:
                with open(self.log_file, "a", encoding="utf-8") as fp:
                    fp.write(full_message + "\n")
            except OSError:
                pass

        if self.log_target:
            if hasattr(self.log_target, 'emit'):
                self.log_target.emit(message)
            elif isinstance(self.log_target, QTextEdit):
                self.log_target.append(full_message)
            elif callable(self.log_target):
                self.log_target(full_message)

class CommonLogger:
    _last_check = 0
    _last_result = False
    _was_missing = True

    _REPLACEMENTS = {
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
        "у": "y", "х": "x", "м": "m", "т": "t", "н": "h",
        "в": "b", "к": "k",
    }
    _stop = threading.Event()

    @staticmethod
    def safe_locate(path: str, confidence: float = 0.95,log_signal: Optional[Union[pyqtSignal, Callable]] = None) -> Any:
        try:
            return pyautogui.locateOnScreen(path, confidence=confidence)
        except ImageNotFoundException:
            return None
        except Exception as e:
            Log(f"[Ошибка] locate {os.path.basename(path)}: {traceback.format_exc()}",log_signal)
            return None

    @staticmethod
    def is_rage_active() -> bool:
        active = gw.getActiveWindow()
        if not active or not active.title:
            return False

        title = active.title.casefold()
        normalized = "".join(CommonLogger._REPLACEMENTS.get(c, c) for c in title)
        return "multi" in normalized

    @staticmethod
    def is_rage_active_cached(interval: float = 0.5) -> bool:
        now = time.time()
        if now - CommonLogger._last_check >= interval:
            CommonLogger._last_check = now
            CommonLogger._last_result = CommonLogger.is_rage_active()
        return CommonLogger._last_result

    @staticmethod
    def wait_for_rage(log: Optional[Callable[[str], None]] = None,auto_move: Optional[object] = None,sleep: float = 1.0,force_log: bool = False) -> bool:
        active = CommonLogger.is_rage_active_cached()

        if active:
            if CommonLogger._was_missing or force_log:
                if log:
                    log("Окно RAGE Multiplayer найдено. Скрипт активен.")
                CommonLogger._was_missing = False
            return True
        
        if auto_move:
            try:
                auto_move.force_disable()
            except Exception:
                pass

        if not CommonLogger._was_missing or force_log:
            if log:
                log("Окно RAGE Multiplayer не активно. Ожидание...")
            CommonLogger._was_missing = True

        CommonLogger._stop.wait(sleep)
        return False

    @staticmethod
    def reset_flags():
        CommonLogger._was_missing = True
        CommonLogger._last_check = 0
        CommonLogger._last_result = False
            
class ScriptController:
    @staticmethod
    def toggle_script(widget, worker_factory, log_output, extra_signals=None, status_signal=None, worker_args=None, worker_kwargs=None):
        checked = widget.switch.isChecked()
        if checked:
            log_output.clear()
            worker_args = worker_args or ()
            worker_kwargs = worker_kwargs or {}
            widget.worker = worker_factory(*worker_args, **worker_kwargs)

            ui_logger = Log(log_target=log_output, do_write=True)
            widget.worker.log_signal.connect(ui_logger)

            def stop(self):
                self.running = False
                if hasattr(self, "_stop"):
                    self._stop.set()
            widget.worker.stop = types.MethodType(stop, widget.worker)

            if extra_signals:
                for signal_name, slot in extra_signals.items():
                    signal = getattr(widget.worker, signal_name, None)
                    if signal:
                        signal.connect(slot)

            widget.worker.finished.connect(lambda: ui_logger("[■] Скрипт остановлен."))
            widget.worker.start()
        else:
            if widget.worker:
                widget.worker.stop()

        if status_signal:
            status_signal.emit(checked)

class SettingsSignals(QtCore.QObject):
    updated = QtCore.pyqtSignal()
settings_signals = SettingsSignals()

class SettingsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.filename = "settings.json"
            cls._instance.settings = {}
            cls._instance.load()
        return cls._instance

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = {}
        else:
            self.settings = {}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def get(self, section: str, key: str, default=None):
        return self.settings.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save()

    def save_group(self, section: str, values: dict):
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section].update(values)
        self.save()

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

def load_images(folder: str, mapping: Dict[str, str] = None, count: int = None, as_cv2: bool = False) -> Union[Dict[str, str], Dict[str, 'np.ndarray'], List[str]]:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(base, "assets", folder)

    if mapping:
        if as_cv2:
            result = {}
            for filename, key in mapping.items():
                img = cv2.imread(os.path.join(folder_path, filename), cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise FileNotFoundError(f"Файл {filename} не найден")
                result[key] = img[:, :, :3]
            return result
        else:
            return {os.path.join(folder_path, filename): value for filename, value in mapping.items()}

    if count:
        if as_cv2:
            result = []
            for i in range(1, count + 1):
                img = cv2.imread(os.path.join(folder_path, f"{i}.png"), cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise FileNotFoundError(f"Файл {i}.png не найден")
                result.append(img[:, :, :3])
            return result
        else:
            return [os.path.join(folder_path, f"{i}.png") for i in range(1, count + 1)]

    raise ValueError("mapping count")

class OverlayWindow(QWidget):
    def __init__(self, title="HUD", fields=None, f_keys=None, auto_monitor=True):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.fields = fields or {"Действий": 0}
        self.value_labels = {}

        self.setObjectName("root")
        self.setFixedSize(168, 78 + (len(self.fields) - 1) * 20)

        font_title = QFont("Arial", 12, QFont.Bold)
        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        font_f = QFont("Arial", 8)

        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(6)

        status_dot = QLabel()
        status_dot.setFixedSize(QSize(7, 7))
        status_dot.setObjectName("statusDot")

        title_label = QLabel(title)
        title_label.setFont(font_title)
        title_label.setObjectName("titleLabel")

        f_keys_label = QLabel(f_keys or "")
        f_keys_label.setFont(font_f)
        f_keys_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f_keys_label.setObjectName("fKeys")

        left_header = QHBoxLayout()
        left_header.addWidget(status_dot)
        left_header.addWidget(title_label)

        header_layout.addLayout(left_header)
        header_layout.addStretch(1)
        header_layout.addWidget(f_keys_label)

        self.data_container = QWidget()
        self.data_container.setObjectName("body")
        self.data_layout = QGridLayout(self.data_container)
        self.data_layout.setContentsMargins(10, 6, 10, 6)
        self.data_layout.setSpacing(2)

        for i, (label_text, value) in enumerate(self.fields.items()):
            self._create_row(i, label_text, value, font_labels, font_values)

        self.data_layout.setColumnStretch(0, 1)
        self.data_layout.setColumnStretch(1, 1)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setObjectName("separator")
        main.addWidget(sep)
        main.addWidget(self.data_container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet("""
            QWidget#root {
                background: transparent;
            }
            QWidget#header {
                background: rgba(0,0,0,0.38);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border: 1px solid rgba(255,255,255,0.06);
                border-bottom: none;
                color: white;
            }
            QWidget#body {
                background: rgba(24,24,24,0.70);
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border: 1px solid rgba(255,255,255,0.06);
                border-top: none;
                color: white;
            }
            QLabel#statusDot {
                background-color: #2EE279;
                border-radius: 3px;
            }
            QLabel#fKeys {
                color: rgba(255,255,255,0.55);
            }
            QLabel#titleLabel {
                color: white;
            }
            QFrame#separator {
                background: rgba(255,255,255,0.08);
                margin-left: 10px;
                margin-right: 10px;
            }
            QLabel#dimLabel {
                color: rgba(255,255,255,0.60);
            }
            QLabel#valueLabel {
                color: #2EE279;
                font-weight: 700;
            }
            QLabel {
                background: transparent;
            }
        """)

        self.move_to_bottom_right()
        self._hud_timer = None
        if auto_monitor:
            self.start_monitor()

    def _create_row(self, row_index, label_text, value, font_labels, font_values):
        label = QLabel(label_text)
        label.setFont(font_labels)
        label.setObjectName("dimLabel")

        value_label = QLabel(str(value))
        value_label.setFont(font_values)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setObjectName("valueLabel")

        self.data_layout.addWidget(label, row_index, 0)
        self.data_layout.addWidget(value_label, row_index, 1)
        self.value_labels[label_text] = value_label

    def add_field(self, label_text, value):
        if label_text in self.value_labels:
            self.value_labels[label_text].setText(str(value))
            return
        row = self.data_layout.rowCount()
        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        self._create_row(row, label_text, value, font_labels, font_values)
        self._resize()

    def remove_field(self, label_text):
        if label_text not in self.value_labels:
            return

        value_label = self.value_labels.pop(label_text)

        for i in reversed(range(self.data_layout.count())):
            item = self.data_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QLabel) and (w.text() == label_text or w == value_label):
                self.data_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()

        self.data_container.adjustSize()
        self._resize()
        self.data_container.repaint()
        self.repaint()
        QApplication.processEvents()


    def _resize(self):
        self.setFixedHeight(78 + (len(self.value_labels) - 1) * 20)

    def _rebuild_layout(self):
        while self.data_layout.count():
            item = self.data_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        font_labels = QFont("Arial", 10)
        font_values = QFont("Arial", 11, QFont.Bold)
        for i, (label_text, value_label) in enumerate(self.value_labels.items()):
            label = QLabel(label_text)
            label.setFont(font_labels)
            label.setObjectName("dimLabel")
            self.data_layout.addWidget(label, i, 0)
            self.data_layout.addWidget(value_label, i, 1)

    def update_values(self, **kwargs):
        for k, v in kwargs.items():
            if v is None:
                self.remove_field(k)
            else:
                if k in self.value_labels:
                    self.value_labels[k].setText(str(v))
                else:
                    self.add_field(k, v)


    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        x = geo.x() + geo.width() - self.width() - 10
        y = geo.y() + geo.height() - self.height() - 60
        self.move(x, y)

    def start_monitor(self):
        if self._hud_timer is not None:
            return
        self._hud_timer = QTimer(self)
        self._hud_timer.timeout.connect(self._check_game_focus)
        self._hud_timer.start(1000)

    def stop_monitor(self):
        if self._hud_timer is not None:
            self._hud_timer.stop()
            self._hud_timer = None
        self.close()

    def _check_game_focus(self):
        if CommonLogger.wait_for_rage():
            if not self.isVisible():
                self.show()
                self.move_to_bottom_right()
        else:
            if self.isVisible():
                self.close()

    def update_values_auto(self, **kwargs):
        self.update_values(**kwargs)

class ToolTipLabel(QtWidgets.QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent, QtCore.Qt.ToolTip)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.label = QtWidgets.QLabel(text, self)
        self.label.setStyleSheet("""
            background-color: rgba(40,40,45,0.9);
            color: white;
            padding: 6px 10px;
        """)
        self.label.adjustSize()
        self.setFixedSize(self.label.size())
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(200)
        self.hide()

    def showTooltip(self, pos: QtCore.QPoint):
        self.move(pos)
        self.show()
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def hideTooltip(self):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()
        self.opacity_anim.finished.connect(lambda: self.hide() if self.opacity_effect.opacity() == 0 else None)

class CheckWithTooltip(QtWidgets.QWidget):
    def __init__(self, text: str, tooltip_text: str = "", parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.Check = QtWidgets.QCheckBox(text, self)
        self.Check.setCursor(QtCore.Qt.PointingHandCursor)
        self.Check.setStyleSheet("""
            QCheckBox { color: white; font-size: 12px; }
            QCheckBox::indicator { width:15px; height:15px; border:1px solid #fff; border-radius:3px; background:transparent; }
            QCheckBox::indicator:checked { border:1px solid #0A84FF; background-color:#0A84FF; image: url(assets/check.png); }
        """)
        self.layout.addWidget(self.Check)
        self.layout.addStretch()

        self.tooltip = None
        if tooltip_text:
            self.tooltip = ToolTipLabel(tooltip_text)
            self.Check.installEventFilter(self)

    def eventFilter(self, source, event):
        if self.tooltip and source == self.Check:
            cursor_pos = QtGui.QCursor.pos()
            if event.type() == QtCore.QEvent.Enter:
                pos = self.Check.mapToGlobal(QtCore.QPoint(self.Check.width() + 10, 0))
                self.tooltip.showTooltip(pos)
            elif event.type() == QtCore.QEvent.Leave:
                if not self.Check.rect().contains(self.Check.mapFromGlobal(cursor_pos)):
                    self.tooltip.hideTooltip()
        return super().eventFilter(source, event)
    
    def setChecked(self, value: bool):
        self.Check.setChecked(value)

    def isChecked(self) -> bool:
        return self.Check.isChecked()

class CommonUI:
    @staticmethod
    def create_settings_group(title: str = "", spacing: int = 10, margins=(10, 10, 10, 10)):
        group = QtWidgets.QGroupBox(title)
        group.setAlignment(QtCore.Qt.AlignHCenter)
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                background: none;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #ffcc66;
            }
        """)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(spacing)
        layout.setContentsMargins(*margins)
        group.setLayout(layout)
        return group, layout


    @staticmethod
    def create_switch_header(label_text: str, icon: str = "", font_size: int = 18, switch: bool = True):
        layout = QtWidgets.QHBoxLayout()
        display_text = f"{icon} {label_text}".strip()
        label = QtWidgets.QLabel(display_text)
        style = f"color: white; font-size: {font_size}px; background: none;"
        if not switch:
            style += "margin-top: 5px; margin-bottom: 5px;"
        
        label.setStyleSheet(style)
        layout.addWidget(label)
        layout.addStretch()

        switch_widget = SwitchButton() if switch else None
        if switch_widget:
            layout.addWidget(switch_widget)

        return layout, switch_widget
    
    @staticmethod
    def create_counter(text="Счётчик: 0", font_size: int = 14):
        label = QtWidgets.QLabel(text)
        label.setStyleSheet(f"color: white; font-size: {font_size}px; background: none;")
        return label

    @staticmethod
    def create_combo(label_text: str, items: list[str]):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("color: white; font-size: 14px; background: none;")

        combo = QtWidgets.QComboBox()
        combo.addItems(items)
        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addStretch()
        return layout, combo

    @staticmethod
    def add_log_field(parent_layout):
        log_field = QtWidgets.QTextEdit()
        log_field.setReadOnly(True)
        log_field.setObjectName("logField")
        log_field.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        log_field.setMinimumHeight(100)
        parent_layout.addWidget(log_field)
        return log_field
    
    @staticmethod
    def _make_label(text: str, size: int) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(f"background:none;color:white;font-size:{size}px;")
        return lbl
    
    @staticmethod
    def create_slider_row(title: str, minimum: float, maximum: float, default: float, suffix: str = "сек", step: float = 0.1):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(5)
        factor = 1 / step 

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("color: white;")

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(int(minimum * factor))
        slider.setMaximum(int(maximum * factor))
        slider.setValue(int(default * factor))
        slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        value_label = QtWidgets.QLabel(f"{default:.2f} {suffix}")
        value_label.setStyleSheet("color: white;")

        def update_label(val):
            value_label.setText(f"{val / factor:.2f} {suffix}")

        slider.valueChanged.connect(update_label)

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)

        def get_value():
            return slider.value() / factor

        return layout, slider, get_value

    @staticmethod
    def create_hotkey_input(default="f5", description="— вкл/выкл"):
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hotkey_input = HotkeyLineEdit(default)
        hotkey_input.setFixedWidth(60)
        hotkey_input.setAlignment(QtCore.Qt.AlignCenter)
        hotkey_input.setStyleSheet("""
            background-color: #222;
            color: white;
            font-size: 12px;
            border-radius: 4px;
        """)

        label = QtWidgets.QLabel("Горячая клавиша:")
        desc = QtWidgets.QLabel(description)

        layout.addWidget(label)
        layout.addWidget(hotkey_input)
        layout.addWidget(desc)
        layout.addStretch()

        return layout, hotkey_input

class HotkeyManager:
    def __init__(self, hotkey: str, toggle_callback, log_signal=None):
        self.hotkey = hotkey.lower().strip()
        self._hotkey_id = None
        self._enabled = False
        self.log_signal = log_signal
        self.toggle_callback = toggle_callback
        self.log = Log(self.log_signal)

    def toggle(self):
        self._enabled = not self._enabled
        state = "включено" if self._enabled else "выключено"
        self.log(f"Хоткей: {state}")
        if self.toggle_callback:
            self.toggle_callback(self._enabled)

    def register(self):
        self.unregister()
        try:
            self._hotkey_id = keyboard.add_hotkey(self.hotkey, self.toggle)
            self.log(f"Хоткей '{self.hotkey}' зарегистрирован")
        except Exception as exc:
            self.log(f"Ошибка бинда '{self.hotkey}': {exc}")

    def unregister(self):
        if self._hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_id)
            except Exception:
                pass
            self._hotkey_id = None

    def set_hotkey(self, hotkey: str):
        self.hotkey = hotkey.lower().strip()
        self.register()

class HotkeyLineEdit(QtWidgets.QLineEdit):
    hotkeyChanged = QtCore.pyqtSignal(str)

    def __init__(self, default="", parent=None):
        super().__init__(default, parent)
        self.setReadOnly(True)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setFixedHeight(21)
        self._value = default
        self._waiting = False

        self.RU_TO_EN = {
            'й':'q','ц':'w','у':'e','к':'r','е':'t','н':'y','г':'u','ш':'i','щ':'o','з':'p','х':'[','ъ':']',
            'ф':'a','ы':'s','в':'d','а':'f','п':'g','р':'h','о':'j','л':'k','д':'l','ж':';','э':"'",
            'я':'z','ч':'x','с':'c','м':'v','и':'b','т':'n','ь':'m','б':',','ю':'.','ё':'`'
        }

    def focusInEvent(self, event):
        self._waiting = True
        self.setText("Нажмите")
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if self._waiting:
            self.setText(self._value)
        self._waiting = False
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if not self._waiting:
            return

        key = event.key()
        modifiers = event.modifiers()

        if key == QtCore.Qt.Key_Escape:
            self.clearFocus()
            return

        if key in (QtCore.Qt.Key_Control,QtCore.Qt.Key_Shift,QtCore.Qt.Key_Alt,QtCore.Qt.Key_Meta):
            return

        parts = []

        if modifiers & QtCore.Qt.ControlModifier:parts.append("ctrl")
        if modifiers & QtCore.Qt.AltModifier:parts.append("alt")
        if modifiers & QtCore.Qt.ShiftModifier:parts.append("shift")
        if modifiers & QtCore.Qt.MetaModifier:parts.append("win")

        key_name = self._key_to_string(key, event)
        if not key_name:
            return

        parts.append(key_name)
        hotkey = "+".join(parts)

        self._value = hotkey
        self.setText(hotkey)
        self._waiting = False
        self.clearFocus()

        self.hotkeyChanged.emit(hotkey)

    def _key_to_string(self, key, event):
        text = event.text()

        if text and text.isprintable() and not text.isspace():
            ch = text.lower()
            ch = self.RU_TO_EN.get(ch, ch)
            return ch

        special = {
            QtCore.Qt.Key_F1: "f1", QtCore.Qt.Key_F2: "f2",
            QtCore.Qt.Key_F3: "f3", QtCore.Qt.Key_F4: "f4",
            QtCore.Qt.Key_F5: "f5", QtCore.Qt.Key_F6: "f6",
            QtCore.Qt.Key_F7: "f7", QtCore.Qt.Key_F8: "f8",
            QtCore.Qt.Key_F9: "f9", QtCore.Qt.Key_F10: "f10",
            QtCore.Qt.Key_F11: "f11", QtCore.Qt.Key_F12: "f12",
            QtCore.Qt.Key_Space: "space",
            QtCore.Qt.Key_Tab: "tab",
            QtCore.Qt.Key_Return: "enter",
        }
        return special.get(key)

class AutoHold:
    def __init__(self, keys: list[str], logger: Callable[[str], None] | None = None):
        self.keys = keys
        self.enabled = False
        self.logger = logger

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.press()
            self._log(f"[→] Движение включено ({'+'.join(self.keys)} зажаты)")
        else:
            self.release()
            self._log(f"[■] Движение отключено ({'+'.join(self.keys)} отпущены)")

    def press(self):
        for key in self.keys:
            keyboard.press(key)

    def release(self):
        for key in self.keys:
            keyboard.release(key)

    def force_disable(self):
        if self.enabled:
            self.release()
            self.enabled = False
            self._log(f"[■] Движение отключено (принудительно)")

    def _log(self, text: str):
        if self.logger:
            self.logger(text)