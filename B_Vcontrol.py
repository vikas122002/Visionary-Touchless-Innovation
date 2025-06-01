import cv2
import mediapipe as mp
import numpy as np
import math
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
import comtypes
import wmi
import os
import sys
import time
import subprocess

# Audio control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

# Brightness control
wmi_service = wmi.WMI(namespace='wmi')
brightness_ctrl = wmi_service.WmiMonitorBrightnessMethods()[0]

# MediaPipe hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Utility functions
def get_distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def map_to_percentage(dist, min_d=20, max_d=150):
    return int(np.interp(np.clip(dist, min_d, max_d), [min_d, max_d], [0, 100]))

cap = cv2.VideoCapture(0)
screen_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
screen_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
center_left = screen_width // 3
center_right = 2 * center_left

curr_volume, curr_brightness = 0, 0
last_seen = time.time()
timeout_sec = 5

COLOR_BG = (10, 10, 30)
COLOR_HUD = (80, 20, 40)
COLOR_VOLUME = (160, 40, 20)
COLOR_BRIGHT = (160, 40, 20)
FONT = cv2.FONT_HERSHEY_SIMPLEX

wave_phase_vol = 0
wave_phase_bright = 0

def draw_wave_fill(img, x, y, width, height, percent, color, phase):
    fill_height = int((percent / 100) * height)
    wave_img = np.zeros((height, width, 3), dtype=np.uint8)
    wave_color = np.array(color, dtype=np.uint8)

    for i in range(width):
        wave_y = int((math.sin((i / width * 2 * np.pi * 3) + phase) * 5) + (height - fill_height))
        cv2.line(wave_img, (i, height), (i, wave_y), wave_color.tolist(), 1)

    mask = wave_img.astype(bool)
    roi = img[y:y+height, x:x+width]
    roi[mask] = wave_img[mask]

    img[y:y+height, x:x+width] = roi
    return img

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    overlay = frame.copy()
    output = frame.copy()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame.shape

    hand_found = False
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        last_seen = time.time()
        for handLms in results.multi_hand_landmarks:
            index = handLms.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            thumb = handLms.landmark[mp_hands.HandLandmark.THUMB_TIP]

            x1, y1 = int(index.x * w), int(index.y * h)
            x2, y2 = int(thumb.x * w), int(thumb.y * h)

            dist = get_distance((x1, y1), (x2, y2))
            percent = map_to_percentage(dist)

            if x1 < center_left:
                curr_brightness = percent
                brightness_ctrl.WmiSetBrightness(curr_brightness, 0)
            elif x1 > center_right:
                curr_volume = percent
                volume.SetMasterVolumeLevelScalar(curr_volume / 100, None)

            # Smaller dots
            cv2.circle(overlay, (x1, y1), 10, COLOR_BRIGHT, -1)
            cv2.circle(overlay, (x2, y2), 10, COLOR_BRIGHT, -1)
            cv2.line(overlay, (x1, y1), (x2, y2), COLOR_HUD, 2)

            hand_found = True

    # Timeout check
    if not hand_found and time.time() - last_seen > timeout_sec:
        print("No hand detected. Returning to Main UI...")
        cap.release()
        cv2.destroyAllWindows()
        try:
            import mainUI
        except ImportError:
            subprocess.run(['python', 'mainUI.py'])
        exit()

    # UI Zones
    bar_top, bar_bottom = 100, 400
    bar_height = bar_bottom - bar_top
    bar_width = 60

    left_center_x = center_left // 2
    right_center_x = center_right + (w - center_right) // 2

    # Volume Bar
    vol_x = right_center_x - bar_width // 2
    overlay = draw_wave_fill(overlay, vol_x, bar_top, bar_width, bar_height, curr_volume, COLOR_VOLUME, wave_phase_vol)
    cv2.putText(overlay, f'{curr_volume}%', (vol_x + 5, 450), FONT, 0.6, COLOR_VOLUME, 2)
    cv2.putText(overlay, 'VOLUME', (vol_x - 10, 80), FONT, 0.6, COLOR_VOLUME, 2)

    # Brightness Bar
    bright_x = left_center_x - bar_width // 2
    overlay = draw_wave_fill(overlay, bright_x, bar_top, bar_width, bar_height, curr_brightness, COLOR_BRIGHT, wave_phase_bright)
    cv2.putText(overlay, f'{curr_brightness}%', (bright_x + 5, 450), FONT, 0.6, COLOR_BRIGHT, 2)
    cv2.putText(overlay, 'BRIGHTNESS', (bright_x - 20, 80), FONT, 0.6, COLOR_BRIGHT, 2)

    # UI zone lines
    cv2.line(overlay, (center_left, 0), (center_left, h), (30, 30, 60), 1)
    cv2.line(overlay, (center_right, 0), (center_right, h), (30, 30, 60), 1)

    # Instruction text (Center Top)
    instruction = "Try with Hand-Gesture (Pinch-in & Pinch-out)"
    text_size = cv2.getTextSize(instruction, FONT, 0.8, 2)[0]
    text_x = (w - text_size[0]) // 2
    cv2.putText(overlay, instruction, (text_x, 40), FONT, 0.8, (200, 50, 200), 2)

    # Blend final output
    cv2.addWeighted(overlay, 0.85, output, 0.15, 0, output)
    cv2.imshow("Neuro-TouchFree : Fingertip Brightness and Volume Control (Timeout- 5 Seconds)", output)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    wave_phase_vol += 0.2
    wave_phase_bright += 0.2

cap.release()
cv2.destroyAllWindows()
