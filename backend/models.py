"""Pydantic request schemas (REST API contracts – see docs/ARCHITECTURE.md §8)."""
from typing import Dict, List, Optional

from pydantic import BaseModel


class Login(BaseModel):
    username: str
    password: str


class ZoneIn(BaseModel):
    name: str
    kind: str = "perimeter"          # perimeter | restricted | area
    points: List[list]               # [[x_norm, y_norm], ...] 0..1 coords
    color: str = "#22c55e"


class CameraIn(BaseModel):
    bop_id: int
    name: str
    source_type: str = "rtsp"        # rtsp | video | synthetic
    source_config: Dict = {}


class UserIn(BaseModel):
    username: str
    password: str
    role: str = "operator"           # admin | operator | viewer
    full_name: str = ""
    bop_id: Optional[int] = None


class BopIn(BaseModel):
    code: str
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
