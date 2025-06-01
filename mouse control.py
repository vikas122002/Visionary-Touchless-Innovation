import cv2
import mediapipe as mp
import pyautogui
from pynput.mouse import Controller, Button
import time
import os
import sys
import math
import subprocess

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mouse = Controller()
cap = cv2.VideoCapture(0)

HAND_TIMEOUT = 10
SWITCH_DELAY = 1
last_hand_time = time.time()
task_switcher_active = False
direction = None
direction_hold_start = None
scroll_sensitivity = 5

prev_mouse_x, prev_mouse_y = 0, 0
smoothing = 3

dragging = False
index_finger_hold_start = None
DOUBLE_CLICK_MAX_TIME = 0.4

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Unable to access camera.")
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        hand_detected = False
        hand_data = []
        current_time = time.time()

        if results.multi_hand_landmarks:
            hand_detected = True
            last_hand_time = current_time

            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]

                index_x, index_y = int(index.x * w), int(index.y * h)
                thumb_x, thumb_y = int(thumb.x * w), int(thumb.y * h)
                middle_x, middle_y = int(middle.x * w), int(middle.y * h)
                ring_x, ring_y = int(ring.x * w), int(ring.y * h)

                hand_data.append({
                    'index': (index_x, index_y),
                    'thumb': (thumb_x, thumb_y),
                    'middle': (middle_x, middle_y),
                    'ring': (ring_x, ring_y),
                    'raw': hand_landmarks
                })

            if len(hand_data) == 2:
                h1, h2 = hand_data
                tx1, ty1 = h1['thumb']
                tx2, ty2 = h2['thumb']
                ix1, iy1 = h1['index']
                ix2, iy2 = h2['index']

                thumb_distance = distance((tx1, ty1), (tx2, ty2))
                index_distance = distance((ix1, iy1), (ix2, iy2))
                center_x = (tx1 + tx2) // 2

                # 🧹 Minimize All Windows
                if thumb_distance > 150 and iy1 > ty1 and iy2 > ty2 and not task_switcher_active:
                    print("🧹 Minimizing All Windows – Show Desktop")
                    pyautogui.hotkey('win', 'd')
                    time.sleep(1)
                    continue

                # 🌀 Task Switcher
                if thumb_distance < 60:
                    if not task_switcher_active and direction_hold_start is None:
                        direction_hold_start = current_time
                    elif not task_switcher_active and current_time - direction_hold_start > 1:
                        print("🌀 Task Switcher Activated")
                        pyautogui.keyDown('alt')
                        pyautogui.press('tab')
                        task_switcher_active = True
                        direction = None
                        direction_hold_start = None
                    elif task_switcher_active:
                        if center_x < w // 3:
                            if direction != 'left':
                                direction = 'left'
                                direction_hold_start = current_time
                            elif current_time - direction_hold_start > SWITCH_DELAY:
                                print("⬅ Switching Left")
                                pyautogui.keyDown('shift')
                                pyautogui.press('tab')
                                pyautogui.keyUp('shift')
                                direction_hold_start = current_time
                        elif center_x > 2 * w // 3:
                            if direction != 'right':
                                direction = 'right'
                                direction_hold_start = current_time
                            elif current_time - direction_hold_start > SWITCH_DELAY:
                                print("➡ Switching Right")
                                pyautogui.press('tab')
                                direction_hold_start = current_time
                        else:
                            direction = None
                            direction_hold_start = None
                else:
                    if task_switcher_active:
                        print("✅ Task Selected, Exiting Task Switcher")
                        pyautogui.keyUp('alt')
                        task_switcher_active = False
                    direction_hold_start = None

                # 🖱️ Scroll with 2 hands
                if not task_switcher_active and thumb_distance > 60:
                    vertical_distance = abs(iy1 - iy2)
                    scroll_amount = int(vertical_distance / scroll_sensitivity)
                    if scroll_amount > 0:
                        if iy1 > iy2:
                            print("⬇ Scrolling Down")
                            mouse.scroll(0, -scroll_amount)
                        elif iy1 < iy2:
                            print("⬆ Scrolling Up")
                            mouse.scroll(0, scroll_amount)

                # 🖱️ Double Click and Drag Using Both Index Fingers
                if index_distance < 30:
                    if index_finger_hold_start is None:
                        index_finger_hold_start = current_time
                    else:
                        hold_duration = current_time - index_finger_hold_start
                        if not dragging and hold_duration >= 0.5:
                            print("🖱️ Drag Start")
                            mouse.press(Button.left)
                            dragging = True
                else:
                    if index_finger_hold_start:
                        hold_duration = current_time - index_finger_hold_start
                        if not dragging and hold_duration < 0.5:
                            print("🖱️ Double Click Triggered")
                            mouse.click(Button.left, 2)
                        elif dragging:
                            print("🖱️ Drag End")
                            mouse.release(Button.left)
                            dragging = False
                        index_finger_hold_start = None

            elif len(hand_data) == 1 and not task_switcher_active:
                data = hand_data[0]
                screen_w, screen_h = pyautogui.size()
                index_pos = data['index']

                target_x = index_pos[0] * screen_w // w
                target_y = index_pos[1] * screen_h // h
                smooth_x = prev_mouse_x + (target_x - prev_mouse_x) // smoothing
                smooth_y = prev_mouse_y + (target_y - prev_mouse_y) // smoothing
                mouse.position = (smooth_x, smooth_y)
                prev_mouse_x, prev_mouse_y = smooth_x, smooth_y

                # Left Click
                if distance(data['thumb'], data['index']) < 30:
                    mouse.click(Button.left, 1)

                # Right Click
                if distance(data['index'], data['middle']) < 30:
                    mouse.click(Button.right, 1)

                # If one hand disappears while dragging
                if dragging:
                    print("🖱️ Drag End (Hand Lost)")
                    mouse.release(Button.left)
                    dragging = False
                index_finger_hold_start = None

        # ⏱️ Auto Return
        if not hand_detected and (current_time - last_hand_time > HAND_TIMEOUT):
            print("🔙 No hand detected — Returning to mainUI.py")
            cap.release()
            cv2.destroyAllWindows()
            try:
                import mainUI
            except ImportError:
                subprocess.run(['python', 'mainUI.py'])
            exit()

        cv2.imshow("Neuro-Mouse Control Center (Timeout-10 Second)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()