"""IoU tracker: identity across frames, new objects, expiry."""
from backend.detection import Tracker


def test_new_track_and_identity():
    tr = Tracker(expire=1.0)
    d0 = tr.update([{"cls": "person", "conf": 0.9, "box": (100, 100, 30, 60)}], 0.0)
    assert len(d0) == 1
    tid = d0[0].track_id
    d1 = tr.update([{"cls": "person", "conf": 0.9, "box": (103, 102, 30, 60)}], 0.2)
    assert len(d1) == 1 and d1[0].track_id == tid


def test_new_object_gets_new_id():
    tr = Tracker(expire=1.0)
    tr.update([{"cls": "person", "conf": 0.9, "box": (10, 10, 30, 60)}], 0.0)
    d = tr.update([
        {"cls": "person", "conf": 0.9, "box": (12, 10, 30, 60)},
        {"cls": "car", "conf": 0.8, "box": (400, 200, 90, 40)},
    ], 0.2)
    assert len(d) == 2
    assert len({x.track_id for x in d}) == 2


def test_expiry_after_gap():
    tr = Tracker(expire=1.0)
    d0 = tr.update([{"cls": "person", "conf": 0.9, "box": (100, 100, 30, 60)}], 0.0)
    tid = d0[0].track_id
    d1 = tr.update([{"cls": "car", "conf": 0.8, "box": (400, 200, 90, 40)}], 2.0)
    assert tid not in [x.track_id for x in d1]
    assert tid not in tr.tracks


def test_expiry_with_empty_frame():
    tr = Tracker(expire=1.0)
    tr.update([{"cls": "person", "conf": 0.9, "box": (100, 100, 30, 60)}], 0.0)
    out = tr.update([], 2.0)
    assert out == [] and tr.tracks == {}
