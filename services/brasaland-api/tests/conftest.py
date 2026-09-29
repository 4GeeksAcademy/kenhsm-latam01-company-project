from __future__ import annotations

import pytest

from brasaland_api.core.config import get_settings
from brasaland_api.core.db import get_db


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    get_db.cache_clear()
    get_settings.cache_clear()
    monkeypatch.setenv("TINYDB_PATH", str(tmp_path / "db.json"))
    yield
    get_db.cache_clear()
    get_settings.cache_clear()