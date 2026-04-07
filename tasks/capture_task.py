"""
capture_task.py
---------------
Görevi: kamera ya da video dosyasından ham frame okumak.
Başka hiçbir işlem yapmaz, sadece frame döndürür.
"""

import cv2
from config import VIDEO_SOURCE, FRAME_WIDTH, FRAME_HEIGHT


def initialize_capture(video_source=None):
    """
    Video yakalama nesnesini başlatır ve çözünürlüğü ayarlar.
    Kaynak açılamazsa RuntimeError fırlatır.
    """
    # Eğer özel bir kaynak verilmişse onu, aksi halde config'de olanı kullan
    source = video_source if video_source is not None else VIDEO_SOURCE
    
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError(f"Video kaynagi acilamadi: {source}")

    # Webcam'de çözünürlük ayarı geçerli olur, video dosyasında genellikle yoksayılır
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    return cap


def capture_frame(cap):
    """
    Bir sonraki frame'i okur ve config'deki boyuta göre yeniden boyutlandırır.

    cap.set() ile boyut ayarlamak sadece webcam'de çalışır.
    Video ve resim dizileri için rezise burada yapılıyor böylece
    kaynak türünden bağımsız olarak her zaman aynı boyutta frame geliyor.

    Returns:
        (True, frame)  → okuma başarılı
        (False, None)  → video bitti veya hata var
    """
    success, frame = cap.read()
    if not success:
        return False, None
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    return True, frame


def release_capture(cap):
    """Kamera/video nesnesini serbest bırakır. Program kapanırken çağrılmalı."""
    cap.release()
