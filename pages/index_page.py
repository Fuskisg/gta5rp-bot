import sys
import webbrowser
from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PyQt5.QtWidgets import QMessageBox
from widgets.common import SettingsManager

def load_icon(path, size=18):
    return QtGui.QPixmap(path).scaled(size, size,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)

def make_link_button(text, color, hover, icon=None, icon_size=18):
    btn = QtWidgets.QPushButton(text)
    btn.setCursor(QtCore.Qt.PointingHandCursor)

    if icon:
        if isinstance(icon, QtGui.QPixmap):
            btn.setIcon(QtGui.QIcon(icon))
        else:
            btn.setIcon(QtGui.QIcon(icon))
        btn.setIconSize(QtCore.QSize(icon_size, icon_size))

    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {color};
            font-size: 14px;
            text-decoration: underline;
            padding: 0;
            padding-left: 2px;
            text-align: left;
        }}
        QPushButton:hover {{
            color: {hover};
        }}
        QPushButton::icon {{
            margin-right: 6px;
        }}
    """)

    return btn

class HelpOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(parent.size())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.telegram_icon = load_icon("assets/tg.png")
        self.build_ui()
        self.run_animation()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        content_rect = QtCore.QRectF(self.rect()).adjusted(15, 15, -15, -15)
        path = QtGui.QPainterPath()
        path.addRoundedRect(content_rect, 18, 18)
        painter.setClipPath(path)
        painter.fillRect(content_rect, QtGui.QColor(0, 0, 0, 180))

    def build_ui(self):
        self.card = QtWidgets.QFrame(self)
        self.card.setFixedSize(400, 260)
        self.card.setStyleSheet("""
            QFrame {
                background: #0a0a0a;
                border: 1px solid #1c1c1c;
                border-radius: 20px;
            }
            QLabel {
                color: white;
                font-family: 'Segoe UI';
            }
        """)

        layout = QtWidgets.QVBoxLayout(self.card)
        layout.setContentsMargins(25, 20, 25, 25)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Поддержка")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#00ffcc;border:none")

        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background:#ff5f57;
                border-radius:14px;
                color:white;
                border:none;
            }
            QPushButton:hover { background:#ff7b73; }
        """)
        close_btn.clicked.connect(self.close)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        self.answer = QtWidgets.QLabel("Возможно, мешает NVIDIA Overlay / Game Filter или сторонние фильтры.")
        self.answer.setWordWrap(True)
        self.answer.setMaximumHeight(0)
        self.answer.setStyleSheet("color:#bbb;padding-left:20px;border:none")

        question = QtWidgets.QPushButton("❓ Бот не нажимает кнопки?")
        question.setCursor(QtCore.Qt.PointingHandCursor)
        question.setStyleSheet("""
            QPushButton {
                background:none;
                border:none;
                color:#00ffcc;
                font-weight:bold;
                text-align:left;
            }
            QPushButton:hover { color:white; }
        """)
        question.clicked.connect(self.toggle_answer)

        layout.addWidget(question)
        layout.addWidget(self.answer)
        layout.addStretch()

        row = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.telegram_icon)
        link = QtWidgets.QLabel(
            '<a href="https://t.me/id3001" '
            'style="color:#0088cc;text-decoration:none;">Telegram — <b>@id3001</b></a>'
        )
        link.setStyleSheet("border:none;")
        icon.setStyleSheet("border:none;")
        link.setOpenExternalLinks(True)

        row.addWidget(icon)
        row.addWidget(link)
        row.addStretch()
        layout.addLayout(row)

        self.center_card()

    def center_card(self):
        self.card.move((self.width() - self.card.width()) // 2,(self.height() - self.card.height()) // 2)

    def toggle_answer(self):
        expand = self.answer.maximumHeight() == 0
        anim = QPropertyAnimation(self.answer, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(self.answer.maximumHeight())
        anim.setEndValue(self.answer.sizeHint().height() if expand else 0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self.anim = anim

    def run_animation(self):
        opacity = QtWidgets.QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(opacity)

        fade = QPropertyAnimation(opacity, b"opacity")
        fade.setDuration(250)
        fade.setStartValue(0)
        fade.setEndValue(1)

        move = QPropertyAnimation(self.card, b"pos")
        move.setDuration(350)
        move.setStartValue(self.card.pos() + QtCore.QPoint(0, -500))
        move.setEndValue(self.card.pos())
        move.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(move)
        group.start()

class GradientLabel(QtWidgets.QWidget):
    def __init__(self, text, start_color, end_color, font_size=40, parent=None):
        super().__init__(parent)
        self.text = text
        self.start_color = QtGui.QColor(start_color)
        self.end_color = QtGui.QColor(end_color)
        self.font = QtGui.QFont("Arial", font_size, QtGui.QFont.Bold)
        metrics = QtGui.QFontMetrics(self.font)
        self.text_width = metrics.horizontalAdvance(self.text)
        self.text_height = metrics.height()
        self.setFixedSize(self.text_width , self.text_height )

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        gradient = QtGui.QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, self.start_color)
        gradient.setColorAt(1, self.end_color)
        path = QtGui.QPainterPath()
        metrics = QtGui.QFontMetrics(self.font)
        path.addText(0, metrics.ascent(), self.font, self.text)
        painter.fillPath(path, QtGui.QBrush(gradient))

class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.settings = SettingsManager()
        self.help_overlay = None
        self.telegram_icon = load_icon("assets/tg.png")
        self.support_icon = load_icon("assets/btn.png")

        self.net = QtNetwork.QNetworkAccessManager(self)
        self.net.finished.connect(self._on_response)

        self.init_styles()
        self.build_ui()
        self.load_online_count()

        if not self.settings.get("index", "link", False):
            self.show_first_launch_dialog()

    def init_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(26,26,30,180);
            }
            QLabel { color: lightgray; font-size: 14px; }
            QLabel#title {
                background: transparent;
                color:white;
                font-size:26px;
                font-weight:bold;
            }
            QLabel.small {
                font-size:12px;
                color:gray;
            }
            QLabel#text,QLabel#online {
                background: transparent;            
            }
        """)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("🏠 Главная", objectName="title")
        layout.addWidget(title)
        welcome_row = QtWidgets.QHBoxLayout()
        welcome_row.setSpacing(6)

        welcome_text_left = QtWidgets.QLabel("🎮 <b>Добро пожаловать в</b>",objectName="text")
        welcome_text_left.setTextFormat(QtCore.Qt.RichText)

        gradient_label = GradientLabel("BOT [GTA5RP]","#b859f3","#ddc2ed",font_size=10)

        welcome_text_right = QtWidgets.QLabel("<b>!</b>", objectName="text")
        welcome_text_right.setTextFormat(QtCore.Qt.RichText)

        welcome_row.addWidget(welcome_text_left)
        welcome_row.addWidget(gradient_label)
        welcome_row.addWidget(welcome_text_right)

        welcome_row.addStretch()

        layout.addLayout(welcome_row)
        text = QtWidgets.QLabel(
            "Этот мощный инструмент поможет вам <span style='color:#8d4bb9;'>автоматизировать рутину</span>"
            " в <b>GTA5RP</b> на платформе <b>RAGE Multiplayer</b>.<br><br>"
            "⚙️ <u>Ключевые фичи:</u><br>"
            "• Автоматизация повторяющихся задач<br>"
            "• Интуитивный и стильный интерфейс<br>"
            "• Полная кастомизация под ваш стиль игры<br>"
            "• Регулярные обновления и поддержка<br><br>"
            "📁 Перейдите в меню сверху и выберите модуль — и вперёд к доминации!<br><br>"
            "<span style='color: yellow;'>⚠️ <i>Внимание: использование может нарушать правила сервера. Играйте умно!</i></span>",
            objectName="text"
        )
        text.setWordWrap(True)
        text.setTextFormat(QtCore.Qt.RichText)
        layout.addWidget(text)
        layout.addStretch()

        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(8)

        btn_support = make_link_button("Поддержка", "#00ffcc", "#8FFFE8", icon=self.support_icon)
        btn_support.clicked.connect(self.show_help)

        btn_channel = make_link_button("Канал бота", "#FF0A0A", "#FF4D4D", icon=self.telegram_icon)
        btn_channel.clicked.connect(lambda: webbrowser.open("https://t.me/bot_gta5blast"))

        self.online_label = QtWidgets.QLabel("🌐 Запусков сегодня: ...")

        left_col.addWidget(btn_support)
        left_col.addWidget(btn_channel)
        left_col.addWidget(self.online_label)

        version_label = QtWidgets.QLabel(f"Версия: {self.version}")
        version_label.setProperty("class", "small")

        right_wrap = QtWidgets.QVBoxLayout()
        right_wrap.addStretch(1)
        right_wrap.addWidget(version_label, alignment=QtCore.Qt.AlignRight)
        right_wrap.addStretch(1)

        bottom_row.addLayout(left_col)
        bottom_row.addStretch(1)
        bottom_row.addLayout(right_wrap)

        layout.addLayout(bottom_row)

    def load_online_count(self):
        self.net.get(QtNetwork.QNetworkRequest(QUrl("https://purls.ru/online.php")))

    def _on_response(self, reply):
        if reply.error() == QtNetwork.QNetworkReply.NoError:
            data = reply.readAll().data().decode().strip()
            self.online_label.setText(f"🌐 Запусков сегодня: {data if data.isdigit() else 'ошибка данных'}")
        else:
            self.online_label.setText("🌐 Запусков сегодня: ошибка сети")
        reply.deleteLater()

    def show_help(self):
        if not self.help_overlay:
            self.help_overlay = HelpOverlay(self.window())
            self.help_overlay.destroyed.connect(lambda: setattr(self, "help_overlay", None))
            self.help_overlay.show()

    def show_first_launch_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("🔔 Внимание")
        msg.setText("У бота появился официальный Telegram-канал.\nПодпишитесь, чтобы не пропускать обновления.")
        open_btn = msg.addButton("Открыть ссылку", QMessageBox.AcceptRole)
        msg.addButton("Закрыть", QMessageBox.RejectRole)
        msg.exec_()

        if msg.clickedButton() == open_btn:
            webbrowser.open("https://t.me/bot_gta5blast")

        self.settings.save_group("index", {"link": True})