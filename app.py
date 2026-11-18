"""Render entry point:  uvicorn app:app --host 0.0.0.0 --port $PORT"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "server"))

from remote_server import build_app

app = build_app()
