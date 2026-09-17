# IBVAP — Intelligent Border Video Analytics Platform

Working reference implementation of the system architecture in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), for the SSB / MoHA proposal
(Problem Statement 26187). CPU-only, open-source, zero new BOP hardware.

## What you get out of the box

A live, self-contained ops console (no build step, no CDN — runs offline):

* **Live camera wall** (MJPEG, server-annotated) — 4 demo cameras:
  * 3 procedural border scenes (IR night / day / dusk) with moving
    persons & vehicles,
  * 1 **real CNN camera**: YOLOv8n detecting real people/vehicles in
    recorded crosswalk footage (loops).
* **Virtual fence intrusion + loitering** — draw any polygon zone remotely
  in the Zone Editor; breaches fire events automatically.
* **Real-time alerts** — WebSocket push with on-screen toast feed **and an
  optional audible alert** (🔔/🔕 toggle, per-severity tones), one-click ACK,
  HTTP-poll fallback for flaky links.
* **Event database** — filterable, searchable, with evidence:
  snapshot JPG at moment of breach + 20-second MP4 evidence clip
  (10 s pre-roll) finalised when the event closes.
* **AuthN/AuthZ + audit** — JWT login, RBAC (admin / operator / viewer);
  every privileged action is logged and browsable (Admin → **Audit trail**,
  `GET /api/admin/audit`).
* **REST API** for C2 integration (events, clips, status, cameras, zones, reports, audit).
* **Reports & analytics** — `GET /api/reports/summary` + console tab: total/
  active/acked/closed cards, daily trend chart (7/30/90-day window),
  type & severity mix, per-camera event load, average event duration.
* **BOP map** — offline schematic deployment map: BOPs plotted from GPS
  coordinates, cameras status-coloured (online/offline), click a BOP to focus
  its camera list. No tiles/internet required (works in the field).
* **Automated test suite** — 27 tests (geometry, tracker, event engine, full
  API incl. WebSocket, frame→alert latency) in `tests/`, all green in ~20 s
  (sim detector, temp DB).
* **KPI verification** — `scripts/measure_kpis.py` measures the proposal's
  headline numbers end-to-end (fence-crossing → WebSocket alert latency,
  event precision/recall vs ground truth, real YOLOv8n inference audit) and
  writes [`docs/KPI_VERIFICATION.md`](docs/KPI_VERIFICATION.md).

Demo accounts: `admin / admin123` · `operator / operator123` · `viewer / viewer123`

## Quickstart

```bash
pip install -r requirements-ai.txt     # core + torch/ultralytics (CPU)
                                       # (or: pip install -r requirements.txt
                                       #  and the demo runs in sim mode)
bash scripts/fetch_demo_assets.sh      # model weights + demo video
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
# → open http://localhost:8000
```

Production: `docker build -t ibvap . && docker compose up -d`
(env template: `.env.example`).

## Running the tests

```bash
pip install -r requirements.txt pytest httpx
python -m pytest tests/ -q        # 27 tests, ~20 s
```

`tests/conftest.py` isolates every run: temp SQLite DB + media dir, `sim`
detector, no model weights required — CI (`.github/workflows/ci.yml`) runs the
same suite on every push/PR.

## Repository map

| Path | What |
|---|---|
| `docs/ARCHITECTURE.md` | **Full system architecture** (17 sections) |
| `diagrams/` | 5 SVG diagrams (deployment, logical, pipeline, sequence, ER) |
| `docs/USER_MANUAL.md` | BOP operator manual (live view, alerts, events, zones) |
| `docs/ADMIN_GUIDE.md` | Installation, config, ops, backup, **troubleshooting** |
| `docs/API_REFERENCE.md` | Complete REST + WebSocket contracts with examples |
| `docs/EXECUTIVE_SUMMARY.md` | 1-page summary for quick review |
| `docs/EXECUTIVE_SUMMARY.docx` | Printable executive summary (8 sections, 5 tables) |
| `docs/TRAINING_SCRIPT.md` | 2-hour bilingual (Hindi/English) BOP operator training script + quick-ref cards |
| `docs/KPI_VERIFICATION.md` | **Measured** proposal KPIs: alert latency, precision/recall, YOLO audit |
| `docs/budget/IBVAP-Budget.xlsx` | Budget model: one-time, scaling, annual, 5-yr TCO, ROI (6 sheets) |
| `docs/presentation/IBVAP-Proposal-Deck.pptx` | 14-slide proposal deck (16:9) |
| `tests/` | 27 pytest tests: geometry, tracker, event engine, full API, latency (sim detector, temp DB) |
| `scripts/measure_kpis.py` | KPI harness → `docs/KPI_VERIFICATION.md` (latency, precision/recall, YOLO audit) |
| `scripts/fetch_demo_assets.sh` | Downloads YOLOv8n weights + demo video |
| `.github/workflows/ci.yml` | CI: pytest + compileall on push/PR |
| `backend/` | FastAPI app: ingestion → detection → rules → events → alerts |
| `frontend/index.html` | Ops console (live wall, alerts + audio, events, **camera registration**, zones, **reports**, **BOP map**, admin + **audit**) |
| `Dockerfile`, `docker-compose.yml`, `.env.example` | Production deployment |

### Real cameras

Register any RTSP camera from the web UI (or API):
`POST /api/cameras {"bop_id":1,"name":"CAM-05","source_type":"rtsp",
"source_config":{"url":"rtsp://user:pass@bop-cam/h264"}` — it appears in the
wall within ~10 s. All production guidance (sizing, HA, security, scaling)
is in the architecture document.
