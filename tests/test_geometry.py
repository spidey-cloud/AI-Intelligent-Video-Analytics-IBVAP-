"""Zone geometry: point-in-polygon (virtual fence core)."""
from backend.events import point_in_polygon

SQ = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]


def test_inside():
    assert point_in_polygon(0.5, 0.5, SQ)


def test_outside():
    assert not point_in_polygon(0.1, 0.5, SQ)
    assert not point_in_polygon(0.5, 0.95, SQ)


def test_just_outside_edges():
    assert not point_in_polygon(0.19, 0.5, SQ)
    assert not point_in_polygon(0.81, 0.5, SQ)
    assert not point_in_polygon(0.5, 0.19, SQ)


def test_concave_polygon():
    # L-shape: (0.75, 0.75) is inside the bbox but in the cut-out
    L = [[0, 0], [1, 0], [1, 0.5], [0.5, 0.5], [0.5, 1], [0, 1]]
    assert point_in_polygon(0.25, 0.25, L)
    assert not point_in_polygon(0.75, 0.75, L)
