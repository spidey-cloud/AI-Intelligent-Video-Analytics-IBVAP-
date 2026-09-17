"""Camera frame sources.

Production:  RTSPSource – existing IP CCTV over the SSB VPN (zero new hardware).
Reference:   SyntheticSource – procedural border scenes with ground-truth
             tracks so the full event/alert pipeline is demonstrable without
             hardware (proposal §14 MVP setup).
             VideoFileSource – recorded footage (detector tuning / ANPR clips).
"""
import math
import time

import cv2
import numpy as np


def resize_to_width(frame, width):
    """Adaptive streaming: analytics runs on a reduced-resolution frame.
    Scales so the LARGER dimension equals `width` (handles portrait feeds)."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    m = max(w, h)
    if m == width:
        return frame
    return cv2.resize(frame, (max(1, int(w * width / m)), max(1, int(h * width / m))))


# ---------------------------------------------------------------------------
# Synthetic border scenes (demo cameras)
# ---------------------------------------------------------------------------
class _Obj:
    def __init__(self, oid, kind, x, y, w, h, update_fn):
        self.id, self.kind = oid, kind
        self.x, self.y, self.w, self.h = x, y, w, h
        self.update_fn = update_fn

    def step(self, t, dt):
        self.x, self.y = self.update_fn(t, self.x, self.y)


def _smooth(p):
    return p * p * (3 - 2 * p)


class SyntheticSource:
    """Renders a stylized border scene (IR night / day / dusk) with moving
    persons and vehicles; emits ground-truth boxes used by SimDetector."""

    name = "synthetic"
    target_interval = 0.12

    def __init__(self, scene="north-gate", width=640, height=360):
        self.W, self.H, self.scene = width, height, scene
        self.t0 = time.time()
        self._last = self.t0
        self._build()

    # -- scene definitions ----------------------------------------------------
    def _build(self):
        o = []
        if self.scene == "north-gate":
            # IR-night scene. Perimeter fence line at y=180; restricted strip
            # above it (y < 180). Person periodically "climbs" the fence.
            def person(t, x, y):
                x = (t * 24) % 760 - 60
                y = 192 - 60 * math.exp(-(((x - 330) / 80) ** 2))
                return x, y

            def truck(t, x, y):
                return 60 + 500 * (0.5 + 0.5 * math.sin(t * 0.10)), 318

            def walker(t, x, y):
                return 560 - (t * 18) % 720 + 60, 258

            o.append(_Obj(1, "person", 80, 192, 26, 52, person))
            o.append(_Obj(2, "truck", 200, 318, 118, 44, truck))
            o.append(_Obj(3, "person", 400, 258, 24, 48, walker))
        elif self.scene == "west-approach":
            # Day scene. Person patrols to the gate zone, holds (loiters),
            # returns – exercises intrusion + loitering rules.
            def gate_person(t, x, y):
                c = t % 44
                if c < 18:
                    return 140 + (610 - 140) * _smooth(c / 18), 252
                if c < 34:
                    return 600 + 14 * math.sin(t * 2.1), 250
                return 610 - (610 - 140) * _smooth((c - 34) / 10), 252

            def car(t, x, y):
                return (t * 70) % 820 - 120, 300

            o.append(_Obj(1, "person", 140, 252, 26, 52, gate_person))
            o.append(_Obj(2, "car", 100, 300, 86, 34, car))
        else:  # checkpoint (dusk)
            def queue(t, x, y):
                return (t * 16) % 900 - 160, 306

            def strag(t, x, y):
                c = t % 36
                if 8 < c < 20:
                    return 100 + (420 - 100) * _smooth((c - 8) / 12), 150
                if c >= 20:
                    return 420 - (420 - 100) * _smooth((c - 20) / 16), 150
                return 100, 150

            o.append(_Obj(1, "truck", 200, 306, 118, 44, queue))
            o.append(_Obj(2, "person", 100, 150, 26, 52, strag))
        self.objs = o

    # -- frame API -------------------------------------------------------------
    def read(self):
        now = time.time()
        dt = min(0.25, now - self._last)
        self._last = now
        t = now - self.t0
        for o in self.objs:
            o.step(t, dt)
        frame = self._render(t)
        truth = []
        for o in self.objs:
            conf = 0.84 + 0.12 * (0.5 + 0.5 * math.sin(t * 1.9 + o.id * 2.3))
            x1, y1 = max(0, int(o.x) - 2), max(0, int(o.y) - 2)
            x2, y2 = min(self.W, int(o.x + o.w) + 2), min(self.H, int(o.y + o.h) + 2)
            truth.append({"id": o.id, "cls": o.kind, "conf": conf,
                          "box": (x1, y1, x2 - x1, y2 - y1)})
        return frame, {"truth": truth}

    # -- rendering ---------------------------------------------------------------
    def _render(self, t):
        f = np.zeros((self.H, self.W, 3), np.uint8)
        if self.scene == "north-gate":
            self._vgrad(f, (10, 28, 14), (28, 66, 34))
            self._ground(f, (18, 44, 22), 200)
            self._fence(f, 180, (90, 200, 110))
            self._watchtower(f, 60, 120)
            self._lamp(f, 560, 120)
        elif self.scene == "west-approach":
            self._vgrad(f, (120, 116, 108), (176, 168, 152))
            self._ground(f, (120, 112, 96), 210)
            self._road(f, 280, 70, (84, 82, 80))
            self._checkpoint(f, 120, 150)
        else:
            self._vgrad(f, (52, 42, 66), (140, 92, 60))
            self._ground(f, (88, 74, 62), 200)
            self._road(f, 288, 66, (70, 66, 64))
            self._gate(f, 240, 120)
        for o in self.objs:
            if o.kind == "person":
                self._person(f, o)
            else:
                self._vehicle(f, o)
        tag = "IBVAP-CAM · " + self.scene.upper()
        (tw, _), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.putText(f, tag, ((self.W - tw) // 2, self.H - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
        return f

    @staticmethod
    def _vgrad(f, top, bottom):
        for i in range(f.shape[0]):
            k = i / max(1, f.shape[0] - 1)
            f[i] = tuple(int(a + (b - a) * k) for a, b in zip(top, bottom))

    def _ground(self, f, color, y0):
        f[y0:] = color

    def _fence(self, f, y, color):
        w = f.shape[1]
        cv2.line(f, (0, y), (w, y), color, 2)
        cv2.line(f, (0, y - 14), (w, y - 14), color, 1)
        for x in range(8, w, 46):
            cv2.line(f, (x, y + 4), (x, y - 18), color, 2)

    def _road(self, f, y, h, color):
        cv2.rectangle(f, (0, y), (f.shape[1], y + h), color, -1)
        for x in range(0, f.shape[1], 40):
            cv2.line(f, (x, y + h // 2), (x + 18, y + h // 2), (210, 210, 190), 1)

    def _watchtower(self, f, x, y):
        cv2.line(f, (x, y + 70), (x + 14, y), (110, 110, 110), 3)
        cv2.rectangle(f, (x - 8, y - 22), (x + 34, y + 4), (55, 55, 55), -1)
        cv2.rectangle(f, (x - 4, y - 18), (x + 30, y - 2), (140, 170, 140), -1)

    def _lamp(self, f, x, y):
        cv2.line(f, (x, y), (x, y + 80), (130, 130, 130), 3)
        cv2.circle(f, (x, y), 8, (140, 190, 255), 2)
        cv2.fillPoly(f, np.array([[x, y], [x - 34, y + 80], [x + 34, y + 80]]), (34, 74, 42))

    def _checkpoint(self, f, x, y):
        cv2.rectangle(f, (x, y), (x + 70, y + 34), (150, 150, 150), -1)
        cv2.rectangle(f, (x + 8, y + 6), (x + 62, y + 22), (90, 90, 90), -1)
        cv2.putText(f, "SSB", (x + 24, y + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)

    def _gate(self, f, x, y):
        cv2.rectangle(f, (x, y), (x + 6, y + 80), (90, 90, 110), -1)
        cv2.rectangle(f, (x + 90, y), (x + 96, y + 80), (90, 90, 110), -1)
        cv2.rectangle(f, (x, y), (x + 96, y + 8), (90, 90, 110), -1)

    def _person(self, f, o):
        x, y, w, h = int(o.x), int(o.y), int(o.w), int(o.h)
        c = (228, 228, 235) if self.scene == "north-gate" else (60, 60, 70)
        r = max(3, int(w * 0.42))
        cv2.circle(f, (x + w // 2, y + r), r, c, -1)
        cv2.rectangle(f, (x + int(w * 0.22), y + 2 * r),
                      (x + int(w * 0.78), y + 2 * r + int(h * 0.34)), c, -1)
        mid = y + 2 * r + int(h * 0.34)
        cv2.line(f, (x + w // 2, mid), (x + int(w * 0.28), y + h), c, 2)
        cv2.line(f, (x + w // 2, mid), (x + int(w * 0.72), y + h), c, 2)
        cv2.line(f, (x + int(w * 0.24), y + 2 * r + 4),
                 (x + int(w * 0.10), y + 2 * r + int(h * 0.28)), c, 2)
        cv2.line(f, (x + int(w * 0.76), y + 2 * r + 4),
                 (x + int(w * 0.90), y + 2 * r + int(h * 0.28)), c, 2)

    VEH_COLORS = {"car": (170, 45, 45), "bus": (180, 80, 30),
                  "truck": (95, 125, 55), "motorcycle": (80, 80, 80)}

    def _vehicle(self, f, o):
        x, y, w, h = int(o.x), int(o.y), int(o.w), int(o.h)
        c = self.VEH_COLORS.get(o.kind, (120, 120, 120))
        if o.kind == "truck":
            cv2.rectangle(f, (x, y + 4), (x + int(w * 0.62), y + h - 8), c, -1)
            cv2.rectangle(f, (x + int(w * 0.62), y + int(h * 0.30)),
                          (x + w, y + h - 8), (max(0, c[0] - 30), max(0, c[1] - 30), max(0, c[2] - 30)), -1)
            cv2.rectangle(f, (x + int(w * 0.74), y + int(h * 0.36)),
                          (x + int(w * 0.94), y + int(h * 0.52)), (200, 230, 255), -1)
        else:
            cv2.rectangle(f, (x, y + int(h * 0.42)), (x + w, y + h - 8), c, -1)
            cv2.rectangle(f, (x + int(w * 0.22), y + 4),
                          (x + int(w * 0.72), y + int(h * 0.52)),
                          (max(0, c[0] - 20), max(0, c[1] - 20), max(0, c[2] - 20)), -1)
        for cx in (x + int(w * 0.22), x + int(w * 0.78)):
            cv2.circle(f, (cx, y + h - 8), max(3, h // 6), (20, 20, 20), -1)
            cv2.circle(f, (cx, y + h - 8), max(1, h // 12), (95, 95, 95), -1)


# ---------------------------------------------------------------------------
# RTSP source (production path – existing IP CCTV)
# ---------------------------------------------------------------------------
class RTSPSource:
    name = "rtsp"
    target_interval = 0.05

    def __init__(self, url, timeout_ms=4000):
        self.url = url
        self.timeout_ms = timeout_ms
        self.cap = None

    def _connect(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if self.timeout_ms:
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.timeout_ms)
        return self.cap if self.cap.isOpened() else None

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            if not self._connect():
                return None, {}
        ok, frame = self.cap.read()
        if not ok or frame is None:
            self.cap = None
            return None, {}
        return frame, {}


# ---------------------------------------------------------------------------
# Recorded-footage source (looping)
# ---------------------------------------------------------------------------
class VideoFileSource:
    name = "video"
    target_interval = 0.05

    def __init__(self, path, loop=True):
        self.path, self.loop, self.cap = path, loop, None

    def _connect(self):
        self.cap = cv2.VideoCapture(self.path)
        return self.cap if self.cap.isOpened() else None

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            if not self._connect():
                return None, {}
        ok, frame = self.cap.read()
        if not ok or frame is None:
            if not self.loop:
                return None, {}
            self.cap = None
            return self.read()
        return frame, {}


def build_source(cfg: dict):
    t = cfg.get("type")
    if t is None:  # infer from config keys for robustness
        t = "rtsp" if "url" in cfg else ("video" if "path" in cfg else "synthetic")
    if t == "rtsp":
        return RTSPSource(cfg.get("url", ""), cfg.get("timeout_ms", 4000))
    if t == "video":
        return VideoFileSource(cfg.get("path", ""))
    return SyntheticSource(scene=cfg.get("scene", "north-gate"),
                           width=cfg.get("width", 640), height=cfg.get("height", 360))
