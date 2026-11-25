"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from feedwise.db import open_db

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def rss2_xml() -> str:
    return (FIXTURES / "rss2_sample.xml").read_text()


@pytest.fixture
def atom_xml() -> str:
    return (FIXTURES / "atom_sample.xml").read_text()


@pytest.fixture
def db_conn(tmp_path: Path):
    conn = open_db(tmp_path / "test.db")
    yield conn
    conn.close()
