"""Rule engine + event lifecycle.

Rules implemented in the reference build:
  • virtual-fence intrusion  – track centroid crosses into a zone polygon
  • loitering                – track dwells in a zone longer than T
(ANPR / abandoned-object / face-watchlist plug in at the same seam –
see docs/ARCHITECTURE.md §6.)

Storage is event-only (proposal §5.1C): snapshots on fire, a 20-second
ring-buffer evidence clip finalised when the event closes.
"""
import json
import os
from collections import deque

import cv2

from . import db
from .annotate import draw_frame


def point_in_polygon(px, py, pts):
    inside, n, j = False, len(pts), len(pts) - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


class RingBuffer:
    """Small per-camera ring of recent frames; flushed to MP4 around events."""

    def __init__(self, max_frames=40, width=480, height=270, fps=2):
        self.buf = deque(maxlen=max_frames)
        self.width, self.height, self.fps = width, height, fps
        self.last_t = 0

    def tick(self, frame, now):
        if now - self.last_t < 0.5:
            return
        self.last_t = now
        self.buf.append((now, cv2.resize(frame, (self.width, self.height))))

    def flush(self, t0, t1, path):
        frames = [f for t, f in self.buf if t0 <= t <= t1]
        if len(frames) < 4:
            return False
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"),
                                 self.fps, (self.width, self.height))
        if not writer.isOpened():
            return False
        for f in frames:
            writer.write(f)
        writer.release()
        return os.path.exists(path)


class EventEngine:
    def __init__(self, cam_id, media_dir, settings, alerts, camera_name=""):
        self.cam_id = cam_id
        self.media_dir = media_dir
        self.sdir = os.path.join(media_dir, "snapshots")
        self.cdir = os.path.join(media_dir, "clips")
        os.makedirs(self.sdir, exist_ok=True)
        os.makedirs(self.cdir, exist_ok=True)
        self.settings = settings
        self.alerts = alerts
        self.camera_name = camera_name
        self.ring = RingBuffer(max_frames=settings.clip_seconds * settings.ring_fps)
        self._zs_cache, self._zs_t = None, 0.0
        self.state = {}           # track_id -> {zone_id: {...}, "_ts": t}
        self.active = {}          # event_id -> {track_id, zone_id, started, last_seen}
        self.ev_by_tz = {}        # (track_id, zone_id) -> [event_id, ...]
        self.zone_last_fire = {}  # (track_id, zone_id) -> t (intrusion cooldown)
        self._last_seen_pos = {}  # track_id -> (t, cx, cy) normalized centroid
        self._detect_seen = {}    # track_id -> last alert time (detection alert)
        self._detect_classes = set(
            c.strip() for c in settings.detect_alert_classes.split(",") if c.strip()
        )

    # -- track handoff ---------------------------------------------------------
    def _handoff(self, d, pos, now, live):
        """A brand-new track appearing where a track just vanished is almost
        always an ID reset (frame gap / jitter), not a new object. Inherit the
        donor's zone state so the object does not 're-intrude' a zone it is
        already inside — suppresses a whole class of false alarms."""
        for tid_d in [t for t in self.state if t != d.track_id and t not in live]:
            last = self._last_seen_pos.get(tid_d)
            if last is None or now - last[0] > 10.0:
                continue
            dx, dy = last[1] - pos[0], last[2] - pos[1]
            if dx * dx + dy * dy > 0.10 ** 2:      # ~64 px at 640 wide
                continue
            st_d = self.state.pop(tid_d)
            self.state[d.track_id] = st_d          # inside/enter/loiter carry over
            self._last_seen_pos[d.track_id] = last
            for zid in st_d:
                if zid == "_ts":
                    continue
                old = (tid_d, zid)
                if old in self.zone_last_fire:
                    self.zone_last_fire[(d.track_id, zid)] = \
                        self.zone_last_fire.pop(old)
                if old in self.ev_by_tz:
                    self.ev_by_tz[(d.track_id, zid)] = self.ev_by_tz.pop(old)
            for a in self.active.values():
                if a["track_id"] == tid_d:
                    a["track_id"] = d.track_id
            return

    # -- zones (3 s cache) ----------------------------------------------------
    def zones(self, now):
        if now - self._zs_t > 3 or self._zs_cache is None:
            self._zs_cache = db.list_zones(self.cam_id)
            for z in self._zs_cache:
                z["points"] = json.loads(z["points"])
            self._zs_t = now
        return self._zs_cache or []

    # -- main per-frame hook ---------------------------------------------------
    def process(self, frame, dets, now):
        live = {d.track_id for d in dets}
        h, w = frame.shape[:2]
        for d in dets:
            if d.track_id not in self.state:
                cx, cy = (d.x + d.w / 2) / w, (d.y + d.h / 2) / h
                self._handoff(d, (cx, cy), now, live)
        for d in dets:
            cx, cy = (d.x + d.w / 2) / w, (d.y + d.h / 2) / h
            st = self.state.setdefault(d.track_id, {})
            st["_ts"] = now
            self._last_seen_pos[d.track_id] = (now, cx, cy)
            active_zones = self.zones(now)
            for z in active_zones:
                zs = st.setdefault(z["id"], {"inside": False, "enter": 0.0, "loiter": False})
                inside = point_in_polygon(cx, cy, z["points"])
                if inside and not zs["inside"]:
                    zs["inside"], zs["enter"] = True, now
                    key = (d.track_id, z["id"])
                    if now - self.zone_last_fire.get(key, 0) > self.settings.intrusion_cooldown:
                        self.zone_last_fire[key] = now
                        self._fire(d, z, "intrusion",
                                   "high" if d.cls == "person" else "medium", frame, now)
                elif inside:
                    if not zs["loiter"] and now - zs["enter"] > self.settings.loiter_seconds:
                        zs["loiter"] = True
                        self._fire(d, z, "loitering", "medium", frame, now)
                elif zs["inside"]:
                    zs["inside"], zs["loiter"] = False, False
                    for eid in self.ev_by_tz.pop((d.track_id, z["id"]), []):
                        self._close(eid, now)
            # person-in-frame detection alert: only when no zones are configured
            # (if zones exist but the detection is outside them all, no event fires)
            if not active_zones:
                self._check_detect_alert(d, frame, now)
        # update liveness + drop stale rule state
        for eid, a in list(self.active.items()):
            if a["track_id"] in live:
                a["last_seen"] = now
        for tid in list(self.state):
            ts = self.state[tid].get("_ts")
            if ts is not None and now - ts > 5:
                del self.state[tid]
        for tid in [t for t, p in self._last_seen_pos.items() if now - p[0] > 15]:
            del self._last_seen_pos[tid]
        # clean stale detect_seen entries
        for tid in [t for t, lt in list(self._detect_seen.items()) if now - lt > self.settings.detect_cooldown * 2]:
            del self._detect_seen[tid]
        # max-age / lost-track fallback
        for eid, a in list(self.active.items()):
            if now - a.get("last_seen", a["started"]) > self.settings.event_stable_gap \
               or now - a["started"] > self.settings.event_max_age:
                self._close(eid, now)

    # -- detection alert (person in frame, no zone needed) --------------------
    def _check_detect_alert(self, d, frame, now):
        if d.cls not in self._detect_classes:
            return
        last = self._detect_seen.get(d.track_id, 0)
        if now - last < self.settings.detect_cooldown:
            return
        self._detect_seen[d.track_id] = now
        self._fire_detect(d, frame, now)

    def _fire_detect(self, d, frame, now):
        # snap = os.path.join(self.sdir, f"cam{self.cam_id}_det{int(now * 1000)}.jpg")
        # ok = cv2.imwrite(snap, draw_frame(frame, [d], [], self.camera_name, now))
        eid = db.add_event(self.cam_id, None, d.track_id, d.cls, "detection",
                           "medium", d.conf, None,
                           meta={"source": "detect_alert"})
        ev = db.get_event(eid)
        db.add_alert(eid, "ws", {"type": "detection"})
        self.alerts.push({"kind": "alert", "event": ev})

    # -- event lifecycle --------------------------------------------------------
    def _fire(self, d, zone, etype, severity, frame, now):
        # snap = os.path.join(self.sdir, f"cam{self.cam_id}_t{int(now * 1000)}.jpg")
        # ok = cv2.imwrite(snap, draw_frame(frame, [d], [zone], self.camera_name, now))
        eid = db.add_event(self.cam_id, zone["id"], d.track_id, d.cls, etype,
                           severity, d.conf, None,
                           meta={"zone_kind": zone.get("kind")})
        ev = db.get_event(eid)
        self.active[eid] = {"track_id": d.track_id, "zone_id": zone["id"],
                            "started": now, "last_seen": now}
        self.ev_by_tz.setdefault((d.track_id, zone["id"]), []).append(eid)
        db.add_alert(eid, "ws", {"type": etype})
        self.alerts.push({"kind": "alert", "event": ev})

    def _close(self, eid, now):
        a = self.active.pop(eid, None)
        if a is None:
            return
        # path = os.path.join(self.cdir, f"cam{self.cam_id}_ev{eid}.mp4")
        # if self.ring.flush(a["started"] - 10, now + 2, path):
        #     db.update_event(eid, clip=path)
        #     db.close_event(eid, path)
        # else:
        #     db.close_event(eid)
        db.close_event(eid)
        self.alerts.push({"kind": "event_closed", "event_id": eid})
