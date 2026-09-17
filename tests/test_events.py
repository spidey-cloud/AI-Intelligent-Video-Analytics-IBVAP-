"""Event engine: intrusion, loitering, cooldown, severity, lifecycle."""
import os
import time
import types

import numpy as np
import pytest

from backend import db
from backend.detection import Det
from backend.events import EventEngine


class _FakeAlerts:
    def __init__(self):
        self.msgs = []

    def push(self, m):
        self.msgs.append(m)


@pytest.fixture()
def env(tmp_path):
    db.init(str(tmp_path / "t.db"))
    db.add_bop("BOP-T", "Test BOP")
    cid = db.add_camera(1, "CAM-T", "synthetic", {"scene": "north-gate"})
    # zone: x 256..384, y 144..216 on a 640x360 frame
    db.add_zone(cid, "Z", "perimeter",
                [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]])
    s = types.SimpleNamespace(
        clip_seconds=4, ring_fps=2, loiter_seconds=0.5,
        intrusion_cooldown=100.0, track_expire=1.6,
        event_max_age=5.0, event_stable_gap=0.5,
        detect_alert_classes="person", detect_cooldown=30.0)
    alerts = _FakeAlerts()
    eng = EventEngine(cid, str(tmp_path / "media"), s, alerts, "CAM-T")
    return eng, alerts, cid


def _det(tid, cls="person", x=280, y=160):
    return Det(tid, cls, 0.9, x, y, 26, 52)  # centroid (293,186) -> inside zone


def _frame():
    return np.zeros((360, 640, 3), np.uint8)


def test_intrusion_fires(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)
    evs = db.list_events(camera_id=cid)
    assert len(evs) == 1
    e = evs[0]
    assert e["type"] == "intrusion" and e["severity"] == "high"
    assert e["status"] == "active"
    assert any(m["kind"] == "alert" for m in alerts.msgs)


def test_no_event_outside_zone(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1, x=20, y=20)], 1000.0)
    assert db.list_events(camera_id=cid) == []


def test_vehicle_is_medium_severity(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(2, cls="truck")], 1000.0)
    ev = db.list_events(camera_id=cid)[0]
    assert ev["severity"] == "medium"


def test_cooldown_suppresses_rapid_refire(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)   # intrusion
    eng.process(_frame(), [], 1001.0)          # dropout
    eng.process(_frame(), [_det(1)], 1002.0)   # still inside -> loitering OK,
    intr = [e for e in db.list_events(camera_id=cid) if e["type"] == "intrusion"]
    assert len(intr) == 1                      # but no 2nd intrusion (cooldown)


def test_loitering_fires_after_dwell(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)
    eng.process(_frame(), [_det(1)], 1000.8)   # inside > loiter_seconds (0.5)
    types_ = [e["type"] for e in db.list_events(camera_id=cid)]
    assert "loitering" in types_


def test_exit_closes_event(env):
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)
    eng.process(_frame(), [_det(1, x=20, y=20)], 1001.0)
    ev = db.get_event(1)
    assert ev["status"] == "closed"
    assert ev["ended_at"] is not None


def test_track_handoff_no_false_intrusion(env):
    """Tracker ID reset while already inside a zone (frame gap / jitter) must
    NOT fire a second intrusion — the new track inherits the donor's state.
    Loitering must continue under the new track id as well."""
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)   # enter -> intrusion #1
    eng.process(_frame(), [], 1001.0)          # tracker loses the object
    eng.process(_frame(), [_det(2)], 1002.0)   # same spot, new id -> handoff
    intr = [e for e in db.list_events(camera_id=cid) if e["type"] == "intrusion"]
    assert len(intr) == 1
    eng.process(_frame(), [_det(2)], 1003.0)   # dwell > loiter_seconds (0.5)
    types_ = [e["type"] for e in db.list_events(camera_id=cid)]
    assert "loitering" in types_               # continued, not re-fired as new


def test_new_distant_track_still_intrudes(env):
    """A genuinely new object, seen OUTSIDE the zone before crossing, must
    still fire its own intrusion (handoff must not swallow real events)."""
    eng, alerts, cid = env
    eng.process(_frame(), [_det(1)], 1000.0)              # track 1 inside -> intrusion
    eng.process(_frame(), [], 1001.0)                     # tracker drops it
    eng.process(_frame(), [_det(2, x=40, y=20)], 1002.0)  # new object, far, outside
    eng.process(_frame(), [_det(2, x=280)], 1003.0)       # it crosses in -> intrusion #2
    intr = [e for e in db.list_events(camera_id=cid) if e["type"] == "intrusion"]
    assert len(intr) == 2


def test_frame_to_alert_latency(env):
    """Engine-side latency: a frame that breaches a zone must produce the
    alert push within the same process() call — a fraction of the <3 s budget
    (proposal §7). The WS hop adds ~ms, not seconds."""
    eng, alerts, cid = env
    t0 = time.perf_counter()
    eng.process(_frame(), [_det(1)], 1000.0)   # breaches -> intrusion fires
    dt = time.perf_counter() - t0
    kinds = [m["kind"] for m in alerts.msgs]
    assert "alert" in kinds
    assert dt < 0.25   # generous cap; in practice < 5 ms
