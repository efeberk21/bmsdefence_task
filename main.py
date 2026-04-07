"""
main.py - BMS Defence IHA Görüntü İşleme Sistemi
Çıkmak için 'q' tuşuna bas.
"""

import time
import datetime
import cv2
import config

from tasks.capture_task  import initialize_capture, capture_frame, release_capture
from tasks.process_task  import preprocess_frame
from tasks.detect_task   import get_targets, draw_detections, _load_yolo_model
from tasks.transmit_task import transmit_targets
import utils.tracker as tracker_module

WINDOW_NAME = "IHA Vision System"
SYSTEM_VER  = "v1.0"


def draw_hud(frame, fps, frame_no, is_alert, target_count=0, threat_count=0):
    import numpy as np

    PANEL_X, PANEL_Y = 8, 8
    LINE_HEIGHT       = 22
    PANEL_W           = 310
    FONT              = cv2.FONT_HERSHEY_SIMPLEX
    FONT_S            = 0.48
    FONT_L            = 0.58
    COLOR_TITLE  = (0, 255, 255)
    COLOR_NORMAL = (200, 200, 200)
    COLOR_ALERT  = (0, 0, 255)
    COLOR_SAFE   = (0, 220, 0)
    PANEL_H = LINE_HEIGHT * 6 + 18

    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (PANEL_X - 4, PANEL_Y - 4),
                  (PANEL_X + PANEL_W, PANEL_Y + PANEL_H),
                  (10, 10, 10), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    now        = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    zone_label = "ALERT" if is_alert else "SAFE"
    zone_color = COLOR_ALERT if is_alert else COLOR_SAFE

    lines = [
        (f"BMS DEFENCE  IHA SYS  {SYSTEM_VER}",          FONT_L, COLOR_TITLE),
        (f"FPS: {fps:.1f}          Frame: {frame_no}",    FONT_S, COLOR_NORMAL),
        (f"Hedef: {target_count}   Tehdit: {threat_count}", FONT_S, COLOR_NORMAL),
        (f"Status:  {zone_label}",                         FONT_S, zone_color),
        (now,                                               FONT_S, COLOR_NORMAL),
    ]

    y = PANEL_Y + LINE_HEIGHT
    for text, size, color in lines:
        cv2.putText(frame, text, (PANEL_X, y), FONT, size, color, 1, cv2.LINE_AA)
        y += LINE_HEIGHT

    return frame


def scale_frame(frame, scale):
    h, w = frame.shape[:2]
    return cv2.resize(frame, (int(w * scale), int(h * scale)))


def run_pipeline(video_source=None):
    print("[INFO] Sistem baslatiliyor...")

    print("[INFO] YOLO modeli yukleniyor...")
    try:
        _load_yolo_model()
    except RuntimeError as e:
        print(f"[HATA] {e}")
        return
    print("[INFO] YOLO modeli hazir.")

    print("[INFO] Video/kamera kaynagi aciliyor...")
    try:
        cap = initialize_capture(video_source=video_source)
    except RuntimeError as e:
        print(f"[HATA] {e}")
        return
    print("[INFO] Kaynak basariyla acildi.\n")

    disp_w = int(config.FRAME_WIDTH  * config.DISPLAY_SCALE)
    disp_h = int(config.FRAME_HEIGHT * config.DISPLAY_SCALE)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, disp_w, disp_h)

    try:
        import ctypes
        user32   = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        cv2.moveWindow(WINDOW_NAME,
                       max(0, (screen_w - disp_w) // 2),
                       max(0, (screen_h - disp_h) // 2))
    except Exception:
        pass

    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

    frame_no      = 1
    fps_start     = time.time()
    fps_count     = 0
    fps_value     = 0.0
    last_targets  = []
    last_is_alert = False

    print("[INFO] Sistem hazir. Cikmak icin 'q' tusuna basin.\n")

    while True:
        success, current_frame = capture_frame(cap)
        if not success:
            print("[INFO] Video bitti veya kamera baglantisi kesildi.")
            break

        processed = preprocess_frame(current_frame)

        if frame_no % config.DETECT_EVERY_N_FRAMES == 0:
            raw_targets   = get_targets(processed, current_frame)
            last_targets  = tracker_module.update(raw_targets)
            last_is_alert = transmit_targets(frame_no, last_targets)

        display = draw_detections(current_frame, last_targets)

        target_count = len(last_targets)
        threat_count = sum(
            1 for t in last_targets
            if t.get("dwell_seconds", 0.0) >= config.DWELL_RED_SEC
        )

        display = draw_hud(display,
                           fps=fps_value,
                           frame_no=frame_no,
                           is_alert=last_is_alert,
                           target_count=target_count,
                           threat_count=threat_count)

        fps_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            fps_value = fps_count / elapsed
            fps_count = 0
            fps_start = time.time()

        cv2.imshow(WINDOW_NAME, scale_frame(display, config.DISPLAY_SCALE))

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Kullanici cikis yapti.")
            break

        frame_no += 1

    release_capture(cap)
    cv2.destroyAllWindows()
    print("[INFO] Sistem kapatildi.")


if __name__ == "__main__":
    import os
    print("=" * 50)
    print("BMS DEFENCE - IHA HEDEF TESPIT SISTEMI")
    print("=" * 50)
    print("Mevcut Kaynak Secenekleri:")
    print("  [1] Arac Simulasyonu (road.mp4)")
    print("  [2] Asker/Insan Simulasyonu (soldiers.mp4)")
    print("  [3] Canli Kamera (Webcam)")
    print("  [4] Ozel dosya yolu (Kendi klibini sec)")
    print("=" * 50)
    
    secim = input("Lutfen bir kaynak secin (1/2/3/4) [Varsayilan: 2]: ").strip()
    
    selected_source = None
    if secim == "1":
        selected_source = os.path.join(config.BASE_DIR, "dataset", "road.mp4")
    elif secim == "2":
        selected_source = os.path.join(config.BASE_DIR, "dataset", "soldiers.mp4")
    elif secim == "3":
        selected_source = 0
    elif secim == "4":
        import tkinter as tk
        from tkinter import filedialog
        
        print("[INFO] Lutfen acilan klasor penceresinden videoyu secin...")
        root = tk.Tk()
        root.withdraw() # Ana pencereyi gizle
        root.attributes('-topmost', True) # Secim penceresini diger pencerelerin ustune getir
        
        file_path = filedialog.askopenfilename(
            title="Video Dosyasi Sec",
            filetypes=[("Video Dosyalari", "*.mp4 *.avi *.mkv *.mov"), ("Tum Dosyalar", "*.*")]
        )
        
        if file_path:
            selected_source = file_path
        else:
            print("[UYARI] Dosya secilmedi. Varsayilan kaynak kullaniliyor. (soldiers.mp4)")
            selected_source = os.path.join(config.BASE_DIR, "dataset", "soldiers.mp4")
    else:
        # Varsayilan olarak soldiers
        if secim != "":
            print("[UYARI] Gecersiz secim. Varsayilan kaynak kullaniliyor. (soldiers.mp4)")
        selected_source = os.path.join(config.BASE_DIR, "dataset", "soldiers.mp4")
    
    print(f"\n[SECILEN KAYNAK] -> {selected_source}\n")
    
    try:
        run_pipeline(video_source=selected_source)
    except KeyboardInterrupt:
        print("\n[INFO] Kullanici programi kesti.")
    except Exception as e:
        print(f"[HATA] Beklenmedik bir sorun olustu: {e}")
