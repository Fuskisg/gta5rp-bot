from PyQt5 import QtWidgets, QtCore, QtGui

class SwitchButton(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._track_w = 53
        self._track_h = 24
        self._margin = 3
        
        self.setFixedSize(self._track_w + 10, self._track_h + 10)
        self._checked = False

        self._off_bg_grad_1 = QtGui.QColor(255, 255, 255, 30)
        self._off_bg_grad_2 = QtGui.QColor(0, 0, 0, 10)
        
        self._on_bg_grad_1 = QtGui.QColor("#d53369")
        self._on_bg_grad_2 = QtGui.QColor("#daae51")
        self._handle_color = QtGui.QColor(255, 255, 255, 200)

        self._anim_pos = 0.0
        self._anim_squish = 0.0

        self.animGroup = QtCore.QParallelAnimationGroup(self)

        self._pos_anim = QtCore.QPropertyAnimation(self, b"anim_pos", self)
        self._pos_anim.setDuration(350)
        self._pos_anim.setEasingCurve(QtCore.QEasingCurve.InOutBack)

        self._squish_anim = QtCore.QPropertyAnimation(self, b"anim_squish", self)
        self._squish_anim.setDuration(350)
        self._squish_anim.setKeyValues([(0.0, 0.0), (0.5, 0.15), (1.0, 0.0)]) 

        self.animGroup.addAnimation(self._pos_anim)
        self.animGroup.addAnimation(self._squish_anim)

        self.setCursor(QtCore.Qt.PointingHandCursor)

    @QtCore.pyqtProperty(float)
    def anim_pos(self): return self._anim_pos
    @anim_pos.setter
    def anim_pos(self, v):
        self._anim_pos = v
        self.update()

    @QtCore.pyqtProperty(float)
    def anim_squish(self): return self._anim_squish
    @anim_squish.setter
    def anim_squish(self, v):
        self._anim_squish = v
        self.update()

    def isChecked(self): return self._checked
    
    def setChecked(self, state):
        if self._checked == state: return
        self._checked = state
        self.animGroup.stop()
        self._pos_anim.setStartValue(self._anim_pos)
        self._pos_anim.setEndValue(1.0 if state else 0.0)
        self.animGroup.start()
        self.clicked.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        track_rect = QtCore.QRectF(5, 5, self._track_w, self._track_h)
        radius = self._track_h / 2.0

        p.save()
        bg_grad = QtGui.QLinearGradient(track_rect.topLeft(), track_rect.bottomRight())
        
        if self._anim_pos < 1.0:
            opacity_on = self._anim_pos
            c1 = self._lerp_color(self._off_bg_grad_1, self._on_bg_grad_1, opacity_on)
            c2 = self._lerp_color(self._off_bg_grad_2, self._on_bg_grad_2, opacity_on)
            bg_grad.setColorAt(0, c1)
            bg_grad.setColorAt(1, c2)
        else:
            bg_grad.setColorAt(0, self._on_bg_grad_1)
            bg_grad.setColorAt(1, self._on_bg_grad_2)

        path = QtGui.QPainterPath()
        path.addRoundedRect(track_rect, radius, radius)
        
        p.setBrush(bg_grad)
        p.setPen(QtCore.Qt.NoPen)
        p.drawPath(path)
        p.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 100), 1.5)
        p.setPen(pen)
        p.drawPath(path)
        p.restore()

        handle_h = self._track_h - (self._margin * 2)
        span = self._track_w - (self._margin * 2) - handle_h
        current_x = track_rect.x() + self._margin + (span * self._anim_pos)
        current_y = track_rect.y() + self._margin
        
        stretch_w = handle_h * self._anim_squish
        handle_rect = QtCore.QRectF(
            current_x - (stretch_w / 2), 
            current_y, 
            handle_h + stretch_w, 
            handle_h
        )

        p.save()
        
        shadow_path = QtGui.QPainterPath()
        shadow_path.addRoundedRect(handle_rect.translated(0, 3), handle_h/2, handle_h/2)
        p.setBrush(QtGui.QColor(0, 0, 0, 40))
        p.setPen(QtCore.Qt.NoPen)
        p.drawPath(shadow_path)

        glass_grad = QtGui.QLinearGradient(handle_rect.topLeft(), handle_rect.bottomRight())
        glass_grad.setColorAt(0, QtGui.QColor(255, 255, 255, 255))
        glass_grad.setColorAt(1, QtGui.QColor(230, 230, 255, 200))

        p.setBrush(glass_grad)
        
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
        p.drawRoundedRect(handle_rect, handle_h/2, handle_h/2)
        
        highlight_rect = handle_rect.adjusted(4, 2, -4, -handle_h/2)
        p.setBrush(QtGui.QColor(255, 255, 255, 120))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(highlight_rect, 4, 4)

        p.restore()

    def _lerp_color(self, c1, c2, t):
        r = c1.red() + (c2.red() - c1.red()) * t
        g = c1.green() + (c2.green() - c1.green()) * t
        b = c1.blue() + (c2.blue() - c1.blue()) * t
        a = c1.alpha() + (c2.alpha() - c1.alpha()) * t
        return QtGui.QColor(int(r), int(g), int(b), int(a))