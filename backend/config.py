"""IBVAP configuration – every knob is overridable via environment variables."""
import os
from dataclasses import dataclass


def _env(name: str, default, cast=str):
    v = os.environ.get(name)
    if v is None or v == "":
        return cast(default)
    return cast(v)


@dataclass
class Settings:
    # server
    host: str = _env("IBVAP_HOST", "0.0.0.0")
    port: int = _env("IBVAP_PORT", 8000, int)
    secret: str = _env("IBVAP_SECRET", "ibvap-dev-secret-change-me-0123456789")
    token_ttl_hours: int = _env("IBVAP_TOKEN_TTL_HOURS", 12, int)

    # storage
    db_path: str = _env("IBVAP_DB", "data/ibvap.db")
    media_dir: str = _env("IBVAP_MEDIA", "data/media")

    # detection
    detector: str = _env("IBVAP_DETECTOR", "auto")   # auto | ssd | yolo | sim
    ssd_weights: str = _env("IBVAP_SSD_WEIGHTS", "models/mobilenet_iter_73000.caffemodel")
    ssd_prototxt: str = _env("IBVAP_SSD_PROTOTXT", "models/object_detection_caffe.prototxt")
    yolo_model: str = _env("IBVAP_YOLO_MODEL", "")
    conf: float = _env("IBVAP_CONF", 0.4, float)
    frame_width: int = _env("IBVAP_FRAME_WIDTH", 640, int)   # analytics stream width
    cpu_threads: int = _env("IBVAP_CPU_THREADS", 2, int)

    # event engine
    clip_seconds: int = _env("IBVAP_CLIP_SECONDS", 20, int)   # evidence clip length
    ring_fps: int = _env("IBVAP_RING_FPS", 2, int)
    loiter_seconds: float = _env("IBVAP_LOITER_SECONDS", 15, float)
    intrusion_cooldown: float = _env("IBVAP_INTRUSION_COOLDOWN", 25, float)
    track_expire: float = _env("IBVAP_TRACK_EXPIRE", 1.6, float)
    event_max_age: float = _env("IBVAP_EVENT_MAX_AGE", 90, float)
    event_stable_gap: float = _env("IBVAP_EVENT_STABLE_GAP", 3.0, float)

    # live view
    mjpeg_interval: float = _env("IBVAP_MJPEG_INTERVAL", 0.12, float)

    # detection alerts (person-in-frame, no zone required)
    detect_alert_classes: str = _env("IBVAP_DETECT_CLASSES", "person")  # comma-separated
    detect_cooldown: float = _env("IBVAP_DETECT_COOLDOWN", 30, float)  # seconds between alerts per-track


settings = Settings()
