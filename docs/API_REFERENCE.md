# IBVAP API Reference

Base: `http(s)://<host>:8000` · Auth: `Authorization: Bearer <JWT>`
(token from `POST /api/auth/login`). Media/static endpoints also accept
`?token=…` (for `<img>` tags and the MJPEG wall). JSON everywhere unless noted.

Error shape: `{"detail": "message"}` with 4xx/5xx status.
RBAC: **V** = viewer+, **O** = operator+, **A** = admin only.

---

## Auth

### `POST /api/auth/login` — V (public)
```json
// req
{"username": "operator", "password": "operator123"}
// 200
{"token": "eyJ…", "user": {"id": 2, "username": "operator",
  "role": "operator", "full_name": "BOP Operator"}}
// 401 invalid credentials
```

### `GET /api/auth/me` — V
```json
{"user": {"id": 2, "username": "operator", "role": "operator", "full_name": "BOP Operator"}}
```

## BOPs

### `GET /api/bops` — V
```json
[{"id": 1, "code": "BOP-01", "name": "North Gate BOP", "lat": 28.25, "lng": 82.10, "active": 1}]
```

### `POST /api/bops` — A
```json
// req
{"code": "BOP-05", "name": "East Gate BOP", "lat": 28.31, "lng": 82.22}
// 201  {"id": 5}
```

## Cameras

### `GET /api/cameras` — V
```json
[{"id": 1, "bop_id": 1, "name": "CAM-01 · North Gate (IR night)",
  "source_type": "synthetic", "source_config": "{\"scene\": \"north-gate\"}",
  "status": "online", "created_at": "2026-09-14T08:44:32Z", "bop_code": "BOP-01"}]
```

### `POST /api/cameras` — O
```json
// req
{"bop_id": 1, "name": "CAM-05 · East Gate", "source_type": "rtsp",
 "source_config": {"type": "rtsp", "url": "rtsp://user:pass@10.0.0.12/h264"}}
// source_type: rtsp | video | synthetic
//   rtsp:      {"type":"rtsp","url":"…","timeout_ms":4000}
//   video:     {"type":"video","path":"data/videos/clip.mp4"}
//   synthetic: {"type":"synthetic","scene":"north-gate|west-approach|checkpoint"}
// 201 → full camera list (new camera online within ~10 s)
```

### `DELETE /api/cameras/{id}` — A → `{"ok": true}`

### `GET /api/cameras/{id}/snapshot` — V
Latest **annotated** frame as JPEG (`?clean=1` → no zone overlays, used by
the Zone Editor). `404` until first frame.

### `GET /stream/{id}` — V
**MJPEG** stream (`multipart/x-mixed-replace; boundary=frame`), server-
annotated (boxes + zones + watermark), ~1.5 fps. Use as
`<img src="/stream/1?token=…">`. Robust through HTTP proxies/VPNs.

## Zones

### `GET /api/zones?camera_id=` — V
```json
[{"id": 1, "camera_id": 1, "name": "Perimeter fence line", "kind": "perimeter",
  "color": "#22c55e", "points": [[0.2, 0.27], [0.78, 0.27], [0.78, 0.5], [0.2, 0.5]],
  "active": 1}]
```
`points` are **normalised** (0..1 of frame width/height), any polygon ≥ 3 pts.

### `POST /api/cameras/{id}/zones` — O
```json
// req
{"name": "Gate approach", "kind": "perimeter",
 "points": [[0.78, 0.45], [0.98, 0.45], [0.98, 0.85], [0.78, 0.85]],
 "color": "#22c55e"}
// 201 {"id": 4}      // 400 if < 3 points; 404 unknown camera
```

### `DELETE /api/zones/{id}` — O → `{"ok": true}`

## Events

### `GET /api/events` — V
Query params: `camera_id`, `type` (`intrusion|loitering`), `status`
(`active|acknowledged|closed`), `q` (free text over class/camera/type),
`since` (ISO UTC), `limit` (≤ 500, default 100). Newest first.
```json
[{"id": 210, "camera_id": 1, "zone_id": 1, "track_id": 14,
  "class_name": "person", "type": "intrusion", "severity": "high",
  "status": "closed", "confidence": 0.88,
  "started_at": "2026-09-14T09:24:11Z", "ended_at": "2026-09-14T09:24:17Z",
  "snapshot": "data/media/snapshots/cam1_t1757…jpg",
  "clip": "data/media/clips/cam1_ev210.mp4",
  "meta": "{\"zone_kind\": \"perimeter\"}",
  "camera_name": "CAM-01 · North Gate (IR night)",
  "zone_name": "Perimeter fence line"}]
```

### `POST /api/events/{id}/ack` — O
`active → acknowledged` (audited). Returns the updated event.

### `GET /api/events/{id}/snapshot` — V → JPEG (404 if none)
### `GET /api/events/{id}/clip` — V → MP4 (404 while event still open)

## Reports

### `GET /api/reports/summary` — V
Analytics over the events table (powers the console **Reports** tab).

| Param | Type | Default | Notes |
|---|---|---|---|
| `days` | int | 7 | Window in days, clamped to 1–90 |
| `camera_id` | int | — | Optional single-camera filter |

```json
{
  "totals":         {"total": 344, "active": 3, "acked": 0, "closed": 341, "avg_conf": 0.899},
  "by_type":        [{"type": "intrusion", "n": 278}, {"type": "loitering", "n": 66}],
  "by_severity":    [{"severity": "high", "n": 278}, {"severity": "medium", "n": 66}],
  "by_camera":      [{"camera": "CAM-02 · West Approach (day)", "n": 172}],
  "by_day":         [{"day": "2026-09-14", "n": 344}],
  "avg_duration_sec": 10.2
}
```

All aggregates are SQL-side (`db.event_stats`); `by_day` is ISO-date buckets over the window.

## Admin

### `GET /api/admin/users` — A
Returns `[{id, username, role, full_name, created_at}, …]`.

### `POST /api/admin/users` — A
```json
// req
{"username": "jsharma", "password": "…", "role": "operator",
 "full_name": "J. Sharma"}
// 201 {"id": 7}      // 409 duplicate username
```

### `GET /api/admin/audit` — A
Audit trail — every privileged action (login, user add, camera add/delete,
zone add/delete, event ack) is written to the `audit` table (proposal §9:
"complete audit logging").

| Param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int | 50 | Rows returned, clamped to 1–200 |

```json
[{"id": 41, "user": "operator", "action": "event.ack",
  "detail": "event 312", "at": "2026-09-14T10:41:22Z"}]
```
`user` is the acting username (`system` for bootstrap entries). Rendered in
the console's Admin → "Audit trail" panel.

## System & realtime

### `GET /api/system/status` — V
```json
{"uptime_sec": 143, "detector_mode": "auto", "yolo_model": "models/yolov8n.pt",
 "cameras": [{"id": 1, "name": "CAM-01 …", "status": "online", "fps": 8.0}]}
```

### `GET /api/alerts/recent` — V
Last 300 realtime messages (poll fallback for the WebSocket).

### `WS /ws/realtime?token=…`
Server→client frames (JSON):
```json
{"kind": "alert", "event": {…public event…}}
{"kind": "event_closed", "event_id": 210}
{"kind": "camera_status", "camera_id": 1, "camera_name": "…", "status": "online"}
{"kind": "ping"}
```
On connect you receive the last 20 alerts (rejoin safety). Keepalive ping
every 25 s. Unauthenticated sockets are closed with code `4401`.

## C2 integration example
```bash
TOKEN=$(curl -s -X POST :8000/api/auth/login -d '{"username":"c2","password":"…"}' \
        -H 'Content-Type: application/json' | jq -r .token)
# watch new events (loop or webhook)
curl -s ":8000/api/events?since=2026-09-14T09:00:00Z&limit=50" -H "Authorization: Bearer $TOKEN"
```
