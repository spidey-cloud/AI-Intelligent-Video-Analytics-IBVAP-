"""Detection + lightweight IoU tracking.

Detectors are pluggable (proposal §5.1A: CPU-only inference, 3-5 FPS per
camera is sufficient for security analytics):

  SimDetector   – consumes SyntheticSource ground truth (reference demo mode)
  YOLODetector  – ultralytics YOLOv8/YOLO11 nano (default real feed; INT8 /
                  OpenVINO in production for 2-4× speed on CPU)
  SSDDetector   – OpenCV-DNN MobileNet-SSD fallback (no heavy deps)
"""
import os
import threading
from dataclasses import dataclass

import cv2

WANTED = {"person", "car", "motorcycle", "bus", "truck"}

SSD_LABELS = ["background", "aeroplane", "animal", "bird", "boat", "bottle",
              "bus", "car", "cat", "chair", "cow", "table", "dog", "horse",
              "motorbike", "person", "pottedplant", "sheep", "sofa", "train",
              "tvmonitor"]
RENAME = {"motorbike": "motorcycle"}


@dataclass
class Det:
    track_id: int
    cls: str
    conf: float
    x: int
    y: int
    w: int
    h: int


def _iou(a, b):
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    iw = min(ax1 + aw, bx1 + bw) - max(ax1, bx1)
    ih = min(ay1 + ah, by1 + bh) - max(ay1, by1)
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / (aw * ah + bw * bh - inter + 1e-6)


class Tracker:
    """Greedy IoU track association with expiry (BoT-SORT in production)."""

    def __init__(self, expire=1.6):
        self.expire = expire
        self.tracks = {}
        self._next = 1

    def update(self, raw, now):
        matched, out = set(), []
        for r in raw:
            best_id, best_iou = None, 0.0
            for tid, tr in self.tracks.items():
                if tid in matched:
                    continue
                i = _iou(r["box"], tr["box"])
                if i > best_iou:
                    best_iou, best_id = i, tid
            if best_id is not None and best_iou > 0.25:
                tid = best_id
            else:
                tid = self._next
                self._next += 1
            tr = self.tracks.setdefault(tid, {"box": r["box"], "last": now})
            tr["box"], tr["last"] = r["box"], now
            out.append(Det(tid, r["cls"], r["conf"], *r["box"]))
            matched.add(tid)
        self.tracks = {tid: tr for tid, tr in self.tracks.items()
                       if now - tr["last"] <= self.expire}
        return out


class SimDetector:
    name = "sim"

    def __init__(self, tracker):
        self.tracker = tracker

    def detect(self, frame, extras, now):
        raw = [{"cls": t["cls"], "conf": t["conf"], "box": t["box"]}
               for t in extras.get("truth", [])]
        return self.tracker.update(raw, now)


class SSDDetector:
    """MobileNet-SSD via cv2.dnn – CPU friendly, zero heavy dependencies."""

    name = "ssd"

    def __init__(self, prototxt, weights, conf=0.4, tracker=None):
        self.net = cv2.dnn.readNetFromCaffe(prototxt, weights)
        self.conf = conf
        self.tracker = tracker or Tracker()

    def detect(self, frame, extras, now):
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.00784,
                                     (300, 300), (127.5, 127.5, 127.5),
                                     swapRB=False, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()
        raw = []
        for i in range(out.shape[2]):
            conf = float(out[0, 0, i, 2])
            if conf < self.conf:
                continue
            label = SSD_LABELS[int(out[0, 0, i, 1])]
            label = RENAME.get(label, label)
            if label not in WANTED:
                continue
            x1, y1 = max(0, int(out[0, 0, i, 3] * w)), max(0, int(out[0, 0, i, 4] * h))
            x2, y2 = min(w, int(out[0, 0, i, 5] * w)), min(h, int(out[0, 0, i, 6] * h))
            if x2 - x1 < 12 or y2 - y1 < 12:
                continue
            raw.append({"cls": label, "conf": conf, "box": (x1, y1, x2 - x1, y2 - y1)})
        return self.tracker.update(raw, now)


_YOLO_LOCK = threading.Lock()
_YOLO_MODEL = None


class YOLODetector:
    name = "yolo"

    def __init__(self, model_path, conf=0.4, tracker=None):
        self.model_path = model_path
        self.conf = conf
        self.tracker = tracker or Tracker()

    def detect(self, frame, extras, now):
        global _YOLO_MODEL
        with _YOLO_LOCK:
            if _YOLO_MODEL is None:
                from ultralytics import YOLO
                _YOLO_MODEL = YOLO(self.model_path)
            results = _YOLO_MODEL(frame, conf=self.conf, imgsz=640, verbose=False)
        raw = []
        r = results[0]
        for b in r.boxes:
            label = r.names[int(b.cls[0])]
            if label not in WANTED or float(b.conf[0]) < self.conf:
                continue
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
            raw.append({"cls": label, "conf": float(b.conf[0]),
                        "box": (x1, y1, x2 - x1, y2 - y1)})
        return self.tracker.update(raw, now)


def build_detector(mode, source, cfg):
    if mode == "sim" or (mode == "auto" and getattr(source, "name", None) == "synthetic"):
        return SimDetector(Tracker(cfg["track_expire"]))
    if mode == "yolo" or (mode == "auto" and cfg.get("yolo_model")
                          and os.path.exists(cfg["yolo_model"])):
        return YOLODetector(cfg["yolo_model"], cfg["conf"], Tracker(cfg["track_expire"]))
    if cfg.get("ssd_weights") and os.path.exists(cfg["ssd_weights"]):
        return SSDDetector(cfg["ssd_prototxt"], cfg["ssd_weights"], cfg["conf"],
                           Tracker(cfg["track_expire"]))
    return SimDetector(Tracker(cfg["track_expire"]))
