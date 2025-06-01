# 🚀 Visionary Touchless Innovation

**Visionary Touchless Innovation** is an advanced Human-Computer Interaction (HCI) project that enables users to control key system functions — such as brightness, volume, mouse, and screenshots — using hand gestures, facial recognition, and eye blinks, eliminating the need for physical contact.

This project is best run using **PyCharm** due to its reliable support for PyQt5, subprocesses, and environment management.

---

## 🧠 Features

- 🎮 **Hand Gesture Control** for system **volume** and **brightness**
- 🖱️ **Mouse Control** using finger tracking
- 🔐 **Face Unlock System** using OpenCV + encrypted password typing
- 📸 **Screenshot Capture** with **blink detection**
- 🧭 Custom PyQt5 GUI for launching modules
- 🔁 Smart return-to-mainUI on hand/face timeout

---

## 🖥️ Modules Overview

| Module            | Description                                             |
|-------------------|---------------------------------------------------------|
| `mainUI.py`       | Central PyQt5 launcher with hover animation & scripts  |
| `B_Vcontrol.py`   | Gesture-based Brightness & Volume control              |
| `mouse control.py`| Mouse pointer control + gesture-based scrolling        |
| `face_unlock.py`  | Facial recognition + secure password auto-typing       |
| `screenshot.py`   | Blink to capture screenshot and look-away to exit      |

---

## 🔧 How to Run

### 🧩 Requirements

Make sure Python is installed, then install dependencies:

```bash
pip install -r requirements.txt
