import sys
from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
from PyQt5.QtCore import QUrl, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve

GLOBAL_NETWORK_MANAGER = QtNetwork.QNetworkAccessManager()

class HelpOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.resize(parent.size())
        self.set_rounded_mask()
        self.telegram_icon_pixmap = QtGui.QPixmap("assets/tg.png").scaled(18, 18,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)

        pixmap = QtGui.QPixmap(parent.size())
        pixmap.fill(QtCore.Qt.transparent)
        parent.render(pixmap)
        small = pixmap.scaled(self.width()//4, self.height()//4, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
        self.final_bg = self.apply_blur(small, 8).scaled(self.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)

        self.build_ui()
        self.run_card_animation()

    def set_rounded_mask(self, radius=18, offset=15):
        path = QtGui.QPainterPath()
        inner_rect = QtCore.QRectF(self.rect()).marginsRemoved(QtCore.QMarginsF(offset, offset, offset, offset))
        
        path.addRoundedRect(inner_rect, radius, radius)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))

    def apply_blur(self, pixmap, radius):
        if pixmap.isNull():
            return pixmap
        blur = QtWidgets.QGraphicsBlurEffect()
        blur.setBlurRadius(radius)
        tmp_label = QtWidgets.QLabel()
        tmp_label.setPixmap(pixmap)
        tmp_label.setGraphicsEffect(blur)
        tmp_label.setAttribute(QtCore.Qt.WA_DontShowOnScreen)
        tmp_label.resize(pixmap.size())
        
        res = QtGui.QPixmap(pixmap.size())
        res.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(res)
        if painter.isActive():
            tmp_label.render(painter)
            painter.end()
        
        return res
    
    def paintEvent(self, event):
        if not hasattr(self, 'final_bg') or self.final_bg.isNull():
            return
            
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), 18, 18)
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self.final_bg)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 180))
        painter.end()

    def build_ui(self):
        self.card = QtWidgets.QFrame(self)
        self.card.setFixedSize(400, 260)
        self.card.setStyleSheet("""
            QFrame {
                background: #0a0a0a;
                border: 1px solid #1c1c1c;
                border-radius: 20px;
            }
            QLabel { color: white; background: transparent; font-family: 'Segoe UI', sans-serif; }
        """)

        layout = QtWidgets.QVBoxLayout(self.card)
        layout.setContentsMargins(25, 20, 25, 25)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Поддержка")
        title.setStyleSheet("font-weight: bold; font-size: 18px; color: #00ffcc; border:none;")
        
        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: #ff5f57; border-radius: 14px; color: white; font-weight: bold; border: none; }
            QPushButton:hover { background: #ff7b73; }
        """)
        close_btn.clicked.connect(self.close)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        self.qa_container = QtWidgets.QWidget()
        qa_layout = QtWidgets.QVBoxLayout(self.qa_container)
        qa_layout.setContentsMargins(0, 0, 0, 0)
        qa_layout.setSpacing(5)

        self.q_btn = QtWidgets.QPushButton("❓ Бот не нажимает кнопки?")
        self.q_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.q_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #00ffcc;
                font-size: 14px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover { color: white; }
        """)

        self.a_label = QtWidgets.QLabel("Возможно, мешает редукс или фильтры от видеокарты (NVIDIA Overlay / Game Filter).")
        self.a_label.setStyleSheet("color: #bbb; font-size: 13px; border: none; padding-left: 20px;")
        self.a_label.setWordWrap(True)
        self.a_label.setMaximumHeight(0)
        #self.a_label.setGraphicsEffect(QtWidgets.QGraphicsOpacityEffect())

        qa_layout.addWidget(self.q_btn)
        qa_layout.addWidget(self.a_label)
        
        layout.addWidget(self.qa_container)
        layout.addStretch(1)

        self.q_btn.clicked.connect(self.toggle_answer)

        telegram_row = QtWidgets.QHBoxLayout()
        telegram_icon = QtWidgets.QLabel()
        telegram_icon.setPixmap(self.telegram_icon_pixmap)
        telegram_row.addWidget(telegram_icon)
        telegram_link = QtWidgets.QLabel(
            '<a href="https://t.me/id3001" '
            'style="color:#0088cc; text-decoration:none; font-size:14px;">'
            'Telegram — <b>@id3001</b></a>'
        )
        telegram_link.setTextFormat(QtCore.Qt.RichText)
        telegram_link.setOpenExternalLinks(True)
        telegram_link.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        telegram_link.setStyleSheet("border:none;")
        telegram_icon.setStyleSheet("border:none;")
        telegram_link.setFocusPolicy(QtCore.Qt.NoFocus)
        telegram_row.addWidget(telegram_link, alignment=QtCore.Qt.AlignLeft)
        telegram_row.addStretch(1)
        layout.addLayout(telegram_row)
        layout.addStretch()

    def toggle_answer(self):
        self.a_label.setGraphicsEffect(None) 
        
        is_collapsed = self.a_label.maximumHeight() == 0
        target_height = self.a_label.sizeHint().height() if is_collapsed else 0
        
        self.anim_a = QPropertyAnimation(self.a_label, b"maximumHeight")
        self.anim_a.setDuration(300)
        self.anim_a.setStartValue(self.a_label.maximumHeight())
        self.anim_a.setEndValue(target_height)
        self.anim_a.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim_a.start()

    def run_card_animation(self):
        self.card_opacity = QtWidgets.QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(self.card_opacity)
        
        anim_fade = QPropertyAnimation(self.card_opacity, b"opacity")
        anim_fade.setDuration(250)
        anim_fade.setStartValue(0)
        anim_fade.setEndValue(1)

        center_pos = QtCore.QPoint((self.width()-self.card.width())//2, (self.height()-self.card.height())//2)
        start_pos = QtCore.QPoint(center_pos.x(), center_pos.y() - 40)
        
        self.card.move(start_pos)
        anim_move = QPropertyAnimation(self.card, b"pos")
        anim_move.setDuration(350)
        anim_move.setStartValue(start_pos)
        anim_move.setEndValue(center_pos)
        anim_move.setEasingCurve(QEasingCurve.OutCubic)

        self.group = QParallelAnimationGroup()
        self.group.addAnimation(anim_fade)
        self.group.addAnimation(anim_move)
        self.group.start()

class IndexPage(QtWidgets.QWidget):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.telegram_icon_pixmap = QtGui.QPixmap("assets/tg.png").scaled(18, 18,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
        self.btn_icon_pixmap = QtGui.QPixmap("assets/btn.png").scaled(18, 18,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
        self.help_overlay = None

        self.init_styles()
        self.build_ui()
        self.load_online_count()

    def init_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(26, 26, 30, 180);
                font-family: 'Inter', sans-serif;
            }

            QLabel {
                background: transparent;
                color: lightgray;
                font-size: 14px;
            }

            QLabel#title {
                color: white;
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 1px;
            }
                           
            QLabel.small {
                color: gray;
                font-size: 12px;
            }
        """)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("🏠 Главная")
        title.setObjectName("title")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "🎮 <b>Добро пожаловать в BOT [GTA5RP]!</b><br><br>"
            "Этот мощный инструмент поможет вам <span style='color:#00ffcc;'>автоматизировать рутину</span> "
            "в <b>GTA5RP</b> на платформе <b>RAGE Multiplayer</b>.<br><br>"
            "⚙️ <u>Ключевые фичи:</u><br>"
            "• Автоматизация повторяющихся задач<br>"
            "• Интуитивный и стильный интерфейс<br>"
            "• Полная кастомизация под ваш стиль игры<br>"
            "• Регулярные обновления и поддержка<br><br>"
            "📁 Перейдите в меню сверху и выберите модуль — и вперёд к доминации!<br><br>"
            "⚠️ <i>Внимание: использование может нарушать правила сервера. Играйте умно!</i><br><br>"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addStretch(1)

        bottom_container = QtWidgets.QHBoxLayout()

        left_container = QtWidgets.QVBoxLayout()
        left_container.setSpacing(8)

        btn_row = QtWidgets.QHBoxLayout()

        btn_icon = QtWidgets.QLabel()
        btn_icon.setPixmap(self.btn_icon_pixmap)
        btn_row.addWidget(btn_icon)

                
        btn = QtWidgets.QPushButton("Поддержка")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent; 
                border: none; 
                color: #00ffcc; 
                font-size: 14px; 
                text-decoration: underline;
                padding: 0px;
            }
            QPushButton:hover {
                color: #50ffdd;
            }
        """)
        btn.clicked.connect(self.show_help)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignCenter)
        btn_row.addWidget(btn, alignment=QtCore.Qt.AlignLeft)
        btn_row.addWidget(btn)

        left_container.addLayout(btn_row)

        self.online_label = QtWidgets.QLabel("🌐 Запусков сегодня: ...")
        left_container.addWidget(self.online_label)

        bottom_container.addLayout(left_container)
        bottom_container.addStretch(1)

        version_label = QtWidgets.QLabel(f"Версия: {self.version}")
        version_label.setProperty("class", "small")
        bottom_container.addWidget(version_label, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(bottom_container)

    def load_online_count(self):
        request = QtNetwork.QNetworkRequest(QUrl("https://purls.ru/online.php"))
        GLOBAL_NETWORK_MANAGER.finished.connect(self._on_response)
        GLOBAL_NETWORK_MANAGER.get(request)

    def _on_response(self, reply):
        if reply.error() == QtNetwork.QNetworkReply.NoError:
            data = reply.readAll().data().decode("utf-8").strip()
            if data.isdigit():
                self.online_label.setText(f"🌐 Запусков сегодня: {data}")
            else:
                self.online_label.setText("🌐 Запусков сегодня: ошибка данных")
        else:
            self.online_label.setText("🌐 Запусков сегодня: ошибка сети")

        reply.deleteLater()

    def show_help(self):
        if not self.help_overlay:
            self.help_overlay = HelpOverlay(self.window())
            self.help_overlay.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.help_overlay.destroyed.connect(self._clear_ref)
            self.help_overlay.show()

    def _clear_ref(self):
        self.help_overlay = None
