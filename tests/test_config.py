"""Configuration loading tests."""

from __future__ import annotations

import pytest

from common.exceptions import ConfigError
from config.settings import get_settings, load_settings


def test_settings_loads_required_fields() -> None:
    settings = load_settings(reload=True)
    assert settings.kafka_bootstrap_servers == "localhost:9092"
    assert settings.minio_profile == "internal"
    assert settings.kafka_topic_ccu == "fortnite.raw.ccu"


def test_settings_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ConfigError):
        get_settings()
