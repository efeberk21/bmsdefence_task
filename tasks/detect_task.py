"""
detect_task.py
--------------
Görevi: görüntüde hedef tespit etmek ve koordinatları döndürmek.


Hibrit Tespit :
  YOLOv8 derin öğrenme ile nesneleri bulur.
  Bulunan her kutu, Canny kenar haritasıyla çapraz doğrulanır.
  İçinde yeterli kenar pikseli olmayan kutular sahte pozitif olarak atılır.
"""

import cv2
import numpy as np
from config import (
    BOUNDING_BOX_THICKNESS,
    CENTER_MARKER_RADIUS,
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE,
    YOLO_PERSON_CONFIDENCE,
    YOLO_TARGET_CLASSES,
    YOLO_NMS_IOU,
    YOLO_AGNOSTIC_NMS,
)

# YOLO modeli program boyunca bir kez yükleniyor
_yolo_model = None


def _load_yolo_model():
    """
    YOLO modelini belleğe yükler. Uygulama açılışında bir kez çalışır.
    _yolo_model global değişkeniyle modeli tekrar yüklemekten kaçınıyoruz.
    """
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(YOLO_MODEL_PATH)
        except FileNotFoundError:
            raise RuntimeError(f"YOLO model dosyası bulunamadı: {YOLO_MODEL_PATH}")
        except Exception as e:
            raise RuntimeError(f"YOLO modeli yüklenirken hata oluştu: {e}")
    return _yolo_model


def get_targets(processed, frame):
    """
    Hibrit tespit: YOLOv8 + Canny Kenar Doğrulama.

    Adımlar:
      1. YOLOv8 hedefleri tespit eder.
      2. Her tespit için bounding box içindeki Canny kenar yoğunluğu hesaplanır.
      3. Kenar yoğunluğu eşiğin altında olan tespitler (düz yüzey) atılır.
      4. İnsan tespitlerinde daha yüksek güven eşiği uygulanır.

    Returns:
        list of dict: bbox, center, area, label, confidence içerir
    """
    model = _load_yolo_model()
    results = model(
        frame,
        conf=YOLO_CONFIDENCE,
        classes=YOLO_TARGET_CLASSES,
        verbose=False,
        agnostic_nms=YOLO_AGNOSTIC_NMS,
        iou=YOLO_NMS_IOU,
    )

    targets   = []
    edges_map = processed["edges"]  # process_task.py'den gelen Canny kenar haritası

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        w  = x2 - x1
        h  = y2 - y1
        cx = x1 + w // 2
        cy = y1 + h // 2

        # -- Kenar Doğrulama (Edge Verification) --
        # YOLO bazen düz asfalttaki gölgeyi veya yerdeki lekeyi araç sanabilir.
        # Gerçek bir araç ya da insanın içinde keskin kenarlar (tekerlek, omuz, çerçeve) olur.
        roi_y1 = max(0, y1)
        roi_y2 = min(edges_map.shape[0], y2)
        roi_x1 = max(0, x1)
        roi_x2 = min(edges_map.shape[1], x2)
        roi_edges = edges_map[roi_y1:roi_y2, roi_x1:roi_x2]

        if roi_edges.size > 0:
            edge_pixel_count = np.count_nonzero(roi_edges == 255)
            edge_ratio       = edge_pixel_count / roi_edges.size

            # %1'den az kenar → büyük ihtimalle düz yüzey, YOLO yanılmış → atla
            if edge_ratio < 0.01:
                continue

        label      = results[0].names[int(box.cls)]
        confidence = float(box.conf)

        # -- Sınıfa Özel Güven Eşiği --
        # Logar kapakları, tabelalar gibi nesneler bazen insan olarak algılanıyor.
        # Person sınıfı için eşiği yükselterek bu hataları azaltıyoruz.
        if label == "person" and confidence < YOLO_PERSON_CONFIDENCE:
            continue

        targets.append({
            "bbox":       (x1, y1, w, h),
            "center":     (cx, cy),
            "area":       w * h,
            "label":      label,
            "confidence": confidence,
        })

    return targets


# --------------------------------------------------
# Çizim / Görselleştirme
# --------------------------------------------------

def _threat_color(label):
    """
    Hedef sınıfına göre tehdit rengi döndürür (BGR formatında).
    person         → kırmızı (yüksek tehdit)
    car/truck/bus  → sarı (orta tehdit)
    diğerleri      → yeşil (düşük tehdit / bilinmiyor)
    """
    if label == "person":
        return (0, 0, 255)
    elif label in ["car", "truck", "bus"]:
        return (0, 255, 255)
    else:
        return (0, 255, 0)


def draw_detections(frame, targets):
    """
    Tespit edilen hedefleri frame'e çizer.
    Bounding box rengi sınıfa göre değişir.
    DWELL_RED_SEC eşiği aşıldıysa hedef [LOCKED] olarak işaretlenir.
    Orijinal frame'i bozmamak için kopya üzerinde çalışır.
    """
    from config import DWELL_RED_SEC
    annotated = frame.copy()

    for target in targets:
        x, y, w, h = target["bbox"]
        cx, cy     = target["center"]
        label      = target["label"]
        conf_text  = f' {target["confidence"]:.2f}' if "confidence" in target else ""
        dwell      = target.get("dwell_seconds", 0.0)

        color = _threat_color(label)

        # Bounding box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, BOUNDING_BOX_THICKNESS)

        # Merkez noktası
        cv2.circle(annotated, (cx, cy), CENTER_MARKER_RADIUS, color, -1)

        dwell_str = f" [{dwell:.1f}s]" if dwell > 0.1 else ""

        if dwell >= DWELL_RED_SEC:
            # Kilitlenme — person zaten kırmızı olduğundan kilit rengi yeşil 
            lock_color = (0, 255, 0) if label == "person" else (0, 0, 255)
            label_text = f"[LOCKED] {label}{conf_text}{dwell_str}"
            cv2.rectangle(annotated, (x - 4, y - 4), (x + w + 4, y + h + 4), lock_color, 1)
            cv2.putText(annotated, label_text, (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, lock_color, 1)
            cv2.putText(annotated, "!! ALERT !!",  (x, y - 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        else:
            label_text = f"{label}{conf_text}{dwell_str}"
            cv2.putText(annotated, label_text, (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    return annotated
