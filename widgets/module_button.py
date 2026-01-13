from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia
from .theme import COLORS
from widgets.common import SettingsManager, settings_signals
from .status_dot import StatusPulseDot
import os
import sys
import time

def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

class ModuleButton(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()
    STATE_NORMAL = "normal"
    STATE_HOVER = "hover"
    STATE_PRESS = "press"

    def __init__(self,title: str,subtitle: str,emoji: str,right_indicator: StatusPulseDot,is_settings_button: bool = False):
        super().__init__()
        self.setObjectName("moduleCard")
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(73)
        self.setMinimumWidth(100)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.settings = SettingsManager()
        self.is_settings_button = is_settings_button

        self._active = False
        self._module_active = False
        self._indicator = right_indicator

        self.hover_sound_player = None
        self.click_sound_player = None
        self._last_hover_time = 0

        self._init_shadow()
        self._build_ui(title, subtitle, emoji)
        self._apply_style(self.STATE_NORMAL)

        self.update_sound_settings()
        settings_signals.updated.connect(self.update_sound_settings)

    def _build_ui(self, title: str, subtitle: str, emoji: str):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10) 
        layout.setSpacing(12)

        icon = QtWidgets.QLabel(emoji)
        icon.setFixedSize(36, 36)
        icon.setAlignment(QtCore.Qt.AlignCenter)
        icon.setStyleSheet("""
            QLabel {
                background-color: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                font-size: 18px;
            }
        """)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;")
        title_lbl.setWordWrap(True)
        title_lbl.setContentsMargins(0, 0, 0, 0)

        subtitle_lbl = QtWidgets.QLabel(subtitle)
        subtitle_lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        subtitle_lbl.setContentsMargins(0, 0, 0, 0)

        text_col = QtWidgets.QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)
        text_col.addWidget(title_lbl)
        text_col.addWidget(subtitle_lbl)

        text_widget = QtWidgets.QWidget()
        text_widget.setLayout(text_col)

        self.ind_holder = QtWidgets.QWidget()
        ind_layout = QtWidgets.QHBoxLayout(self.ind_holder)
        ind_layout.setContentsMargins(0, 0, 0, 0)
        ind_layout.addStretch()
        ind_layout.addWidget(self._indicator)
        self._indicator.hide()

        layout.addWidget(icon)
        layout.addWidget(text_widget, 1)
        layout.addWidget(self.ind_holder)
        
    def _apply_style(self, state: str):
        bg = {
            self.STATE_NORMAL: COLORS["surface"],
            self.STATE_HOVER: COLORS["surface_hover"],
            self.STATE_PRESS: COLORS["surface_press"],
        }[state]

        self.setStyleSheet(f"""
            QFrame#moduleCard {{
                background-color: {bg};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)

    def _init_shadow(self):
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(COLORS["shadow"])
        self.shadow.setBlurRadius(18)
        self.setGraphicsEffect(self.shadow)

        self.anim_shadow_on = QtCore.QPropertyAnimation(self.shadow, b"blurRadius", self)
        self.anim_shadow_on.setDuration(180)
        self.anim_shadow_on.setStartValue(18)
        self.anim_shadow_on.setEndValue(28)
        self.anim_shadow_on.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self.anim_shadow_off = QtCore.QPropertyAnimation(self.shadow, b"blurRadius", self)
        self.anim_shadow_off.setDuration(220)
        self.anim_shadow_off.setStartValue(28)
        self.anim_shadow_off.setEndValue(18)
        self.anim_shadow_off.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def _animate_shadow(self, hover: bool):
        self.anim_shadow_on.stop()
        self.anim_shadow_off.stop()
        (self.anim_shadow_on if hover else self.anim_shadow_off).start()

    def update_sound_settings(self):
        hover_state = self.settings.get("settings", "switch_hover", True)
        click_state = self.settings.get("settings", "switch_click", True)
        volume_hover = self.settings.get("settings", "volume_hover", 35)
        volume_click = self.settings.get("settings", "volume_click", 45)

        hover_path = resource_path(os.path.join("assets", "hover.wav"))
        click_path = resource_path(os.path.join("assets", "click.wav"))
        settings_click_path = resource_path(os.path.join("assets", "settings.wav"))

        if hover_state and os.path.exists(hover_path):
            if not self.hover_sound_player:
                self.hover_sound_player = QtMultimedia.QMediaPlayer(self)
                self.hover_sound_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(hover_path)))
            self.hover_sound_player.setVolume(int(volume_hover))
        else:
            self.hover_sound_player = None

        if click_state:
            sound = settings_click_path if self.is_settings_button else click_path
            if os.path.exists(sound):
                if not self.click_sound_player:
                    self.click_sound_player = QtMultimedia.QMediaPlayer(self)
                    self.click_sound_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(sound)))
                self.click_sound_player.setVolume(int(volume_click))
            else:
                self.click_sound_player = None
        else:
            self.click_sound_player = None

    def enterEvent(self, e: QtCore.QEvent):
        self._animate_shadow(True)
        self._apply_style(self.STATE_HOVER)

        now = time.time()
        if self.hover_sound_player and now - self._last_hover_time > 0.15:
            self._last_hover_time = now
            self.hover_sound_player.stop()
            self.hover_sound_player.play()

        super().enterEvent(e)

    def leaveEvent(self, e: QtCore.QEvent):
        self._animate_shadow(False)
        self._apply_style(self.STATE_NORMAL)
        super().leaveEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._apply_style(self.STATE_PRESS)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            if self.click_sound_player:
                self.click_sound_player.stop()
                self.click_sound_player.play()

            self.clicked.emit()

            self._apply_style(self.STATE_HOVER if self.rect().contains(e.pos()) else self.STATE_NORMAL)

        super().mouseReleaseEvent(e)

    def setActive(self, active: bool):
        self._active = active
        self._update_indicator()

    def setModuleActive(self, active: bool):
        self._module_active = active
        self._update_indicator()

    def _update_indicator(self):
        if self._module_active:
            self._indicator.show()
            self._indicator.start()
        else:
            self._indicator.hide()
            self._indicator.stop()
