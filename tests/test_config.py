"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from feedwise.config import AppConfig, load_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_minimal_config():
    cfg = load_config(FIXTURES / "minimal_config.yaml")
    assert len(cfg.feeds) == 1
    assert str(cfg.feeds[0].url) == "https://example.com/feed.xml"
    assert cfg.feeds[0].labels == ["test"]


def test_load_full_config():
    cfg = load_config(FIXTURES / "full_config.yaml")
    assert len(cfg.feeds) == 2
    assert len(cfg.topics) == 2
    assert cfg.topics[0].name == "Distributed Systems"
    assert cfg.learning.candidate_min_mentions == 2
    assert cfg.llm.tasks["triage"].provider == "ollama"


def test_config_example_validates():
    cfg = load_config(Path(__file__).parent.parent / "config.example.yaml")
    assert len(cfg.feeds) >= 1


def test_empty_config_is_valid(tmp_path: Path):
    p = tmp_path / "empty.yaml"
    p.write_text("{}")
    cfg = load_config(p)
    assert cfg.feeds == []


def test_unknown_top_level_key_rejected(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("feeds: []\nbogus_key: true\n")
    with pytest.raises(Exception, match="bogus_key"):
        load_config(p)


def test_unknown_feed_key_rejected(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("feeds:\n  - url: https://example.com/feed\n    surprise: yes\n")
    with pytest.raises(Exception, match="surprise"):
        load_config(p)


def test_missing_feed_url_rejected(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("feeds:\n  - labels: [test]\n")
    with pytest.raises(Exception):
        load_config(p)


def test_invalid_feed_url_rejected(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("feeds:\n  - url: not-a-url\n")
    with pytest.raises(Exception):
        load_config(p)


def test_malformed_yaml_rejected(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("feeds:\n  - url: [unclosed bracket\n")
    with pytest.raises(Exception):
        load_config(p)
