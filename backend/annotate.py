"""Server-side frame annotation (boxes, zones, watermark) – keeps clients dumb."""
import time

import cv2
import numpy as np

CLS_COLORS = {
    "person": (80, 200, 255),
    "car": (80, 80, 255),
    "bus": (140, 60, 255),
    "truck": (120, 200, 60),
    "motorcycle": (100, 100, 220),
}


def _zone_pts(points, w, h):
    """Returns (px (N,2) float, poly (N,1,2) int32) for labelling + drawing."""
    pts_px = np.array(points, dtype=np.float32) * np.array([w, h], dtype=np.float32)
    poly = pts_px.astype(np.int32).reshape((-1, 1, 2))
    return pts_px, poly


def draw_frame(frame, dets, zones, cam_name, now, active_zone_ids=(), clean=False):
    """Render annotations. clean=True skips zone overlays (zone-editor base)."""
    f = frame.copy()
    h, w = f.shape[:2]

    if not clean:
        for z in zones:
            pts_px, poly = _zone_pts(z["points"], w, h)
            hot = z["id"] in active_zone_ids
            color = (60, 60, 255) if hot else (80, 200, 90)
            ov = f.copy()
            cv2.polylines(ov, [poly], True, color, 2)
            cv2.addWeighted(ov, 0.9 if hot else 0.55, f, 0.4, 0, f)
            label = z["name"].upper()
            cx = int(pts_px[:, 0].mean())
            ty = max(14, int(pts_px[:, 1].min()) - 6)
            cv2.putText(f, label, (max(4, min(cx - 40, w - 130)), ty),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    for d in dets:
        color = CLS_COLORS.get(d.cls, (255, 255, 255))
        cv2.rectangle(f, (d.x, d.y), (d.x + d.w, d.y + d.h), color, 2)
        text = f"{d.cls} {d.conf:.2f} #{d.track_id}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        ly = d.y - 6 if d.y - 6 - th > 2 else d.y + th + 6
        cv2.rectangle(f, (d.x, ly - th - 3), (d.x + tw + 6, ly + 2), color, -1)
        cv2.putText(f, text, (d.x + 3, ly - 3), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (20, 20, 20), 1, cv2.LINE_AA)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)) + " UTC"
    cv2.putText(f, f"IBVAP · {cam_name}", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    (tw, _), _ = cv2.getTextSize(stamp, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(f, stamp, (w - tw - 10, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1, cv2.LINE_AA)
    return f
