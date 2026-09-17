# IBVAP Administrator Guide

*Installation, configuration, operations, backup and troubleshooting.*

---

## 1. System requirements

| Item | Minimum (pilot, ≤ 50 cams) | Recommended (≤ 200 cams) |
|---|---|---|
| CPU | 8 cores (x86-64, AVX2) | 16–32 cores (Xeon/EPYC) |
| RAM | 32 GB | 64–128 GB |
| Storage | 1 TB (fast disk) + 5 TB NAS | 10 TB NAS/SAN |
| Network | 100 Mbps (inside SSB VPN) | 1 Gbps |
| OS | Ubuntu Server 22.04/24.04 | same |
| GPU | **not required** | optional (2–4× headroom) |

## 2. Installation

### 2.1 From source (dev / pilot)
```bash
git clone <repo> ibvap && cd ibvap
pip install -r requirements-ai.txt     # CPU torch + ultralytics
bash scripts/fetch_demo_assets.sh      # YOLOv8n + demo video
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 2.2 Docker (production)
```bash
cp .env.example .env
# edit .env → IBVAP_SECRET (32+ chars), detector, thresholds
docker build -t ibvap:0.1.0 .
docker compose up -d
curl -s localhost:8000/api/system/status   # healthcheck
```
Put nginx in front for TLS (internal CA / SSB PKI) and MFA; never expose
port 8000 outside the VPN.

### 2.3 First-boot behaviour
Seeds demo users/BOPs/cameras/zones only on an **empty database**. Create
real users (Admin tab), delete demo cameras (Cameras tab), register real
cameras by RTSP URL, draw zones per BOP.

## 3. Configuration reference (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `IBVAP_SECRET` | — | **must change** — JWT signing key, 32+ chars |
| `IBVAP_DETECTOR` | `auto` | `auto` (sim for demo scenes, YOLO for real feeds) · `yolo` · `ssd` · `sim` |
| `IBVAP_YOLO_MODEL` | `models/yolov8n.pt` | any ultralytics .pt; swap = drop file + restart |
| `IBVAP_CONF` | `0.4` | detection confidence gate (raise → fewer false alarms) |
| `IBVAP_FRAME_WIDTH` | `640` | analytics resolution (max edge) |
| `IBVAP_LOITER_SECONDS` | `15` | dwell time that fires loitering |
| `IBVAP_INTRUSION_COOLDOWN` | `25` | min seconds between intrusions per track×zone |
| `IBVAP_CLIP_SECONDS` | `20` | evidence clip length (ring buffer) |
| `IBVAP_EVENT_MAX_AGE` | `90` | force-close open events after |
| `IBVAP_TOKEN_TTL_HOURS` | `12` | JWT lifetime |
| `IBVAP_DB` / `IBVAP_MEDIA` | `data/…` | SQLite file / media root (use NAS mount) |
| `IBVAP_CPU_THREADS` | `2` | OpenCV threads (tune to cores / camera count) |

Tune **per deployment, not per incident**: after 2 weeks of ops, set
`IBVAP_CONF` and zone thresholds so false alarms < 5% (target in proposal §12).

## 4. User & RBAC administration

Admin tab → create users (admin / operator / viewer). Assign one operator
per BOP + one viewer for the sector command centre. Disable (not delete)
departed users so the audit trail stays consistent. All user changes are
audit-logged (who/what/when).

### 4.1 Audit trail

Every privileged action is written to the `audit` table — **login**,
**user.add**, **camera.add / camera.delete**, **zone.add / zone.delete**,
**bop.add**, and **event.ack** (who, what, when). View it in the console
(Admin → **Audit trail**) or via API:

```
GET /api/admin/audit?limit=100        # admin only (403 for operator/viewer)
→ [{"id":41,"user":"operator","action":"event.ack",
    "detail":"event 312","at":"2026-09-14T10:41:22Z"}, …]
```

Backups (Section 6) capture the audit table, so the trail survives a
rebuild. Export for an inspection by pulling the last N rows before the
visit — the table is append-only.

## 5. Camera operations

* **Add**: Cameras tab (or `POST /api/cameras`). Prefer the camera's
  *sub-stream* RTSP URL (lower bandwidth); main stream is fine for ≤ 50 cams.
* **Verify**: status goes `online` in ~10 s; watch a frame or two for sane
  detection before drawing zones.
* **Failover rule**: if a camera stays `offline` > 5 min, check (1) VPN link,
  (2) camera power/poE, (3) RTSP URL credentials — the worker auto-retries
  with 1 s→60 s backoff and needs no restart.

## 6. Backup & restore

```bash
# nightly (cron): DB + media
pg_dump ibvap > /backup/ibvap-$(date +%F).sql     # prod (PostgreSQL)
# reference build: cp data/ibvap.db /backup/
rsync -a data/media/ /backup/media/               # or snapshot the NAS volume
```
* **RTO target**: 15 min (restore volume → `docker compose up -d`).
* **Retention**: DB forever; clips 30–90 days (policy `IBVAP_CLIP_SECONDS`
  + pruning job); snapshots 90 days (searchable summary lives in the DB).

## 7. Troubleshooting

| Symptom | First checks |
|---|---|
| Camera red / `offline` | VPN reachability (`ffprobe rtsp://…` from server), camera sub-stream URL, PoE |
| Live view shows image but no boxes | `GET /api/system/status` → `yolo_model` present? `IBVAP_CONF` too high? detector logs |
| Too many false alarms | raise `IBVAP_CONF` (0.4→0.5), shrink/shift zone polygons, raise `IBVAP_LOITER_SECONDS` |
| Missed a real intrusion | zone polygon too small (redraw with 2–3 m margin), check camera angle/IR, multi-frame: re-record and replay through video source |
| Alerts slow on some devices | WS dropped → client auto-polls every 3 s (check `polling` chip); otherwise VPN congestion |
| Events exist but no clip | event still `active` — clip finalises on close; or media disk full (`df -h`) |
| Login loops / 401 | clock skew (JWT exp) → NTP sync; wrong role after user edit → re-login |
| High CPU on server | cameras × FPS budget: `n_cameras × 4 fps × 73 ms` should be < 70% of cores; drop `IBVAP_FRAME_WIDTH` to 512 or add a node |
| Dashboard won't load | server reachable? `curl :8000/api/system/status` (needs token) — check Docker healthcheck, TLS at proxy |

**Diagnostics**: `GET /api/system/status` (per-camera fps/status, detector
mode, uptime) · structured logs (`camera`, `worker`, `detector`, `rules`,
`alerts`) · audit table for any human action.

## 8. Upgrades & model changes

* **App**: build new image → deploy to standby (or rolling) → flip LB →
  healthcheck-gated. Zero-downtime for dashboards.
* **Model**: place weights in the model store (hash-verified), point
  `IBVAP_YOLO_MODEL` at it, rolling restart. A/B per camera possible via
  `source_config` (pilot new weights on 10 cameras first).
* **DB migrations**: run before app swap; schema changes are additive in
  v1 (see `backend/db.py` / ARCHITECTURE.md §7).
