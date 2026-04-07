"""
tracker.py - Centroid tabanlı çoklu hedef takibi
"""

import time
from config import SMOOTH_ALPHA

_tracks  = {}
_next_id = 0

MAX_MATCH_DIST = 130   # piksel
MAX_GONE_SEC   = 3.5   # saniye


def _smooth(new_val, old_val, alpha):
    return int(alpha * new_val + (1 - alpha) * old_val)


def update(targets):
    global _next_id, _tracks

    now = time.time()

    # Süresi dolmuş track'leri temizle
    _tracks = {tid: t for tid, t in _tracks.items()
               if now - t["last_seen"] < MAX_GONE_SEC}

    matched_ids = set()

    for target in targets:
        cx, cy   = target["center"]
        x, y, w, h = target["bbox"]

        best_id   = None
        best_dist = MAX_MATCH_DIST

        for tid, track in _tracks.items():
            if tid in matched_ids:
                continue
            tx, ty = track["center"]
            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_id   = tid

        if best_id is not None:
            prev_cx, prev_cy = _tracks[best_id]["center"]
            prev_bbox        = _tracks[best_id].get("bbox", (x, y, w, h))

            smooth_cx = _smooth(cx, prev_cx, SMOOTH_ALPHA)
            smooth_cy = _smooth(cy, prev_cy, SMOOTH_ALPHA)
            smooth_x  = _smooth(x,  prev_bbox[0], SMOOTH_ALPHA)
            smooth_y  = _smooth(y,  prev_bbox[1], SMOOTH_ALPHA)
            smooth_w  = _smooth(w,  prev_bbox[2], SMOOTH_ALPHA)
            smooth_h  = _smooth(h,  prev_bbox[3], SMOOTH_ALPHA)

            _tracks[best_id]["center"]    = (smooth_cx, smooth_cy)
            _tracks[best_id]["bbox"]      = (smooth_x, smooth_y, smooth_w, smooth_h)
            _tracks[best_id]["last_seen"] = now

            target["center"]        = (smooth_cx, smooth_cy)
            target["bbox"]          = (smooth_x, smooth_y, smooth_w, smooth_h)
            target["dwell_seconds"] = now - _tracks[best_id]["first_seen"]
            target["track_id"]      = best_id
            matched_ids.add(best_id)

        else:
            _tracks[_next_id] = {
                "center":     (cx, cy),
                "bbox":       (x, y, w, h),
                "first_seen": now,
                "last_seen":  now,
            }
            target["dwell_seconds"] = 0.0
            target["track_id"]      = _next_id
            matched_ids.add(_next_id)
            _next_id += 1

    return targets


def reset():
    global _tracks, _next_id
    _tracks  = {}
    _next_id = 0
