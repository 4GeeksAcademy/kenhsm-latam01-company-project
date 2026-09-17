"""Compatibility entrypoint for the incident analysis API."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parents[1] / "admin-api" / "server.py"), run_name="__main__")
