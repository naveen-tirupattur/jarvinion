"""Strict Pydantic configuration loader for config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, HttpUrl, field_validator


class FeedConfig(BaseModel, extra="forbid"):
    url: HttpUrl
    labels: list[str] = []


class TopicConfig(BaseModel, extra="forbid"):
    name: str
    keywords: list[str] = []


class ScheduleConfig(BaseModel, extra="forbid"):
    ingest: str = "0 */4 * * *"
    digest: str = "0 6 * * *"


class LearningConfig(BaseModel, extra="forbid"):
    candidate_min_mentions: int = 2
    resurface_after_days: int = 14


class LLMTaskConfig(BaseModel, extra="forbid"):
    provider: str
    model: str


class OllamaProviderConfig(BaseModel, extra="forbid"):
    base_url: str = "http://localhost:11434"


class BedrockProviderConfig(BaseModel, extra="forbid"):
    region: str = "us-west-2"


class EmptyProviderConfig(BaseModel, extra="forbid"):
    pass


class LLMProvidersConfig(BaseModel, extra="forbid"):
    bedrock: BedrockProviderConfig | None = None
    anthropic: EmptyProviderConfig | None = None
    openai: EmptyProviderConfig | None = None
    gemini: EmptyProviderConfig | None = None
    ollama: OllamaProviderConfig | None = None


class LLMConfig(BaseModel, extra="forbid"):
    providers: LLMProvidersConfig = LLMProvidersConfig()
    tasks: dict[str, LLMTaskConfig] = {}


class AppConfig(BaseModel, extra="forbid"):
    feeds: list[FeedConfig] = []
    topics: list[TopicConfig] = []
    schedule: ScheduleConfig = ScheduleConfig()
    learning: LearningConfig = LearningConfig()
    llm: LLMConfig = LLMConfig()

    @field_validator("feeds")
    @classmethod
    def feeds_must_have_urls(cls, v: list[FeedConfig]) -> list[FeedConfig]:
        for f in v:
            if not str(f.url).strip():
                raise ValueError("Feed URL must not be empty")
        return v


def load_config(path: str | Path) -> AppConfig:
    """Load and validate config.yaml, raising on any schema error."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(text)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at top level, got {type(data).__name__}")
    return AppConfig(**data)
