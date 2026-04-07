"""
transmit_task.py
----------------
Hedefleri izler ve durum değişikliklerinde log yazar.

Her hedef iki aşamadan geçer:
  1. BEKLEMEDE (_pending): Yeni görüldü ama henüz doğrulanmadı
  2. AKTIF (_tracks)     : MIN_LOG_DWELL süresini geçti, artık loga yazılır

Bu iki aşama gürültüyü temizliyor:
  Eğer bir tespit 0.5 saniyeden kısa sürede kaybolursa (büyük ihtimalle
  YOLO'nun anlık hata yaptığı bir frame), loga hiç yazılmaz.
  Böylece 'KONTAK KURULDU → 0.0s → KONTAK KESILDI' satırları ortadan kalkar.

Aktif hedefler için durum değişimlerinde log düşülür:
  KONTAK KURULDU  → hedef MIN_LOG_DWELL süresini geçti, takibe alındı
  TEHDIT TESPIT   → dwell DWELL_RED_SEC eşiğini aştı
  TEHDIT SONLANDI → dwell eşiğin altına düştü
  KONTAK KESILDI  → hedef GRACE_PERIOD boyunca görülmedi
"""

import time
from config import DWELL_RED_SEC, MIN_LOG_DWELL
from utils.logger import log_event

# tracker.py'deki MAX_GONE_SEC ile aynı olmalı — ikisi de 3.5 saniye
GRACE_PERIOD = 3.5

# Onaylanan hedefler: log yazılmış, durum takibi aktif
# Yapı: { track_id: {"state": str, "last_target": dict, "last_seen": float} }
_tracks = {}

# Beklemedeki hedefler: henüz MIN_LOG_DWELL'i geçmedi, log yazılmadı
# Eğer bu süreyi geçerse _tracks'e taşınır, geçemeden kaybolursa sessizce silinir
_pending = {}


def evaluate_alert(targets):
    """Herhangi bir hedef DWELL_RED_SEC saniyeyi geçtiyse True döner."""
    for target in targets:
        if target.get("dwell_seconds", 0.0) >= DWELL_RED_SEC:
            return True
    return False


def transmit_targets(frame_no, targets):
    """
    Her hedefin durumunu önceki frame ile karşılaştırır.

    Yeni hedefler önce _pending'e alınır. MIN_LOG_DWELL süresini geçince
    KONTAK KURULDU logu atılır ve _tracks'e taşınır. Bu süreyi geçemeden
    kaybolan hedefler (gürültü) loga hiç yazılmaz.

    Returns:
        bool: Şu an aktif tehdit var mı?
    """
    global _tracks, _pending

    now = time.time()
    seen_ids = set()
    any_alert = False

    for target in targets:
        tid = target.get("track_id", 0)
        dwell = target.get("dwell_seconds", 0.0)
        is_alert = dwell >= DWELL_RED_SEC

        seen_ids.add(tid)
        if is_alert:
            any_alert = True

        if tid in _tracks:
            # Onaylı hedef — durum geçiş kontrolü
            prev_state = _tracks[tid]["state"]

            if is_alert and prev_state == "TRACKING":
                _tracks[tid]["state"] = "THREAT"
                log_event(frame_no, target, "TEHDIT TESPIT", tid)

            elif not is_alert and prev_state == "THREAT":
                _tracks[tid]["state"] = "TRACKING"
                log_event(frame_no, target, "TEHDIT SONLANDI", tid)

            _tracks[tid]["last_target"] = target
            _tracks[tid]["last_seen"] = now

        elif tid in _pending:
            # Bekleme aşaması — yeterli dwell'e ulaştı mı?
            _pending[tid]["last_target"] = target
            _pending[tid]["last_seen"] = now

            if dwell >= MIN_LOG_DWELL:
                # Onaylandı, _tracks'e taşı ve logla
                new_state = "THREAT" if is_alert else "TRACKING"
                _tracks[tid] = {
                    "state": new_state,
                    "last_target": target,
                    "last_seen": now,
                }
                del _pending[tid]
                log_event(frame_no, target, "KONTAK KURULDU", tid)
                if is_alert:
                    log_event(frame_no, target, "TEHDIT TESPIT", tid)

        else:
            # Marka yeni hedef — önce beklemeye al
            _pending[tid] = {
                "last_target": target,
                "last_seen": now,
            }

    # Bekleme aşamasını geçemeden kaybolan hedefleri sessizce sil
    expired_pending = [
        tid for tid, info in _pending.items()
        if tid not in seen_ids and now - info["last_seen"] >= GRACE_PERIOD
    ]
    for tid in expired_pending:
        del _pending[tid]  # log yazılmaz

    # Onaylı ama kaybolmuş hedefleri kontrol et
    expired_ids = []
    for tid, info in _tracks.items():
        if tid not in seen_ids:
            gone_for = now - info["last_seen"]
            if gone_for >= GRACE_PERIOD:
                expired_ids.append(tid)

    for tid in expired_ids:
        info = _tracks.pop(tid)
        log_event(frame_no, info["last_target"], "KONTAK KESILDI", tid)

    return any_alert
