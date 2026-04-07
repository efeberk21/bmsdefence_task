"""
process_task.py
---------------
Görevi: ham frame'e ön işleme uygulamak.
Tespit veya kayıt işlemi yapmaz, sadece görüntüyü dönüştürür.

Uygulanan adımlar:
  - Grayscale  : Renk kanallarını tek kanala indirger, işlemi hızlandırır
  - Blur       : Küçük gürültüleri yumuşatır → sahte kenarlar azalır
  - Canny      : Renk geçişlerini kenar haritasına çevirir (YOLO doğrulama için kullanılıyor)
"""

import cv2
from config import (
    GAUSSIAN_BLUR_KERNEL,
    CANNY_THRESHOLD_LOW,
    CANNY_THRESHOLD_HIGH,
)


def to_grayscale(frame):
    """BGR frame'i gri tonlamaya çevirir."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def apply_gaussian_blur(gray_frame):
    """Gaussian blur uygular. Canny öncesinde gürültüyü azaltmak için kullanılıyor."""
    return cv2.GaussianBlur(gray_frame, GAUSSIAN_BLUR_KERNEL, 0)


def apply_canny_edge(blurred_frame):
    """
    Canny kenar tespiti.
    low  → bu değerin altındaki geçişler kenar sayılmaz
    high → bu değerin üstündeki geçişler kenar olarak işaretlenir
    """
    return cv2.Canny(blurred_frame, CANNY_THRESHOLD_LOW, CANNY_THRESHOLD_HIGH)



def preprocess_frame(frame):
    """
    Tüm ön işleme adımlarını sırayla uygular ve sonuçları sözlük olarak döndürür.

    Returns:
        dict: {original, gray, blurred, edges}
    """
    gray    = to_grayscale(frame)
    blurred = apply_gaussian_blur(gray)

    # Canny: YOLO'nun tespitlerini doğrulamak için kullanıyoruz (edge verification)
    edges = apply_canny_edge(blurred)

    return {
        "original": frame,
        "gray":     gray,
        "blurred":  blurred,
        "edges":    edges,
    }
