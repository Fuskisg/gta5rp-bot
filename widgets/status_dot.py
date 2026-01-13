from PyQt5 import QtCore, QtGui, QtWidgets
from .theme import COLORS

class StatusPulseDot(QtWidgets.QWidget):
    def __init__(self, color=QtGui.QColor(COLORS["accent"])):
        super().__init__()
        self._radius = 18.0
        self._opacity = 0.35
        self._active = False
        self.color = QtGui.QColor(color)
        self.setFixedSize(35, 35)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.anim_radius = self._anim(b"haloRadius", 12.0, 22.0)
        self.anim_opacity = self._anim(b"haloOpacity", 0.50, 0.05)

    def _anim(self, prop, start, end):
        a = QtCore.QPropertyAnimation(self, prop)
        a.setDuration(1200)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        a.setLoopCount(-1)
        return a

    @QtCore.pyqtProperty(float)
    def haloRadius(self):
        return self._radius

    @haloRadius.setter
    def haloRadius(self, v):
        self._radius = v
        self.update()

    @QtCore.pyqtProperty(float)
    def haloOpacity(self):
        return self._opacity

    @haloOpacity.setter
    def haloOpacity(self, v):
        self._opacity = v
        self.update()

    def start(self):
        if self._active:
            return
        self._active = True
        self.anim_radius.start()
        self.anim_opacity.start()
        self.show()

    def stop(self):
        self._active = False
        self.anim_radius.stop()
        self.anim_opacity.stop()
        self.hide()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        center = self.rect().center()

        if self._active:
            halo_gradient = QtGui.QRadialGradient(center, self._radius)
            halo_color = QtGui.QColor(self.color)
            halo_color.setAlphaF(self._opacity)
            halo_gradient.setColorAt(0.0, halo_color)
            halo_gradient.setColorAt(1.0, QtCore.Qt.transparent)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(halo_gradient)
            painter.drawEllipse(center, self._radius, self._radius)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(center, 5, 5)