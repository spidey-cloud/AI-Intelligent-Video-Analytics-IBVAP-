"""Persistence layer.

Reference build uses SQLite (zero-dependency, single file). The schema mirrors
the production PostgreSQL design in docs/ARCHITECTURE.md §7 one-to-one, so the
swap is a driver + DDL dialect change only.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

_conn = None
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','operator','viewer')),
  full_name TEXT, active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bops (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  lat REAL, lng REAL,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cameras (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bop_id INTEGER NOT NULL REFERENCES bops(id),
  name TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'rtsp',     -- rtsp | video | synthetic
  source_config TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'perimeter',       -- perimeter | restricted | area
  color TEXT NOT NULL DEFAULT '#22c55e',
  points TEXT NOT NULL,                          -- JSON [[x_norm, y_norm], ...]
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  camera_id INTEGER NOT NULL,
  zone_id INTEGER,
  track_id INTEGER,
  class_name TEXT,
  type TEXT NOT NULL,                            -- intrusion | loitering
  severity TEXT NOT NULL,                        -- low | medium | high
  status TEXT NOT NULL DEFAULT 'active',         -- active | acknowledged | closed
  confidence REAL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  snapshot TEXT,
  clip TEXT,
  meta TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_started ON events(started_at);
CREATE INDEX IF NOT EXISTS idx_events_cam ON events(camera_id, started_at);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER REFERENCES events(id),
  channel TEXT NOT NULL,                         -- ws | sms | webhook
  payload TEXT,
  sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  action TEXT NOT NULL,
  detail TEXT,
  at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init(path: str):
    global _conn
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    with _lock:
        _conn.executescript(SCHEMA)
        _conn.commit()


def _q(sql, args=(), one=False):
    with _lock:
        cur = _conn.execute(sql, args)
        rows = cur.fetchall()
        _conn.commit()
        if one:
            r = rows[0] if rows else None
            return dict(r) if r else None
        return [dict(r) for r in rows]


def _qi(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur.lastrowid


# ---------------------------------------------------------------- users
def add_user(username, password_hash, role, full_name=""):
    return _qi("INSERT INTO users(username,password_hash,role,full_name,created_at) VALUES(?,?,?,?,?)",
               (username, password_hash, role, full_name, utcnow()))


def get_user_by_name(username):
    return _q("SELECT * FROM users WHERE username=? AND active=1", (username,), one=True)


def get_user_by_id(uid):
    return _q("SELECT * FROM users WHERE id=? AND active=1", (uid,), one=True)


def list_users():
    return _q("SELECT id,username,role,full_name,active,created_at FROM users ORDER BY id")


# ------------------------------------------------------------- bops/cams
def add_bop(code, name, lat=None, lng=None):
    return _qi("INSERT INTO bops(code,name,lat,lng) VALUES(?,?,?,?)", (code, name, lat, lng))


def get_bop(bop_id):
    return _q("SELECT * FROM bops WHERE id=?", (bop_id,), one=True)


def list_bops():
    return _q("SELECT * FROM bops ORDER BY code")


def add_camera(bop_id, name, source_type, source_config):
    return _qi("INSERT INTO cameras(bop_id,name,source_type,source_config,created_at) VALUES(?,?,?,?,?)",
               (bop_id, name, source_type, json.dumps(source_config), utcnow()))


def list_cameras():
    return _q("SELECT c.*, b.code AS bop_code FROM cameras c "
              "LEFT JOIN bops b ON b.id=c.bop_id ORDER BY c.id")


def get_camera(cid):
    return _q("SELECT * FROM cameras WHERE id=?", (cid,), one=True)


def update_camera_status(cid, status):
    _q("UPDATE cameras SET status=? WHERE id=?", (status, cid))


def delete_camera(cid):
    _q("DELETE FROM cameras WHERE id=?", (cid,))


# ----------------------------------------------------------------- zones
def add_zone(camera_id, name, kind, points, color="#22c55e"):
    return _qi("INSERT INTO zones(camera_id,name,kind,points,color) VALUES(?,?,?,?,?)",
               (camera_id, name, kind, json.dumps(points), color))


def list_zones(camera_id=None):
    if camera_id:
        return _q("SELECT * FROM zones WHERE camera_id=? AND active=1", (camera_id,))
    return _q("SELECT * FROM zones WHERE active=1")


def delete_zone(zid):
    _q("DELETE FROM zones WHERE id=?", (zid,))


# ---------------------------------------------------------------- events
def add_event(camera_id, zone_id, track_id, class_name, etype, severity,
              confidence, snapshot, meta=None):
    return _qi(
        "INSERT INTO events(camera_id,zone_id,track_id,class_name,type,severity,confidence,"
        "snapshot,meta,started_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (camera_id, zone_id, track_id, class_name, etype, severity, confidence, snapshot,
         json.dumps(meta or {}), utcnow(), utcnow()))


def get_event(eid):
    return _q("SELECT e.*, c.name AS camera_name, z.name AS zone_name FROM events e "
              "LEFT JOIN cameras c ON c.id=e.camera_id "
              "LEFT JOIN zones z ON z.id=e.zone_id WHERE e.id=?", (eid,), one=True)


def list_events(camera_id=None, etype=None, status=None, q=None, since=None, limit=200):
    sql = ("SELECT e.*, c.name AS camera_name, z.name AS zone_name FROM events e "
           "LEFT JOIN cameras c ON c.id=e.camera_id "
           "LEFT JOIN zones z ON z.id=e.zone_id WHERE 1=1")
    args = []
    if camera_id:
        sql += " AND e.camera_id=?"; args.append(camera_id)
    if etype:
        sql += " AND e.type=?"; args.append(etype)
    if status:
        sql += " AND e.status=?"; args.append(status)
    if since:
        sql += " AND e.started_at>=?"; args.append(since)
    if q:
        sql += " AND (e.class_name LIKE ? OR c.name LIKE ? OR e.type LIKE ?)"
        like = f"%{q}%"; args += [like, like, like]
    sql += " ORDER BY e.id DESC LIMIT ?"
    args.append(limit)
    return _q(sql, args)


def update_event(eid, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    _q(f"UPDATE events SET {sets} WHERE id=?", list(fields.values()) + [eid])


def close_event(eid, clip_path=None):
    _q("UPDATE events SET status=CASE WHEN status='active' THEN 'closed' ELSE status END, "
       "ended_at=?, clip=COALESCE(?, clip) WHERE id=?", (utcnow(), clip_path, eid))


# ------------------------------------------------------------- audit/log
def add_alert(event_id, channel, payload):
    _qi("INSERT INTO alerts(event_id,channel,payload,sent_at) VALUES(?,?,?,?)",
        (event_id, channel, json.dumps(payload), utcnow()))


def log_audit(user_id, action, detail=""):
    _qi("INSERT INTO audit(user_id,action,detail,at) VALUES(?,?,?,?)",
        (user_id, action, detail, utcnow()))


def list_audit(limit=50):
    """Recent audit rows (newest first) with the acting username resolved."""
    return _q(
        "SELECT a.id, a.action, a.detail, a.at, "
        "COALESCE(u.username, 'system') AS user "
        "FROM audit a LEFT JOIN users u ON u.id = a.user_id "
        "ORDER BY a.id DESC LIMIT ?", (int(limit),))


# ------------------------------------------------------------- reporting
def event_stats(since=None, camera_id=None):
    """Aggregations for the Reports view (proposal §8.2: stats & trends)."""
    def q(sql, args=()):
        with _lock:
            rows = _conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    cond, args = [], []
    if since:
        cond.append("e.started_at>=?"); args.append(since)
    if camera_id:
        cond.append("e.camera_id=?"); args.append(camera_id)
    where = (" WHERE " + " AND ".join(cond)) if cond else ""

    t = q(
        f"SELECT COUNT(*) total, SUM(e.status='active') active, "
        f"SUM(e.status='acknowledged') acked, SUM(e.status='closed') closed, "
        f"AVG(e.confidence) avg_conf FROM events e{where}", args)[0]
    totals = {
        "total": int(t["total"] or 0),
        "active": int(t["active"] or 0),
        "acked": int(t["acked"] or 0),
        "closed": int(t["closed"] or 0),
        "avg_conf": round(float(t["avg_conf"]), 3) if t["avg_conf"] else None,
    }
    by_type = q(f"SELECT type, COUNT(*) n FROM events e{where} GROUP BY type", args)
    by_severity = q(f"SELECT severity, COUNT(*) n FROM events e{where} GROUP BY severity", args)
    by_camera = q(
        f"SELECT COALESCE(c.name, 'unknown') camera, COUNT(*) n FROM events e "
        f"LEFT JOIN cameras c ON c.id=e.camera_id{where} GROUP BY 1 ORDER BY n DESC", args)
    by_day = q(
        f"SELECT substr(e.started_at, 1, 10) day, COUNT(*) n FROM events e{where} "
        f"GROUP BY 1 ORDER BY 1", args)

    dcond = cond + ["e.ended_at IS NOT NULL"]
    dwhere = " WHERE " + " AND ".join(dcond)
    rows = q(f"SELECT e.started_at s, e.ended_at e FROM events e{dwhere}", args)
    durs = []
    for row in rows:
        try:
            durs.append((datetime.strptime(row["e"], "%Y-%m-%dT%H:%M:%SZ")
                         - datetime.strptime(row["s"], "%Y-%m-%dT%H:%M:%SZ")).total_seconds())
        except Exception:
            pass

    return {
        "totals": totals,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_camera": by_camera,
        "by_day": by_day,
        "avg_duration_sec": round(sum(durs) / len(durs), 1) if durs else None,
    }
