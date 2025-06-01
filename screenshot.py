import cv2
import mediapipe as mp
import time
import numpy as np
import os
import sys
from PIL import ImageGrab
import subprocess

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Blink Detection Thresholds
BLINK_THRESHOLD = 0.2
CONSECUTIVE_FRAMES = 3
LOOKAWAY_TIME_LIMIT = 2.5  # seconds
SCREENSHOT_COOLDOWN = 2.0  # seconds between screenshots
SCREENSHOT_SAVE_PATH = "BlinkShots"  # Desired folder to save screenshots


# Function to calculate eye aspect ratio (EAR)
def calculate_eye_aspect_ratio(landmarks, eye_indices):
    vertical_1 = np.linalg.norm(np.array(landmarks[eye_indices[1]]) - np.array(landmarks[eye_indices[5]]))
    vertical_2 = np.linalg.norm(np.array(landmarks[eye_indices[2]]) - np.array(landmarks[eye_indices[4]]))
    horizontal = np.linalg.norm(np.array(landmarks[eye_indices[0]]) - np.array(landmarks[eye_indices[3]]))
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


# Function to capture screenshot using PIL
def capture_screenshot(save_dir=SCREENSHOT_SAVE_PATH):
    os.makedirs(save_dir, exist_ok=True)  # Create directory if not exists
    filename = os.path.join(save_dir, f"screenshot_{int(time.time())}.png")
    screenshot = ImageGrab.grab()
    screenshot.save(filename)
    print(f"✅ Screenshot saved: {filename}")
    return filename


# Apply dotted landmarks
def apply_dotted_mask(frame, landmarks):
    for x, y in landmarks:
        cv2.circle(frame, (x, y), 2, (255, 255, 0), -1)


# Flash effect
def flash_screen():
    flash = np.full((200, 400, 3), 255, dtype=np.uint8)
    cv2.imshow("📸 Screenshot Captured!", flash)
    cv2.waitKey(300)
    cv2.destroyWindow("📸 Screenshot Captured!")


# Main function
def main():
    cap = cv2.VideoCapture(0)
    blink_counter = 0
    last_face_time = time.time()
    last_screenshot_time = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            last_face_time = time.time()
            for face_landmarks in results.multi_face_landmarks:
                landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_landmarks.landmark]

                left_eye_indices = [33, 160, 158, 133, 153, 144]
                right_eye_indices = [362, 385, 387, 263, 373, 380]

                left_ear = calculate_eye_aspect_ratio(landmarks, left_eye_indices)
                right_ear = calculate_eye_aspect_ratio(landmarks, right_eye_indices)
                avg_ear = (left_ear + right_ear) / 2.0

                if avg_ear < BLINK_THRESHOLD:
                    blink_counter += 1
                else:
                    if blink_counter >= CONSECUTIVE_FRAMES:
                        current_time = time.time()
                        if current_time - last_screenshot_time >= SCREENSHOT_COOLDOWN:
                            capture_screenshot()  # Saves to BlinkShots/
                            flash_screen()
                            last_screenshot_time = current_time
                    blink_counter = 0

                apply_dotted_mask(frame, landmarks)

        else:
            if time.time() - last_face_time > LOOKAWAY_TIME_LIMIT:
                print("🔙 Face not detected — Going back to main menu...")
                cap.release()
                cv2.destroyAllWindows()
                try:
                    import mainUI
                except ImportError:
                    subprocess.run(['python', 'mainUI.py'])
                exit()

        # Centered vibrant instruction text
        instruction = "Blink to take Screenshot | Look Away to Exit"
        (text_width, _), _ = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        center_x = (frame.shape[1] - text_width) // 2
        cv2.rectangle(frame, (center_x - 10, 10), (center_x + text_width + 10, 60), (0, 0, 0), -1)
        cv2.putText(frame, instruction, (center_x, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)  # Vibrant Neon Cyan

        cv2.imshow("Neuro-Blink Screenshot (Timeout-2.5 Seconds)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
