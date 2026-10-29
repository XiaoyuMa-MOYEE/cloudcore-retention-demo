"""Load and validate local YAML configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    batch_size: int
    provider: str
    model: str
    model_version: str | None
    api_key_env: str
    base_url: str | None
    request_timeout_seconds: int
    batch_retry_count: int
    record_retry_count: int
    allow_external_cloudcore_data: bool
    input_path: str
    output_path: str
    analysis_path: str
    errors_path: str
    generation_log_path: str
    validation_report_path: str
    prepared_requests_path: str
    prepared_id_map_path: str
    valid_support_tiers: tuple[str, ...]
    prompt_version: str
    checkpoint_path: str


def load_config(path: str | Path) -> AppConfig:
    """Read YAML and reject missing, malformed, or unsafe configuration values."""
    config_path = Path(path)
    try:
        data: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read config file {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a YAML mapping.")

    required = (
        "batch_size", "provider", "model", "api_key_env", "request_timeout_seconds",
        "batch_retry_count", "record_retry_count", "allow_external_cloudcore_data",
        "input_path", "output_path", "analysis_path", "errors_path", "generation_log_path",
        "validation_report_path", "prepared_requests_path", "prepared_id_map_path", "checkpoint_path",
        "valid_support_tiers", "prompt_version",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing configuration keys: {', '.join(missing)}")

    def positive_int(key: str) -> int:
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer.")
        return value

    def nonnegative_int(key: str) -> int:
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer.")
        return value

    tiers = data["valid_support_tiers"]
    if not isinstance(tiers, list) or not tiers or any(not isinstance(t, str) or not t.strip() for t in tiers):
        raise ValueError("valid_support_tiers must be a non-empty list of non-empty strings.")
    normalized = [tier.strip().casefold() for tier in tiers]
    if len(set(normalized)) != len(normalized):
        raise ValueError("valid_support_tiers must not contain duplicate values ignoring case and whitespace.")
    if not isinstance(data["allow_external_cloudcore_data"], bool):
        raise ValueError("allow_external_cloudcore_data must be true or false.")
    if data.get("model_version") is not None and not isinstance(data["model_version"], str):
        raise ValueError("model_version must be quoted as a string in YAML.")

    strings = ("provider", "model", "api_key_env", "input_path", "output_path", "analysis_path",
               "errors_path", "generation_log_path", "validation_report_path", "prepared_requests_path", "prepared_id_map_path", "checkpoint_path",
               "prompt_version")
    if any(not isinstance(data[key], str) or not data[key].strip() for key in strings):
        raise ValueError("Provider, model, path, environment variable, and prompt version values must be non-empty strings.")

    return AppConfig(
        batch_size=positive_int("batch_size"),
        provider=data["provider"], model=data["model"], model_version=data.get("model_version"),
        api_key_env=data["api_key_env"],
        base_url=data.get("base_url"), request_timeout_seconds=positive_int("request_timeout_seconds"),
        batch_retry_count=nonnegative_int("batch_retry_count"),
        record_retry_count=nonnegative_int("record_retry_count"),
        allow_external_cloudcore_data=data["allow_external_cloudcore_data"],
        input_path=data["input_path"], output_path=data["output_path"],
        analysis_path=data["analysis_path"], errors_path=data["errors_path"],
        generation_log_path=data["generation_log_path"],
        validation_report_path=data["validation_report_path"],
        prepared_requests_path=data["prepared_requests_path"],
        prepared_id_map_path=data["prepared_id_map_path"],
        valid_support_tiers=tuple(tiers), prompt_version=data["prompt_version"],
        checkpoint_path=data["checkpoint_path"],
    )
