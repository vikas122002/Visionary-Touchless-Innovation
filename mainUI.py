import sys
import os
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QProcess, QTimer, QProcessEnvironment, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QGraphicsDropShadowEffect, QSizePolicy, QHBoxLayout
)

class HUDIcon(QWidget):
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.setWindowTitle("HUD Icon")
        self.setFixedSize(80, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.icon_button = QPushButton("🚀", self)
        self.icon_button.setGeometry(0, 0, 80, 80)
        self.icon_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 255, 100);
                border-radius: 40px;
                font-size: 28px;
                color: black;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 180);
            }
        """)
        self.offset = None
        self.dragging = False
        self.click_threshold = 5
        self.icon_button.installEventFilter(self)

    def restore_launcher(self):
        self.hide()
        self.launcher.show()

    def eventFilter(self, source, event):
        if source == self.icon_button:
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self.drag_start_pos = event.globalPos()
                self.offset = event.globalPos() - self.frameGeometry().topLeft()
                self.dragging = False
                return True
            elif event.type() == event.MouseMove and event.buttons() == Qt.LeftButton:
                if self.offset:
                    distance = (event.globalPos() - self.drag_start_pos).manhattanLength()
                    if distance > self.click_threshold:
                        self.dragging = True
                        self.move(event.globalPos() - self.offset)
                return True
            elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                if not self.dragging:
                    self.restore_launcher()
                self.offset = None
                self.dragging = False
                return True
        return super().eventFilter(source, event)


class HUDLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neuro-Touchless Accessibility Launcher")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.icon_window = HUDIcon(self)
        self.offset = None
        self.mouse_control_process = None
        self.script_processes = {}
        self.inactive_timer = QTimer()
        self.inactive_timer.setInterval(5000)
        self.inactive_timer.timeout.connect(self.auto_restart_mouse_control)

        self.init_ui()
        self.start_mouse_control()

    def init_ui(self):
        self.resize(500, 600)
        self.frame = QWidget(self)
        self.frame.setStyleSheet("""
            background-color: rgba(20, 20, 30, 160);
            border-radius: 30px;
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 255, 255, 180))
        shadow.setOffset(0, 0)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(20)

        self.title = QLabel("🚀 Neuro-Touchless Launcher")
        self.title.setFont(QFont("Orbitron", 20, QFont.Bold))
        self.title.setStyleSheet("color: #00ffff;")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(10)

        self.switch_button = QPushButton()
        self.switch_button.setCheckable(True)
        self.switch_button.setFixedSize(60, 30)
        self.switch_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border-radius: 15px;
            }
            QPushButton:checked {
                background-color: #00ffff;
            }
            QPushButton::indicator {
                width: 28px;
                height: 28px;
                border-radius: 14px;
                background: white;
                margin: 1px;
            }
        """)
        self.switch_button.clicked.connect(self.toggle_mouse_control)

        switch_label = QLabel("🖱️ Mouse Control")
        switch_label.setStyleSheet("color: white; font-size: 14px;")
        switch_label.setFont(QFont("Segoe UI", 10))

        switch_layout.addWidget(self.switch_button)
        switch_layout.addWidget(switch_label)
        layout.addLayout(switch_layout)

        self.buttons = [
            ("⌨️ Keyboard", "code1.py"),
            ("⚡⚡ Screenshot", "screenshot.py"),
            ("🎤 Voice Control", "voice_control.py"),
            ("🔅 Volume & Brightness", "B_Vcontrol.py"),
            ("🔒 Lock System", "face_lock.py"),
            ("↘ Minimize", None),
            ("❌ Exit", None),
        ]

        self.anim_buttons = []

        for text, script in self.buttons:
            btn = self.create_button(text, self.handle_button(script, text))
            layout.addWidget(btn)
            self.anim_buttons.append(btn)

        self.frame.setLayout(layout)
        self.show_animation()

    def toggle_mouse_control(self):
        if self.switch_button.isChecked():
            self.start_mouse_control()
        else:
            self.stop_mouse_control()

    def start_mouse_control(self):
        if self.mouse_control_process is None:
            self.mouse_control_process = QProcess(self)
            self.mouse_control_process.setProgram(sys.executable)
            self.mouse_control_process.setArguments(["mouse control.py"])
            self.mouse_control_process.setProcessChannelMode(QProcess.MergedChannels)

            # ✅ Connect finished signal to handler to update toggle
            self.mouse_control_process.finished.connect(self.on_mouse_control_finished)

            self.mouse_control_process.start()
            self.switch_button.setChecked(True)
            self.inactive_timer.stop()

    def stop_mouse_control(self):
        if self.mouse_control_process:
            self.mouse_control_process.kill()
            self.mouse_control_process.waitForFinished()
            self.mouse_control_process = None
            self.switch_button.setChecked(False)
            self.inactive_timer.start()

    @pyqtSlot()
    def on_mouse_control_finished(self):
        # ✅ Reset state if mouse control crashes or finishes
        self.mouse_control_process = None
        self.switch_button.setChecked(False)
        self.inactive_timer.start()

    def auto_restart_mouse_control(self):
        if not any(p.state() != QProcess.NotRunning for p in self.script_processes.values()):
            self.start_mouse_control()

    def create_button(self, text, callback):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet("""
            QPushButton {
                color: white;
                border: 2px solid #00ffff;
                border-radius: 15px;
                background-color: rgba(0, 0, 0, 100);
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 60);
                color: #00ffff;
                font-size: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 255, 255, 160))
        shadow.setOffset(0, 0)
        btn.setGraphicsEffect(shadow)
        btn.clicked.connect(callback)
        return btn

    def handle_button(self, script_name, label):
        def inner():
            if label == "↘ Minimize":
                self.minimize_to_icon()
            elif label == "❌ Exit":
                self.stop_mouse_control()
                sys.exit()
            elif script_name:
                self.stop_mouse_control()
                self.run_script(script_name)
        return inner

    def run_script(self, filename):
        if filename in self.script_processes:
            proc = self.script_processes[filename]
            if proc.state() != QProcess.NotRunning:
                proc.kill()
                proc.waitForFinished()
            del self.script_processes[filename]

        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments([filename])
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.finished.connect(lambda: self.on_script_finished(filename))
        self.script_processes[filename] = process
        process.start()
        self.minimize_to_icon()

    def on_script_finished(self, filename):
        if filename in self.script_processes:
            self.script_processes[filename].deleteLater()
            del self.script_processes[filename]
        if not any(p.state() != QProcess.NotRunning for p in self.script_processes.values()):
            self.start_mouse_control()
            self.restore_launcher()

    def minimize_to_icon(self):
        self.hide()
        launcher_pos = self.pos()
        self.icon_window.move(launcher_pos.x() + 500, launcher_pos.y() + 450)
        self.icon_window.show()

    def restore_launcher(self):
        self.show()
        self.icon_window.hide()

    def show_animation(self):
        for i, btn in enumerate(self.anim_buttons):
            anim = QPropertyAnimation(btn, b"geometry")
            anim.setDuration(250)
            anim.setStartValue(QRect(btn.x(), btn.y() + 20, btn.width(), btn.height()))
            anim.setEndValue(QRect(btn.x(), btn.y(), btn.width(), btn.height()))
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()

    def resizeEvent(self, event):
        self.frame.setGeometry(0, 0, self.width(), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(0, 255, 255, 100))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 30, 30)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


if __name__ == "__main__":
    os.environ["PYTHONUNBUFFERED"] = "1"
    app = QApplication(sys.argv)
    launcher = HUDLauncher()
    launcher.show()
    sys.exit(app.exec_())
