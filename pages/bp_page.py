import json
import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont
from widgets.common import SettingsManager

class GlassScrollBar(QtWidgets.QScrollBar):
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setStyleSheet("""
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 25);
                width: 20px;
                margin: 4px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(255,160,160),
                    stop:1 rgb(229,99,99)
                );
                min-height: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgb(255,160,160);
            }

            QScrollBar::add-line,
            QScrollBar::sub-line {
                height: 0px;
            }

            QScrollBar::add-page,
            QScrollBar::sub-page {
                background: none;
            }
        """)

DATA_FILE = "bp.json"

DEFAULT_TASKS = [
    ("Посетить любой сайт в браузере", 1, 2),
    ("Зайти в любой канал в Brawl", 1, 2),
    ("Поставить лайк любой анкете в Match", 1, 2),
    ("Прокрутить за DP серебрянный или золотой кейс", 10, 20),
    ("Кинуть мяч питомцу 15 раз", 2, 4),
    ("15 выполненных питомцем команд", 2, 4),
    ("Ставка в колесе удачи в казино (межсерверное колесо)", 3, 6),
    ("Проехать 1 станцию на метро", 2, 4),
    ("Поймать 20 рыб", 4, 8),
    ("Выполнить 2 квеста любых клубов", 4, 8),
    ("Починить деталь в автосервисе", 1, 2),
    ("Забросить 2 мяча в баскетболе", 1, 2),
    ("Забить 2 гола в футболе", 1, 2),
    ("Победить в армрестлинге", 1, 2),
    ("Победить в дартс", 1, 2),
    ("Забить 10 голов в волейболе", 1, 2),
    ("Поиграть 1 минуту в настольный теннис", 1, 2),
    ("Поиграть 1 минуту в большой теннис", 1, 2),
    ("Сыграть в мафию в казино", 3, 6),
    ("Сделать платеж по лизингу", 1, 2),
    ("Посадить траву в теплице", 4, 8),
    ("Запустить переработку обезболивающих в лаборатории", 4, 8),
    ("Принять участие в двух аирдропах", 2, 4),
    ("3 часа в онлайне (можно выполнять многократно за день)", 2, 4),
    ("Нули в казино", 2, 4),
    ("25 действий на стройке", 2, 4),
    ("25 действий в порту", 2, 4),
    ("25 действий в шахте", 2, 4),
    ("3 победы в Дэнс Баттлах", 2, 4),
    ("Заказ материалов для бизнеса вручную", 1, 2),
    ("20 подходов в тренажерном зале", 1, 2),
    ("Успешная тренировка в тире", 1, 2),
    ("10 посылок на почте", 1, 2),
    ("Арендовать киностудию", 2, 4),
    ("Купить лотерейный билет", 1, 2),
    ("Выиграть гонку в картинге", 1, 2),
    ("10 действий на ферме", 1, 2),
    ("Потушить 25 'огоньков' пожарным", 1, 2),
    ("Выкопать 1 сокровище (не мусор)", 1, 2),
    ("Проехать 1 уличную гонку", 1, 2),
    ("Выполнить 3 заказа дальнобойщиком", 2, 4),
    ("Два раза оплатить смену внешности у хирурга в EMS", 2, 4),
    ("Добавить 5 видео в кинотеатре", 1, 2),
    ("Выиграть 5 игр в тренировочном комплексе со ставкой (от 100$)", 1, 2),
    ("Выиграть 3 любых игры на арене со ставкой (от 100$)", 1, 2),
    ("2 круга на любом маршруте автобусника", 2, 4),
    ("5 раз снять 100% шкуру с животных", 2, 4),
]

class AnimatedLabel(QtWidgets.QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._color = 255
        self.setStyleSheet("color: rgb(255,255,255);")

    def get_color(self):
        return self._color

    def set_color(self, value):
        self._color = value
        r, g, b = 255, 160, 160
        self.setStyleSheet(
            f"color: rgb("
            f"{int(r * (1 - value / 255) + 255 * value / 255)},"
            f"{int(g * (1 - value / 255) + 255 * value / 255)},"
            f"{int(b * (1 - value / 255) + 255 * value / 255)});"
        )

    color = pyqtProperty(int, get_color, set_color)

def animate_bp(label: AnimatedLabel):
    anim = QPropertyAnimation(label, b"color", label)
    anim.setStartValue(0)
    anim.setEndValue(255)
    anim.setDuration(350)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()

class BpPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()

        self.vip_enabled = False
        self.server_x2 = False
        self.total_bp = 0
        self.task_checkboxes = []
        self.tasks_data = []

        self.init_styles()
        self.build_ui()
        self.load_state()
        self.update_total_bp()

    def init_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(26, 26, 30, 180);
                font-family: 'Inter';
            }

            QLabel {
                color: lightgray;
                font-size: 14px;
                background: none;
            }

            QLabel#title {
                color: white;
                font-size: 20px;
                font-weight: 700;
                background: none;
            }

            QLineEdit {
                padding: 8px 12px;
                border-radius: 10px; 
                background-color: rgba(40,40,50,180);
                color: white;
                border: 1px solid rgba(255,255,255,30);
            }

            QLineEdit:focus {
                border: 1px solid #e56363;
            }

            QCheckBox {
                color: #e0e0e0;
                padding: 6px;
                background: none;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 2px solid #777;
                background: transparent;
            }

            QCheckBox::indicator:checked {
                background-color: #e56363;
                border-color: #e56363;
            }

            QPushButton {
                background-color: rgba(229, 99, 99, 160);
                color: white;
                padding: 8px 20px;
                border-radius: 12px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: rgba(255, 130, 130, 200);
            }

            QPushButton:pressed {
                background-color: rgba(200, 70, 70, 220);
            }

        """)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("🏆 BP Tracker")
        title.setObjectName("title")
        layout.addWidget(title)

        top = QtWidgets.QHBoxLayout()

        self.total_label = AnimatedLabel("BP: 0")
        self.total_label.setFont(QFont("Inter", 20, QFont.Bold))
        self.total_label.setStyleSheet("background-color: rgba(50,50,65,200); border-radius:14px; padding:10px 18px;")
        top.addWidget(self.total_label)

        top.addStretch()

        self.x2_checkbox = QtWidgets.QCheckBox("x2 Сервер")
        self.x2_checkbox.stateChanged.connect(self.toggle_x2)
        self.x2_checkbox.setStyleSheet("font-size: 15px;")
        top.addWidget(self.x2_checkbox)

        self.vip_checkbox = QtWidgets.QCheckBox("Gold / Platinum VIP")
        self.vip_checkbox.stateChanged.connect(self.toggle_vip)
        self.vip_checkbox.setStyleSheet("font-size: 15px;")
        top.addWidget(self.vip_checkbox)

        layout.addLayout(top)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Поиск по заданиям...")
        self.search_input.textChanged.connect(self.filter_tasks)
        layout.addWidget(self.search_input)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBar(GlassScrollBar(self.scroll))
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        container = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(container)
        self.scroll_layout.setSpacing(6)

        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)

        bottom = QtWidgets.QHBoxLayout()

        add_btn = QtWidgets.QPushButton("Добавить")
        add_btn.clicked.connect(self.add_task_dialog)

        del_btn = QtWidgets.QPushButton("Удалить")
        del_btn.clicked.connect(self.delete_task_dialog)

        clear_btn = QtWidgets.QPushButton("Сбросить")
        clear_btn.clicked.connect(self.clear_checked)

        bottom.addWidget(add_btn)
        bottom.addWidget(del_btn)
        bottom.addStretch()
        bottom.addWidget(clear_btn)

        layout.addLayout(bottom)

    def add_task_checkbox(self, name, base, vip):
        cb = QtWidgets.QCheckBox(f"{name} ({base}/{vip} BP)")
        cb.stateChanged.connect(self.update_total_bp)
        self.scroll_layout.addWidget(cb)

        self.task_checkboxes.append((cb, base, vip))
        self.tasks_data.append({"name": name, "base": base, "vip": vip})

    def filter_tasks(self):
        q = self.search_input.text().lower()
        for (cb, _, _), task in zip(self.task_checkboxes, self.tasks_data):
            cb.setVisible(q in task["name"].lower())

    def toggle_vip(self):
        self.vip_enabled = self.vip_checkbox.isChecked()
        self.update_total_bp()

    def toggle_x2(self):
        self.server_x2 = self.x2_checkbox.isChecked()
        self.update_total_bp()

    def update_total_bp(self):
        total = 0
        for cb, base, vip in self.task_checkboxes:
            if cb.isChecked():
                amount = vip if self.vip_enabled else base
                if self.server_x2:
                    amount *= 2
                    
                total += amount

        self.total_bp = total
        self.total_label.setText(f"BP: {total}")
        animate_bp(self.total_label)
        self.save_state()

    def clear_checked(self):
        for cb, _, _ in self.task_checkboxes:
            cb.setChecked(False)

    def save_state(self):
        state = {
            "vip": self.vip_enabled,
            "server_x2": self.server_x2,
            "tasks": [
                {
                    "name": task["name"],
                    "base": task["base"],
                    "vip": task["vip"],
                    "checked": cb.isChecked()
                }
                for (cb, _, _), task in zip(self.task_checkboxes, self.tasks_data)
            ]
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self):
        if not os.path.exists(DATA_FILE):
            for name, base, vip in DEFAULT_TASKS:
                self.add_task_checkbox(name, base, vip)
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        self.vip_enabled = state.get("vip", False)
        self.vip_checkbox.setChecked(self.vip_enabled)

        self.server_x2 = state.get("server_x2", False)
        self.x2_checkbox.setChecked(self.server_x2)

        for task in state.get("tasks", []):
            self.add_task_checkbox(task["name"], task["base"], task["vip"])
            if task.get("checked"):
                self.task_checkboxes[-1][0].setChecked(True)

    def add_task_dialog(self):
        dialog = AddTaskDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        text, bp_text = dialog.get_data()
        if not text or "/" not in bp_text:
            return

        try:
            base, vip = map(int, bp_text.split("/"))
        except ValueError:
            return

        self.add_task_checkbox(text, base, vip)
        self.update_total_bp()
        self.save_state()

    def delete_task_dialog(self):
        if not self.tasks_data:
            return

        items = [task["name"] for task in self.tasks_data]

        dialog = DeleteTaskDialog(items, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        index = dialog.selected_index()

        cb, _, _ = self.task_checkboxes.pop(index)
        self.scroll_layout.removeWidget(cb)
        cb.deleteLater()

        self.tasks_data.pop(index)

        self.update_total_bp()
        self.save_state()

class AddTaskDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новое задание")
        self.setFixedWidth(300)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        layout = QtWidgets.QVBoxLayout(self)

        self.task_edit = QtWidgets.QLineEdit()
        self.task_edit.setPlaceholderText("Текст задания")

        self.bp_edit = QtWidgets.QLineEdit()
        self.bp_edit.setPlaceholderText("BP (base/vip), например 2/4")

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(QtWidgets.QLabel("Введите текст задания:"))
        layout.addWidget(self.task_edit)
        layout.addWidget(QtWidgets.QLabel("Введите BP:"))
        layout.addWidget(self.bp_edit)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_data(self):
        return self.task_edit.text().strip(), self.bp_edit.text().strip()
    
class DeleteTaskDialog(QtWidgets.QDialog):
    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Удалить задание")
        self.setFixedWidth(300)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        layout = QtWidgets.QVBoxLayout(self)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(tasks)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        layout.addWidget(QtWidgets.QLabel("Выберите задание:"))
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def selected_index(self):
        return self.combo.currentIndex()