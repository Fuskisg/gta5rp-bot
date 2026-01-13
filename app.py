import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from widgets import COLORS, ModernWindow

class FocusRemover(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Tab:
                return True
            return False

        if event.type() not in (QtCore.QEvent.MouseButtonPress,QtCore.QEvent.MouseButtonRelease):
            return False

        focused = QtWidgets.QApplication.focusWidget()
        if not isinstance(focused, QtWidgets.QLineEdit):
            return False

        try:
            clicked = QtWidgets.QApplication.widgetAt(event.globalPos())
        except Exception:
            clicked = None

        w = clicked
        while w is not None:
            if w is focused:
                return False
            w = w.parent()

        focused.clearFocus()
        return False

def setup_palette(app: QtWidgets.QApplication):
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(COLORS["bg"]))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(COLORS["surface_hover"]))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(COLORS["surface"]))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(COLORS["text"]))
    palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    app.setPalette(palette)

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("BOT [GTA5RP]")
    app.setStyle("Fusion")

    setup_palette(app)
    
    font = app.font()
    font.setFamily("Helvetica")
    font.setPointSize(10)
    app.setFont(font)

    focus_remover = FocusRemover()
    app.installEventFilter(focus_remover)
    app._focus_remover = focus_remover

    window = ModernWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()