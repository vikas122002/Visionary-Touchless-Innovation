import sys
import os
import random
import time
import math
import numpy as np
import datetime
import pyttsx3
import pywhatkit as kit
import wikipedia
import webbrowser
import smtplib
import pyjokes
import pyaudio
import speech_recognition as sr
import subprocess
from PyQt5 import QtWidgets, QtGui, QtCore

# ======= Assistant Functions ========
engine = pyttsx3.init('sapi5')
engine.setProperty('voice', engine.getProperty('voices')[0].id)

def speak(audio):
    engine.say(audio)
    engine.runAndWait()

def wishMe():
    hour = datetime.datetime.now().hour
    greeting = "Good Morning!" if hour < 12 else "Good Afternoon!" if hour < 18 else "Good Evening!"
    speak(greeting)
    speak("I am your Assistant Sir. Please tell me how may I help you")

def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=6)
        except sr.WaitTimeoutError:
            return "none"
    try:
        return r.recognize_google(audio, language='en-in').lower()
    except:
        return "none"

def performCommand(command):
    command = command.lower()

    try:
        if 'open notepad' in command:
            os.system('start notepad')
        elif 'open calculator' in command:
            os.system('start calc')
        elif 'open command prompt' in command:
            os.system('start cmd')
        elif 'open camera' in command:
            os.system('start microsoft.windows.camera:')
        elif 'open control panel' in command:
            os.system('control')
        elif 'open paint' in command:
            os.system('start mspaint')
        elif 'open vs code' in command:
            os.system("code")
        elif 'play music' in command:
            music_dir = 'C:\\Users\\YourName\\Music'
            songs = os.listdir(music_dir)
            os.startfile(os.path.join(music_dir, random.choice(songs)))
        elif 'time' in command:
            speak(f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}")
        elif 'joke' in command:
            speak(pyjokes.get_joke())
        elif 'wikipedia' in command:
            speak('Searching Wikipedia...')
            command = command.replace("wikipedia", "")
            results = wikipedia.summary(command, sentences=2)
            speak("According to Wikipedia")
            speak(results)
        elif 'open youtube' in command:
            webbrowser.open("https://youtube.com")
        elif 'open google' in command:
            speak("What should I search?")
            query = takeCommand()
            if query != "none":
                webbrowser.open(f"https://www.google.com/search?q={query}")
        elif 'shutdown' in command:
            os.system("shutdown /s /t 5")
        elif 'restart' in command:
            os.system("shutdown /r /t 5")
        elif 'sleep' in command:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif 'email' in command:
            speak("What should I say?")
            content = takeCommand()
            if content != "none":
                try:
                    to = "example@example.com"
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login('your_email@gmail.com', 'your_password')
                    server.sendmail('your_email@gmail.com', to, content)
                    server.quit()
                    speak("Email has been sent!")
                except:
                    speak("Sorry, I couldn't send the email.")
        elif 'no thanks' in command or 'you can sleep' in command:
            speak("Thanks for using me Sir, have a good day.")
            QtWidgets.QApplication.quit()
        else:
            speak("Searching online...")
            kit.search(command)
    except Exception as e:
        speak("Sorry, I encountered an issue.")

# ======= GUI Components ========
class CircularWaveform(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.display_data = np.zeros(1024)
        self.setStyleSheet("background-color: black;")
        self.setFixedSize(800, 600)
        self.threshold = 0.01
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.fade_to_silence)
        self.timer.start(30)

    def update_waveform(self, data):
        if np.max(np.abs(data)) > self.threshold:
            self.display_data = data
        else:
            self.display_data *= 0.9
        self.update()

    def fade_to_silence(self):
        self.display_data *= 0.95
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0))
        pen = QtGui.QPen(QtGui.QColor(0, 255, 255, 200), 2)
        painter.setPen(pen)
        center = self.rect().center()
        radius = 200
        angle_step = 360 / len(self.display_data)
        max_amp = np.max(np.abs(self.display_data)) or 1

        for i in range(len(self.display_data)):
            angle = angle_step * i
            amp = (self.display_data[i] / max_amp) * radius
            x = center.x() + amp * math.cos(math.radians(angle))
            y = center.y() + amp * math.sin(math.radians(angle))
            painter.drawLine(center, QtCore.QPointF(x, y))

        glow = QtGui.QRadialGradient(center, 30)
        glow.setColorAt(0, QtGui.QColor(0, 255, 255, 180))
        glow.setColorAt(1, QtGui.QColor(0, 255, 255, 30))
        painter.setBrush(QtGui.QBrush(glow))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(center, 30, 30)

class AudioListener(QtCore.QThread):
    def __init__(self, waveform_widget):
        super().__init__()
        self.waveform_widget = waveform_widget
        self.running = True

    def run(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
        while self.running:
            data = stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            normalized = np.clip(audio_data / 32768.0, -1, 1)
            self.waveform_widget.update_waveform(normalized)
        stream.stop_stream()
        stream.close()
        p.terminate()

    def stop(self):
        self.running = False

class VoiceCommandThread(QtCore.QThread):
    update_status = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._running = True

    def run(self):
        wishMe()
        last_voice_time = time.time()

        while self._running:
            self.update_status.emit("Listening...")
            query = takeCommand()
            now = time.time()
            if query != "none":
                last_voice_time = now
                self.update_status.emit(f"You said: {query}")
                performCommand(query)
            elif now - last_voice_time > 15:
                self.update_status.emit("Timeout reached. Returning to main UI.")
                speak("No voice detected. Returning to main user interface.")
                subprocess.run(['python', 'mainUI.py'])
                QtWidgets.QApplication.quit()
                break
            self.sleep(1)

    def stop(self):
        self._running = False
        self.terminate()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS - Voice Assistant")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: black;")

        self.waveform = CircularWaveform()
        self.setCentralWidget(self.waveform)

        self.label = QtWidgets.QLabel("Listening...", self)
        self.label.setStyleSheet("color: cyan; font-size: 20px;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(0, 540, 800, 40)

        self.audio_thread = AudioListener(self.waveform)
        self.audio_thread.start()

        self.voice_thread = VoiceCommandThread(self)
        self.voice_thread.update_status.connect(self.update_label)
        self.voice_thread.start()

    def update_label(self, text):
        self.label.setText(text)

    def closeEvent(self, event):
        self.audio_thread.stop()
        self.audio_thread.wait()
        self.voice_thread.stop()
        event.accept()

# ========= Run App =========
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
