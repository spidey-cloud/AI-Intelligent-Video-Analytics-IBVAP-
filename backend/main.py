"""IBVAP reference platform – FastAPI application.

Wires together: camera workers (ingestion → detection → rule engine),
event DB, REST API, MJPEG live view, WebSocket alert hub and the
self-contained web dashboard.

Run:  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import json
import os
import queue
import threading
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import (Depends, FastAPI, HTTPException, Query, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import (FileResponse, HTMLResponse, Response,
                               StreamingResponse)

from . import auth, db
from . import models as m
from .alerts import AlertHub
from .annotate import draw_frame
from .config import settings
from .detection import build_detector
from .events import EventEngine
from .sources import build_source, resize_to_width

hub = AlertHub()
frame_store = {}
store_lock = threading.Lock()
jobs = {}
cam_names = {}
START = time.time()

DET_CFG = {
    "mode": settings.detector,
    "conf": settings.conf,
    "track_expire": settings.track_expire,
    "ssd_weights": settings.ssd_weights,
    "ssd_prototxt": settings.ssd_prototxt,
    "yolo_model": settings.yolo_model or "models/yolov8n.pt",
}


def store_set(cam_id, frame, dets, now):
    with store_lock:
        frame_store[cam_id] = {"frame": frame, "dets": dets, "ts": now}


def store_get(cam_id):
    with store_lock:
        return frame_store.get(cam_id)


# ---------------------------------------------------------------------------
# Camera worker
# ---------------------------------------------------------------------------
class CameraJob:
    """One thread per camera: read → resize → detect → rules → frame store."""

    def __init__(self, cam, det_cfg):
        self.cam = cam
        self.id = cam["id"]
        self.name = cam["name"]
        self.running = True
        self.status = "offline"
        self.fps = 0.0
        self.source = build_source(json.loads(cam["source_config"]))
        self.detector = build_detector(det_cfg["mode"], self.source, det_cfg)
        self.engine = EventEngine(self.id, settings.media_dir, settings, hub, self.name)
        self._n, self._t0 = 0, time.time()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def stop(self):
        self.running = False

    def _run(self):
        while self.running:
            try:
                frame, extras = self.source.read()
            except Exception:
                frame = None
            if frame is None:
                if self.status != "offline":
                    self.status = "offline"
                    db.update_camera_status(self.id, "offline")
                    hub.push({"kind": "camera_status", "camera_id": self.id,
                              "camera_name": self.name, "status": "offline"})
                time.sleep(1.0)
                continue
            if self.status != "online":
                self.status = "online"
                db.update_camera_status(self.id, "online")
                hub.push({"kind": "camera_status", "camera_id": self.id,
                          "camera_name": self.name, "status": "online"})
            now = time.time()
            frame = resize_to_width(frame, settings.frame_width)
            dets = self.detector.detect(frame, extras, now)
            self.engine.process(frame, dets, now)
            self.engine.ring.tick(frame, now)
            store_set(self.id, frame, dets, now)
            self._n += 1
            if now - self._t0 >= 2:
                self.fps = self._n / (now - self._t0)
                self._n, self._t0 = 0, now
            time.sleep(max(0.0, self.source.target_interval))


# ---------------------------------------------------------------------------
# Seeding (first boot)
# ---------------------------------------------------------------------------
def seed():
    if not db.list_users():
        db.add_user("admin", auth.hash_password("admin123"), "admin", "System Administrator")
        db.add_user("operator", auth.hash_password("operator123"), "operator", "BOP Operator")
        db.add_user("viewer", auth.hash_password("viewer123"), "viewer", "Command Centre Viewer")
    if not db.list_bops():
        b1 = db.add_bop("BOP-01", "North Gate BOP", 28.25, 82.10)
        b2 = db.add_bop("BOP-02", "West Approach BOP", 28.21, 82.02)
        b3 = db.add_bop("BOP-03", "Border Checkpost BOP", 28.29, 82.18)
        cams = [
            (b1, "CAM-01 · North Gate (IR night)", "synthetic", {"scene": "north-gate"}),
            (b2, "CAM-02 · West Approach (day)", "synthetic", {"scene": "west-approach"}),
            (b3, "CAM-03 · Checkpost Gate (dusk)", "synthetic", {"scene": "checkpoint"}),
        ]
        if os.path.exists("data/videos/crosswalk.mp4"):
            b4 = db.add_bop("BOP-04", "Recorded Evidence Room", 28.27, 82.14)
            cams.append((b4, "CAM-04 · Crosswalk (CNN feed)", "video",
                         {"type": "video", "path": "data/videos/crosswalk.mp4"}))
        for bop_id, name, stype, scfg in cams:
            db.add_camera(bop_id, name, stype, scfg)
    if not db.list_zones():
        cams = db.list_cameras()
        if len(cams) >= 3:
            db.add_zone(cams[0]["id"], "Perimeter fence line", "perimeter",
                        [[0.20, 0.27], [0.78, 0.27], [0.78, 0.50], [0.20, 0.50]])
            db.add_zone(cams[1]["id"], "Gate approach zone", "perimeter",
                        [[0.78, 0.45], [0.98, 0.45], [0.98, 0.85], [0.78, 0.85]])
            db.add_zone(cams[2]["id"], "No-entry zone (gate)", "restricted",
                        [[0.24, 0.28], [0.66, 0.28], [0.66, 0.55], [0.24, 0.55]])
    for c in db.list_cameras():
        cam_names[c["id"]] = c["name"]
    db.log_audit(1, "seed", "defaults initialised")


def _warmup_model():
    p = DET_CFG["yolo_model"]
    if not p or not os.path.exists(p):
        return
    try:
        from . import detection as det_mod
        from ultralytics import YOLO
        with det_mod._YOLO_LOCK:
            det_mod._YOLO_MODEL = YOLO(p)
            det_mod._YOLO_MODEL(np.zeros((360, 640, 3), dtype="uint8"), verbose=False)
        print(f"[ibvap] YOLO model ready: {p}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[ibvap] YOLO warmup failed: {e}", flush=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    cv2.setNumThreads(settings.cpu_threads)
    db.init(settings.db_path)
    os.makedirs(settings.media_dir, exist_ok=True)
    seed()
    _warmup_model()
    for cam in db.list_cameras():
        jobs[cam["id"]] = CameraJob(cam, DET_CFG)
    print(f"[ibvap] started – {len(jobs)} cameras", flush=True)
    yield
    for j in jobs.values():
        j.stop()


app = FastAPI(title="IBVAP – Intelligent Border Video Analytics Platform",
              version="0.1.0", lifespan=lifespan)


# -- auth -------------------------------------------------------------------
@app.post("/api/auth/login")
def api_login(body: m.Login):
    u = db.get_user_by_name(body.username.strip())
    if not u or not auth.verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    db.log_audit(u["id"], "login")
    return {"token": auth.create_token(u),
            "user": {"id": u["id"], "username": u["username"],
                     "role": u["role"], "full_name": u["full_name"]}}


@app.get("/api/auth/me")
def api_me(user=Depends(auth.get_user)):
    u = db.get_user_by_id(user["uid"])
    if not u:
        raise HTTPException(401, "User disabled")
    return {"user": {"id": u["id"], "username": u["username"],
                     "role": u["role"], "full_name": u["full_name"]}}


# -- BOPs -------------------------------------------------------------------
@app.get("/api/bops")
def api_bops(user=Depends(auth.get_user)):
    return db.list_bops()


@app.post("/api/bops", status_code=201)
def api_add_bop(body: m.BopIn, user=Depends(auth.require_role("admin"))):
    bid = db.add_bop(body.code, body.name, body.lat, body.lng)
    db.log_audit(user["uid"], "bop.add", body.code)
    return {"id": bid}


# -- cameras ------------------------------------------------------------------
@app.get("/api/cameras")
def api_cameras(user=Depends(auth.get_user)):
    return db.list_cameras()


@app.post("/api/cameras", status_code=201)
def api_add_camera(body: m.CameraIn, user=Depends(auth.get_user)):
    if not db.get_bop(body.bop_id):
        raise HTTPException(400, "Unknown BOP")
    if body.source_type not in ("rtsp", "video", "synthetic"):
        raise HTTPException(400, "Unknown source type")
    cid = db.add_camera(body.bop_id, body.name, body.source_type, body.source_config)
    cam = db.get_camera(cid)
    jobs[cid] = CameraJob(cam, DET_CFG)
    cam_names[cid] = cam["name"]
    db.log_audit(user["uid"], "camera.add", body.name)
    return db.list_cameras()


@app.delete("/api/cameras/{cid}")
def api_del_camera(cid: int, user=Depends(auth.require_role("admin", "operator"))):
    j = jobs.pop(cid, None)
    if j:
        j.stop()
    db.delete_camera(cid)
    cam_names.pop(cid, None)
    db.log_audit(user["uid"], "camera.delete", str(cid))
    return {"ok": True}


@app.get("/api/cameras/{cid}/snapshot")
def api_snapshot(cid: int, clean: int = 0, user=Depends(auth.get_user)):
    st = store_get(cid)
    if st is None:
        raise HTTPException(404, "No frames from this camera yet")
    zones = [dict(z, points=json.loads(z["points"])) for z in db.list_zones(cid)]
    img = draw_frame(st["frame"], st["dets"], zones,
                     cam_names.get(cid, f"CAM-{cid}"), st["ts"], clean=bool(clean))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return Response(content=buf.tobytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/stream/{cid}")
def api_stream(cid: int, user=Depends(auth.get_user)):
    """MJPEG live view (annotated server-side). Robust through HTTP proxies."""
    if cid not in jobs:
        raise HTTPException(404, "Unknown camera")

    def gen():
        while True:
            st = store_get(cid)
            if st is None:
                time.sleep(1.0)
                continue
            zones = [dict(z, points=json.loads(z["points"])) for z in db.list_zones(cid)]
            now = time.time()
            active = {zid for (tid, zid), t in jobs[cid].engine.zone_last_fire.items()
                      if now - t < 4}
            img = draw_frame(st["frame"], st["dets"], zones,
                             cam_names.get(cid, f"CAM-{cid}"), st["ts"], active)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            time.sleep(settings.mjpeg_interval)

    return StreamingResponse(gen(),
                             media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store"})


# -- zones --------------------------------------------------------------------
@app.get("/api/zones")
def api_zones(camera_id: int = 0, user=Depends(auth.get_user)):
    zs = db.list_zones(camera_id or None)
    for z in zs:
        z["points"] = json.loads(z["points"])
    return zs


@app.post("/api/cameras/{cid}/zones", status_code=201)
def api_add_zone(cid: int, body: m.ZoneIn, user=Depends(auth.get_user)):
    if not db.get_camera(cid):
        raise HTTPException(404, "Unknown camera")
    if len(body.points) < 3:
        raise HTTPException(400, "A zone needs at least 3 points")
    zid = db.add_zone(cid, body.name, body.kind, body.points, body.color)
    db.log_audit(user["uid"], "zone.add", body.name)
    return {"id": zid}


@app.delete("/api/zones/{zid}")
def api_del_zone(zid: int, user=Depends(auth.get_user)):
    db.delete_zone(zid)
    db.log_audit(user["uid"], "zone.delete", str(zid))
    return {"ok": True}


# -- events ---------------------------------------------------------------------
@app.get("/api/events")
def api_events(camera_id: int = 0,
               etype: str = Query(None, alias="type"),
               status: str = None,
               q: str = None,
               since: str = None,
               limit: int = 100,
               user=Depends(auth.get_user)):
    return db.list_events(camera_id or None, etype, status, q, since, min(limit, 500))


@app.post("/api/events/{eid}/ack")
def api_ack(eid: int, user=Depends(auth.get_user)):
    ev = db.get_event(eid)
    if not ev:
        raise HTTPException(404, "Unknown event")
    if ev["status"] == "active":
        db.update_event(eid, status="acknowledged")
    db.log_audit(user["uid"], "event.ack", str(eid))
    return db.get_event(eid)


@app.get("/api/events/{eid}/snapshot")
def api_ev_snapshot(eid: int, user=Depends(auth.get_user)):
    ev = db.get_event(eid)
    if not ev or not ev.get("snapshot") or not os.path.exists(ev["snapshot"]):
        raise HTTPException(404, "Snapshot not available")
    return FileResponse(ev["snapshot"], media_type="image/jpeg")


@app.get("/api/events/{eid}/clip")
def api_ev_clip(eid: int, user=Depends(auth.get_user)):
    ev = db.get_event(eid)
    if not ev or not ev.get("clip") or not os.path.exists(ev["clip"]):
        raise HTTPException(404, "Clip not finalised yet (event still open)")
    return FileResponse(ev["clip"], media_type="video/mp4")


# -- admin -----------------------------------------------------------------------
@app.get("/api/admin/users")
def api_users(user=Depends(auth.require_role("admin"))):
    return db.list_users()


@app.post("/api/admin/users", status_code=201)
def api_add_user(body: m.UserIn, user=Depends(auth.require_role("admin"))):
    if body.role not in ("admin", "operator", "viewer"):
        raise HTTPException(400, "Role must be admin|operator|viewer")
    try:
        uid = db.add_user(body.username, auth.hash_password(body.password),
                          body.role, body.full_name)
    except Exception:  # noqa: BLE001
        raise HTTPException(409, "Username already exists")
    db.log_audit(user["uid"], "user.add", body.username)


@app.get("/api/admin/audit")
def api_audit(limit: int = Query(50, ge=1, le=200),
              user=Depends(auth.require_role("admin"))):
    """Audit trail (proposal §8.2/§9: every privileged action is logged)."""
    return db.list_audit(limit)
    return {"id": uid}


# -- reports ------------------------------------------------------------------------
@app.get("/api/reports/summary")
def api_reports(days: int = 7, camera_id: int = 0, user=Depends(auth.get_user)):
    from datetime import datetime, timedelta, timezone
    days = max(1, min(days, 90))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    return db.event_stats(since=since, camera_id=camera_id or None)


# -- system / alerts -----------------------------------------------------------------
@app.get("/api/system/status")
def api_status(user=Depends(auth.get_user)):
    return {
        "uptime_sec": int(time.time() - START),
        "detector_mode": settings.detector,
        "yolo_model": DET_CFG["yolo_model"]
        if os.path.exists(DET_CFG["yolo_model"]) else None,
        "cameras": [{"id": c["id"], "name": c["name"],
                     "status": jobs[c["id"]].status,
                     "fps": round(jobs[c["id"]].fps, 1)}
                    for c in db.list_cameras() if c["id"] in jobs],
    }


@app.get("/api/alerts/recent")
def api_recent(user=Depends(auth.get_user)):
    return list(hub.recent)


# -- websocket ------------------------------------------------------------------------
@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):
    token = ws.query_params.get("token", "")
    try:
        auth.decode_token(token)
    except HTTPException:
        await ws.close(code=4401)
        return
    await ws.accept()
    q = hub.subscribe()
    try:
        for msg in list(hub.recent)[:20]:
            await ws.send_text(json.dumps(msg))

        async def idle_ping() -> None:
            while True:
                await asyncio.sleep(25)
                await ws.send_text(json.dumps({"kind": "ping"}))

        async def consume_client() -> None:
            # Raises WebSocketDisconnect the moment the client closes.
            while True:
                await ws.receive_text()

        async def deliver() -> None:
            # Bounded blocking get: q.get with timeout=1.0 so the underlying
            # executor thread can never outlive event-loop shutdown (the loop
            # joins its default executor on close; an unbounded q.get would
            # deadlock it).
            while True:
                msg = await asyncio.to_thread(_queue_get_1s, q)
                if msg is not None:
                    await ws.send_text(json.dumps(msg))

        await asyncio.gather(idle_ping(), consume_client(), deliver())
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001  (socket gone any other way)
        pass
    finally:
        hub.unsubscribe(q)


def _queue_get_1s(q):
    try:
        return q.get(timeout=1.0)
    except queue.Empty:
        return None


# -- dashboard ---------------------------------------------------------------------------
FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(FRONT, "index.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port)
