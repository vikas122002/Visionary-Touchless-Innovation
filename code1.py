import tkinter as tk
from tkinter import ttk
import pyautogui
import multiprocessing
import pygetwindow as gw
import keyboard as kb
import time
import cv2
import mediapipe as mp
import subprocess

modifier_keys = {"Shift": False, "Ctrl": False, "Alt": False}
modifier_buttons = {}
win_key_press_time = None
button_map = {}

shift_map = {
    '`': '~', '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
    '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}

keys = [
    ['Esc', 'PrtSc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'Delete'],
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Back'],
    ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
    ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'Enter'],
    ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'Shift'],
    ['Ctrl', 'Win', 'Alt', 'Space', 'Voice', 'Alt', 'Win', 'Left', 'Down', 'Up', 'Right']
]

def is_caps_on():
    return kb.is_pressed('caps lock')

def press_key(k):
    global win_key_press_time
    k = k.strip()
    if k in modifier_keys:
        modifier_keys[k] = not modifier_keys[k]
        modifier_buttons[k].config(bg="deepskyblue" if modifier_keys[k] else "gray")
        return

    if k == "Win":
        if win_key_press_time and (time.time() - win_key_press_time) < 0.4:
            pyautogui.press('win')
            win_key_press_time = None
        else:
            win_key_press_time = time.time()
        return

    special_keys = {
        'Caps': 'caps lock', 'Back': 'backspace', 'Delete': 'delete',
        'Tab': 'tab', 'Enter': 'enter', 'Space': 'space',
        'Esc': 'esc', 'PrtSc': 'printscreen'
    }

    if k in special_keys:
        pyautogui.press(special_keys[k])
        return
    if k == 'Voice':
        multiprocessing.Process(target=voice_typing).start()
        return
    if k in ['Left', 'Right', 'Up', 'Down']:
        pyautogui.press(k.lower())
        return

    send_key = k
    if len(k) == 1:
        if modifier_keys['Shift']:
            send_key = shift_map.get(k, k.upper() if k.isalpha() else k)
        elif is_caps_on() and k.isalpha():
            send_key = k.upper()
        elif not is_caps_on() and k.isalpha():
            send_key = k.lower()

    mods = [mod.lower() for mod in modifier_keys if modifier_keys[mod]]
    if mods:
        pyautogui.hotkey(*mods, send_key.lower())
    else:
        pyautogui.write(send_key)

    if modifier_keys['Shift']:
        modifier_keys['Shift'] = False
        modifier_buttons['Shift'].config(bg="gray")

def voice_typing():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            print("Listening...")
            audio = recognizer.listen(source, timeout=10)
            text = recognizer.recognize_google(audio)
            pyautogui.typewrite(text + " ")
        except Exception as e:
            print("Voice typing error:", e)

def create_keyboard(root, frame):
    for row in keys:
        row_frame = tk.Frame(frame, bg="#e6f2ff")
        row_frame.pack(fill='x', pady=1)
        for key in row:
            display = " " * 4 if key == "Space" else key
            btn = tk.Button(
                row_frame,
                text=display,
                width=30 if key == "Space" else 5,
                height=2,
                command=lambda k=key: press_key(k),
                bg="#f4faff",
                fg="#000000",
                relief='flat',
                font=('Segoe UI', 9, 'bold'),
                highlightthickness=0,
                bd=0
            )
            btn.pack(side='left', padx=1, pady=1)
            button_map[key] = btn

            if key in modifier_keys or key == "Shift":
                modifier_buttons[key] = btn
                btn.config(bg="gray")

def camera_process(pipe_conn):
    mp_hands = mp.solutions.hands
    cap = cv2.VideoCapture(0)
    drag_start_time = None
    dragging = False
    with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                index_tip = hand_landmarks.landmark[8]
                thumb_tip = hand_landmarks.landmark[4]

                x, y = int(index_tip.x * 1920), int(index_tip.y * 1080)
                dist = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5

                pinch = dist < 0.05
                if y < 100 and pinch:
                    if drag_start_time is None:
                        drag_start_time = time.time()
                    elif time.time() - drag_start_time > 5:
                        dragging = True
                else:
                    drag_start_time = None

                pipe_conn.send((x, y, pinch, dragging))
            else:
                pipe_conn.send((None, None, False, False))
    cap.release()

def gui_process(pipe_conn):
    root = tk.Tk()
    root.title("Touchless Keyboard")
    root.geometry("1000x400+300+300")
    root.configure(bg='#e6f2ff')
    root.attributes('-topmost', True)

    keyboard_frame = ttk.Frame(root, padding=2)
    keyboard_frame.pack()

    create_keyboard(root, keyboard_frame)

    cursor = tk.Label(root, text='⬤', fg='red', bg='#e6f2ff', font=('Arial', 14))
    cursor.place(x=0, y=0)

    win_x, win_y = 300, 300
    no_hand_detected_time = None
    TIMEOUT_SECONDS = 10

    def poll_camera():
        nonlocal win_x, win_y, no_hand_detected_time
        try:
            while pipe_conn.poll():
                x, y, click, drag = pipe_conn.recv()
                if x is None:
                    if no_hand_detected_time is None:
                        no_hand_detected_time = time.time()
                    elif time.time() - no_hand_detected_time > TIMEOUT_SECONDS:
                        print("No hand detected for 10 seconds. Returning to mainUI...")
                        root.destroy()
                        subprocess.Popen(["python", "mainUI.py"])
                        return
                else:
                    no_hand_detected_time = None
                    cursor.place(x=x - root.winfo_x(), y=y - root.winfo_y())
                    if drag:
                        win_x, win_y = x - 200, y - 40
                        root.geometry(f"+{win_x}+{win_y}")
                    for key, btn in button_map.items():
                        bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                        bw, bh = btn.winfo_width(), btn.winfo_height()
                        if bx < x < bx + bw and by < y < by + bh:
                            if click:
                                press_key(key)
                            break
        except Exception as e:
            print("Poll error:", e)
        root.after(30, poll_camera)

    root.after(100, poll_camera)
    root.mainloop()

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    parent_conn, child_conn = multiprocessing.Pipe()
    cam_proc = multiprocessing.Process(target=camera_process, args=(child_conn,))
    cam_proc.start()

    gui_process(parent_conn)
    cam_proc.terminate()

