import os

# Projenin ana/kök dizinini dinamik olarak al
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Video / Kamera ---
VIDEO_SOURCE          = os.path.join(BASE_DIR, "dataset", "tank.mp4")
FRAME_WIDTH           = 1366
FRAME_HEIGHT          = 768
FPS_TARGET            = 60
DISPLAY_SCALE         = 1
DETECT_EVERY_N_FRAMES = 2

# --- Görüntü İşleme ---
GAUSSIAN_BLUR_KERNEL  = (5, 5)
CANNY_THRESHOLD_LOW   = 50
CANNY_THRESHOLD_HIGH  = 150

# --- YOLO ---
YOLO_MODEL_PATH       = os.path.join(BASE_DIR, "yolov8n.pt")
YOLO_CONFIDENCE       = 0.25
YOLO_PERSON_CONFIDENCE = 0.40
YOLO_TARGET_CLASSES   = [0, 2, 5, 7]   # person, car, bus, truck
YOLO_NMS_IOU          = 0.30
YOLO_AGNOSTIC_NMS     = True

# --- Takip ---
SMOOTH_ALPHA          = 0.55

# --- Görselleştirme ---
BOUNDING_BOX_THICKNESS = 2
CENTER_MARKER_RADIUS   = 5

# --- Tehdit Eşikleri (saniye) ---
DWELL_RED_SEC  = 4.0

# --- Loglama ---
LOG_DIR       = os.path.join(BASE_DIR, "logs")
LOG_FILENAME  = "detections"
MIN_LOG_DWELL = 0.5
