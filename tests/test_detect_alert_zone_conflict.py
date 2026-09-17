"""Bug condition exploration test: detect-alert / zone-conflict.

**Validates: Requirements 1.1, 1.2**

Property 1 (Bug Condition): Detect Alert Fires When Zones Are Configured
------------------------------------------------------------------------
CURRENT (BUGGY) behavior:
  _check_detect_alert() is called unconditionally for every detection BEFORE
  zone membership is evaluated.  For class-matched detections (e.g. "person"),
  this always inserts a raw `detection` event with zone_id=None — even when the
  same detection then triggers an intrusion, and even when the detection is
  completely outside all configured zones.

EXPECTED (CORRECT) behavior:
  2.1 – When the centroid is INSIDE a configured zone, only zone-based events
        (intrusion / loitering) should fire.  NO detection event with
        zone_id=None must be produced.
  2.2 – When the centroid is OUTSIDE all configured zones, NO event of any kind
        should be produced.

This test MUST FAIL on the unfixed codebase — failure proves the bug exists.
DO NOT attempt to fix the code when this test fails.
"""
import os
import tempfile
import types

import numpy as np
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from backend import db
from backend.detection import Det
from backend.events import EventEngine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRAME_W, FRAME_H = 640, 360

# Zone covers the normalised square [0.4, 0.6] × [0.4, 0.6].
# In pixel space that is x ∈ [256, 384], y ∈ [144, 216].
ZONE_POLY = [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]]

_DEFAULT_SETTINGS = types.SimpleNamespace(
    clip_seconds=4, ring_fps=2, loiter_seconds=0.5,
    intrusion_cooldown=100.0, track_expire=1.6,
    event_max_age=5.0, event_stable_gap=0.5,
    detect_alert_classes="person", detect_cooldown=30.0,
)


class _FakeAlerts:
    def __init__(self):
        self.msgs = []

    def push(self, m):
        self.msgs.append(m)


# ---------------------------------------------------------------------------
# Fixtures — one fresh DB per test function, shared across all examples
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_db(tmp_path):
    """Initialise one isolated SQLite DB for the test function."""
    db.init(str(tmp_path / "t.db"))
    return tmp_path


def _new_camera(tmp_path):
    """Insert a fresh BOP + camera + zone, return (camera_id, media_dir, engine)."""
    # Use a unique BOP code each call to avoid UNIQUE constraint issues
    bop_code = f"BOP-{_new_camera._counter}"
    _new_camera._counter += 1

    db.add_bop(bop_code, "Exploration BOP")
    cid = db.add_camera(1, f"CAM-{bop_code}", "synthetic", {"scene": "test"})
    db.add_zone(cid, "Z", "perimeter", ZONE_POLY)

    media_dir = str(tmp_path / f"media_{bop_code}")
    os.makedirs(media_dir, exist_ok=True)
    alerts = _FakeAlerts()
    eng = EventEngine(cid, media_dir, _DEFAULT_SETTINGS, alerts, f"CAM-{bop_code}")
    return cid, eng


_new_camera._counter = 0


def _frame():
    return np.zeros((FRAME_H, FRAME_W, 3), np.uint8)


def _det_at_norm(track_id, nx, ny, cls="person"):
    """Build a Det whose centroid sits at normalised (nx, ny)."""
    w, h = 26, 52
    px = int(nx * FRAME_W) - w // 2
    py = int(ny * FRAME_H) - h // 2
    return Det(track_id, cls, 0.9, px, py, w, h)


# ---------------------------------------------------------------------------
# Property 1a – inside zone: NO spurious detection event (req 2.1)
# ---------------------------------------------------------------------------

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nx=st.floats(min_value=0.42, max_value=0.58),
    ny=st.floats(min_value=0.42, max_value=0.58),
    track_id=st.integers(min_value=1, max_value=9999),
)
def test_no_detection_event_when_inside_zone(fresh_db, nx, ny, track_id):
    """**Validates: Requirements 1.1, 2.1**

    For every class-matched detection whose centroid is inside a configured
    zone, process() must produce zero detection events with zone_id=None.

    EXPECTED TO FAIL on unfixed code: the bug causes _check_detect_alert() to
    fire unconditionally, inserting a spurious detection event before the zone
    intrusion event.
    """
    cid, eng = _new_camera(fresh_db)

    det = _det_at_norm(track_id, nx, ny, cls="person")
    eng.process(_frame(), [det], 1000.0)

    events = db.list_events(camera_id=cid)
    detection_events = [e for e in events if e["type"] == "detection" and e["zone_id"] is None]

    assert len(detection_events) == 0, (
        f"BUG CONFIRMED (req 2.1): centroid ({nx:.3f}, {ny:.3f}) is INSIDE the zone "
        f"but produced {len(detection_events)} spurious detection event(s) with zone_id=None. "
        f"All events: {[(e['type'], e['zone_id']) for e in events]}"
    )


# ---------------------------------------------------------------------------
# Property 1b – outside zone: NO event at all (req 2.2)
# ---------------------------------------------------------------------------

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nx=st.floats(min_value=0.01, max_value=0.30),
    ny=st.floats(min_value=0.01, max_value=0.30),
    track_id=st.integers(min_value=1, max_value=9999),
)
def test_no_event_when_outside_all_zones(fresh_db, nx, ny, track_id):
    """**Validates: Requirements 1.2, 2.2**

    For every class-matched detection whose centroid is outside all configured
    zones, process() must produce zero events of any kind.

    EXPECTED TO FAIL on unfixed code: the bug causes _check_detect_alert() to
    fire unconditionally, inserting a spurious detection event even though no
    zone rule was triggered.
    """
    cid, eng = _new_camera(fresh_db)

    det = _det_at_norm(track_id, nx, ny, cls="person")
    eng.process(_frame(), [det], 1000.0)

    events = db.list_events(camera_id=cid)

    assert len(events) == 0, (
        f"BUG CONFIRMED (req 2.2): centroid ({nx:.3f}, {ny:.3f}) is OUTSIDE all zones "
        f"but produced {len(events)} spurious event(s). "
        f"Events: {[(e['type'], e['zone_id']) for e in events]}"
    )


# ===========================================================================
# TASK 2 – Preservation property tests
# ===========================================================================
# These tests verify that the fix does NOT regress existing engine behaviour.
# They are run against the FIXED backend/events.py and must ALL PASS.
# ===========================================================================

# ---------------------------------------------------------------------------
# Helpers shared by preservation tests
# ---------------------------------------------------------------------------

def _new_camera_no_zones(tmp_path):
    """Fresh camera with NO zones configured."""
    bop_code = f"BOP-NZ-{_new_camera._counter}"
    _new_camera._counter += 1
    db.add_bop(bop_code, "Preservation BOP (no zones)")
    cid = db.add_camera(1, f"CAM-{bop_code}", "synthetic", {"scene": "test"})
    media_dir = str(tmp_path / f"media_{bop_code}")
    os.makedirs(media_dir, exist_ok=True)
    alerts = _FakeAlerts()
    eng = EventEngine(cid, media_dir, _DEFAULT_SETTINGS, alerts, f"CAM-{bop_code}")
    return cid, eng, alerts


def _new_camera_with_zone(tmp_path):
    """Fresh camera WITH one zone configured (same poly as bug-condition tests)."""
    bop_code = f"BOP-WZ-{_new_camera._counter}"
    _new_camera._counter += 1
    db.add_bop(bop_code, "Preservation BOP (with zone)")
    cid = db.add_camera(1, f"CAM-{bop_code}", "synthetic", {"scene": "test"})
    db.add_zone(cid, "Z", "perimeter", ZONE_POLY)
    media_dir = str(tmp_path / f"media_{bop_code}")
    os.makedirs(media_dir, exist_ok=True)
    alerts = _FakeAlerts()
    eng = EventEngine(cid, media_dir, _DEFAULT_SETTINGS, alerts, f"CAM-{bop_code}")
    return cid, eng, alerts


# ---------------------------------------------------------------------------
# Property 2 – Req 3.1
# Zone-free camera: class-matched detection → exactly ONE detection event
# ---------------------------------------------------------------------------

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nx=st.floats(min_value=0.05, max_value=0.95),
    ny=st.floats(min_value=0.05, max_value=0.95),
    track_id=st.integers(min_value=1, max_value=9999),
)
def test_detection_alert_fires_when_no_zones(fresh_db, nx, ny, track_id):
    """**Validates: Requirements 3.1**

    For every class-matched detection (cls in detect_alert_classes) where NO
    zones are configured for the camera, process() must create exactly one
    'detection' event (zone_id=None).

    This confirms the fix does not break the zone-free detection-alert path.
    """
    cid, eng, alerts = _new_camera_no_zones(fresh_db)

    det = _det_at_norm(track_id, nx, ny, cls="person")
    eng.process(_frame(), [det], 1000.0)

    events = db.list_events(camera_id=cid)
    detection_events = [e for e in events if e["type"] == "detection"]

    assert len(detection_events) == 1, (
        f"Req 3.1: expected exactly 1 detection event for zone-free camera, "
        f"got {len(events)} event(s): {[(e['type'], e['zone_id']) for e in events]}"
    )
    assert detection_events[0]["zone_id"] is None, (
        "Req 3.1: detection event must have zone_id=None (no zone was crossed)"
    )
    alert_kinds = [m["kind"] for m in alerts.msgs]
    assert "alert" in alert_kinds, "Req 3.1: an alert push must accompany the detection event"


# ---------------------------------------------------------------------------
# Parametric tests for Reqs 3.2 – 3.5
# ---------------------------------------------------------------------------

def test_non_class_vehicle_in_zone_fires_medium_intrusion(fresh_db):
    """**Validates: Requirements 3.2**

    A detection whose class is NOT in detect_alert_classes (e.g. 'truck')
    crossing into a zone must fire exactly one 'intrusion' event with
    severity='medium'.  The fix must not affect this path.
    """
    cid, eng, alerts = _new_camera_with_zone(fresh_db)

    # truck centroid well inside zone [0.4..0.6] × [0.4..0.6]
    det = _det_at_norm(1, 0.5, 0.5, cls="truck")
    eng.process(_frame(), [det], 1000.0)

    events = db.list_events(camera_id=cid)
    assert len(events) == 1, (
        f"Req 3.2: expected 1 intrusion event, got {len(events)}: "
        f"{[(e['type'], e['severity']) for e in events]}"
    )
    assert events[0]["type"] == "intrusion", "Req 3.2: event type must be 'intrusion'"
    assert events[0]["severity"] == "medium", (
        f"Req 3.2: non-class-matched vehicle must have severity 'medium', "
        f"got '{events[0]['severity']}'"
    )


def test_loitering_fires_after_dwell(fresh_db):
    """**Validates: Requirements 3.3**

    A detection that remains inside a zone longer than loiter_seconds (0.5 s)
    must fire a 'loitering' event in addition to the initial 'intrusion'.
    """
    cid, eng, _ = _new_camera_with_zone(fresh_db)

    det = _det_at_norm(1, 0.5, 0.5, cls="person")
    eng.process(_frame(), [det], 1000.0)   # enter → intrusion
    eng.process(_frame(), [det], 1000.8)   # still inside, >0.5 s dwell → loitering

    types_ = {e["type"] for e in db.list_events(camera_id=cid)}
    assert "loitering" in types_, (
        f"Req 3.3: expected a loitering event after >{_DEFAULT_SETTINGS.loiter_seconds}s dwell, "
        f"got event types: {types_}"
    )


def test_intrusion_cooldown_suppresses_refire(fresh_db):
    """**Validates: Requirements 3.4**

    A second crossing by the same track within intrusion_cooldown (100 s)
    must NOT produce a second intrusion event.
    """
    cid, eng, _ = _new_camera_with_zone(fresh_db)

    det_in = _det_at_norm(1, 0.5, 0.5, cls="person")
    det_out = _det_at_norm(1, 0.1, 0.1, cls="person")   # outside zone

    eng.process(_frame(), [det_in], 1000.0)    # first crossing → intrusion
    eng.process(_frame(), [det_out], 1001.0)   # exits zone
    eng.process(_frame(), [det_in], 1002.0)    # re-enters within cooldown window

    intrusions = [e for e in db.list_events(camera_id=cid) if e["type"] == "intrusion"]
    assert len(intrusions) == 1, (
        f"Req 3.4: intrusion cooldown must suppress re-fire within {_DEFAULT_SETTINGS.intrusion_cooldown}s, "
        f"but got {len(intrusions)} intrusion event(s)"
    )


def test_track_handoff_suppresses_false_reintrusion(fresh_db):
    """**Validates: Requirements 3.5**

    When the tracker resets the ID for a track already inside a zone (frame
    gap / jitter), the engine must inherit zone state to the new track ID and
    NOT fire a second intrusion.  Loitering must also continue under the new ID.
    """
    cid, eng, _ = _new_camera_with_zone(fresh_db)

    det1 = _det_at_norm(1, 0.5, 0.5, cls="person")
    det2 = _det_at_norm(2, 0.5, 0.5, cls="person")   # same position, new ID

    eng.process(_frame(), [det1], 1000.0)   # track 1 enters → intrusion
    eng.process(_frame(), [], 1001.0)       # tracker drops track 1
    eng.process(_frame(), [det2], 1002.0)   # track 2 at same spot → handoff, NO new intrusion

    intrusions = [e for e in db.list_events(camera_id=cid) if e["type"] == "intrusion"]
    assert len(intrusions) == 1, (
        f"Req 3.5: track handoff must suppress false re-intrusion; "
        f"got {len(intrusions)} intrusion event(s)"
    )

    # Loitering must still fire under the new track ID (dwell time inherited)
    eng.process(_frame(), [det2], 1003.0)   # now >0.5 s inside (2002 - 1000 via donor)
    types_ = {e["type"] for e in db.list_events(camera_id=cid)}
    assert "loitering" in types_, (
        "Req 3.5: loitering must continue under new track ID after handoff"
    )
