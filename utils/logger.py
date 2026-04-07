"""
logger.py - Olay tabanlı telemetri kaydı
"""

import csv
import os
from datetime import datetime
from config import LOG_DIR, LOG_FILENAME

_CSV_HEADER = ["timestamp", "event", "target_id", "frame_no", "x", "y", "label", "dwell_sec"]


def get_log_filepath():
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{LOG_FILENAME}_{today}.csv")


def _ensure_header(filepath):
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_CSV_HEADER)


def log_event(frame_no, target, event, target_id="TGT"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cx, cy    = target.get("center", (0, 0))
    label     = target.get("label", "unknown")
    dwell     = target.get("dwell_seconds", 0.0)

    print(f"{timestamp} | {event} | TGT-{target_id:03d} | Frame:{frame_no} | X:{cx} Y:{cy} | {label} | dwell:{dwell:.1f}s")

    try:
        filepath = get_log_filepath()
        _ensure_header(filepath)
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [timestamp, event, target_id, frame_no, cx, cy, label, round(dwell, 2)]
            )
    except OSError as e:
        print(f"[UYARI] Log dosyasina yazilamadi: {e}")
