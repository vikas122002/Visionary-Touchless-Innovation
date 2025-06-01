import cv2, os, time, ctypes, numpy as np
from cryptography.fernet import Fernet

# Hide console window (for Windows)
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ─── CONFIG ────────────────────────────────────────────────────────────
USER_ID = 1
DATA_DIR = "face_data"
MODEL_PATH = "face_model.yml"
PASSWORD_PATH = "enc_password.bin"
KEY_PATH = "key.bin"
CAPTURES = 20
MAX_ATTEMPTS = 5
THRESHOLD = 50
# ───────────────────────────────────────────────────────────────────────

os.makedirs(DATA_DIR, exist_ok=True)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
recognizer = cv2.face.LBPHFaceRecognizer_create()

# ─── Windows Keyboard Input Setup ──────────────────────────────────────
PUL = ctypes.POINTER(ctypes.c_ulong)

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT)]

SendInput = ctypes.windll.user32.SendInput
KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, INPUT_KEYBOARD = 0x0004, 0x0002, 1

def _press_unicode(code: int, up=False):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    inp = INPUT(type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(0, code, flags, 0, None))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def type_password(text: str):
    ctypes.windll.user32.SetForegroundWindow(ctypes.windll.user32.GetForegroundWindow())
    for ch in text:
        _press_unicode(ord(ch))
        _press_unicode(ord(ch), up=True)
        time.sleep(0.01)
    _press_unicode(0x0D)  # Press Enter
    _press_unicode(0x0D, up=True)

# ─── Password Management ───────────────────────────────────────────────
def encrypt_password():
    key = Fernet.generate_key()
    cipher = Fernet(key)
    password = input("Enter your system password: ").strip()
    encrypted = cipher.encrypt(password.encode())
    with open(KEY_PATH, 'wb') as f:
        f.write(key)
    with open(PASSWORD_PATH, 'wb') as f:
        f.write(encrypted)
    print("[🔐] Password encrypted and saved.")

def load_password():
    if not os.path.exists(KEY_PATH) or not os.path.exists(PASSWORD_PATH):
        encrypt_password()
    key = open(KEY_PATH, 'rb').read()
    cipher = Fernet(key)
    enc_pass = open(PASSWORD_PATH, 'rb').read()
    return cipher.decrypt(enc_pass).decode()

# ─── Register and Train Owner Face ─────────────────────────────────────
def register_owner():
    if os.path.exists(MODEL_PATH):
        print("[ℹ️] Owner already registered. Delete model to re-register.")
        return

    if not os.path.exists(KEY_PATH) or not os.path.exists(PASSWORD_PATH):
        encrypt_password()

    cap = cv2.VideoCapture(0)
    count = 0
    print("[📸] Look at the camera to register…")

    while count < CAPTURES:
        ok, frame = cap.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for x, y, w, h in faces:
            count += 1
            face_img = gray[y:y + h, x:x + w]
            filename = f"{DATA_DIR}/user.{USER_ID}.{count}.jpg"
            cv2.imwrite(filename, face_img)
            print(f"[📸] Captured image {count}/{CAPTURES}")
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            time.sleep(0.25)

    cap.release()
    cv2.destroyAllWindows()
    train_model()

def train_model():
    print("[🧠] Training model...")
    faces, labels = [], []
    for file in os.listdir(DATA_DIR):
        if file.endswith(".jpg"):
            path = os.path.join(DATA_DIR, file)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            faces.append(img)
            labels.append(USER_ID)
    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_PATH)
    print("[✅] Model trained and saved.")

# ─── Unlock Logic ─────────────────────────────────────────────────────
def unlock():
    print("[🔓] Owner recognised – unlocking…")
    password = load_password()
    print("[🪪] Typing password...")
    time.sleep(0.5)
    type_password(password)
    print("[✔️] Password typed. Exiting.")
    os._exit(0)

def recognise_owner():
    if not os.path.exists(MODEL_PATH):
        print("[❗] No face model found. Please register first.")
        register_owner()

    recognizer.read(MODEL_PATH)
    cap = cv2.VideoCapture(0)
    attempts = 0
    print("[🔒] Looking for the owner...")

    while attempts < MAX_ATTEMPTS:
        ok, frame = cap.read()
        if not ok: continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for x, y, w, h in faces:
            roi = gray[y:y + h, x:x + w]
            label, conf = recognizer.predict(roi)
            print(f"[⚠️] Detected face — Confidence: {conf:.2f}")

            if label == USER_ID and conf < THRESHOLD:
                unlock()
                cap.release()
                return
            else:
                attempts += 1
                print(f"[❌] Unauthorized face. Attempt {attempts}/{MAX_ATTEMPTS}")

        if cv2.waitKey(1) == 27: break

    cap.release()
    cv2.destroyAllWindows()
    print("[⛔] Access Denied.")

# ─── Entry Point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        register_owner()
    else:
        recognise_owner()
