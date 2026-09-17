"""Test environment: isolated tmp DB/media, sim detector (no torch needed).
Must run before any `backend` import — pytest loads conftest first."""
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="ibvap_test_")
os.environ["IBVAP_DB"] = os.path.join(_TMP, "test.db")
os.environ["IBVAP_MEDIA"] = os.path.join(_TMP, "media")
os.environ["IBVAP_DETECTOR"] = "sim"
os.environ["IBVAP_YOLO_MODEL"] = "models/none.pt"
os.environ["IBVAP_SECRET"] = "test-secret-key-0123456789-0123456789"
os.environ["IBVAP_CLIP_SECONDS"] = "4"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
