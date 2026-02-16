"""
Centralized Configuration Loader
=================================
Loads config.yaml into typed dataclasses with sensible defaults.
Usage: from config import load_config; cfg = load_config()
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MarketHoursConfig:
    open: str = "09:30"
    close: str = "16:00"
    timezone: str = "America/New_York"


@dataclass
class FetcherConfig:
    refresh_interval: int = 60
    max_tickers_per_cycle: int = 100
    api_retry_attempts: int = 3
    api_retry_delay: int = 2


@dataclass
class DatabaseConfig:
    path: str = "data/options_history.db"
    retention_days: int = 30


@dataclass
class AlertThresholds:
    gex_flip: bool = True
    new_max_gamma_strike: bool = True
    price_near_gamma_wall_pct: float = 1.0


@dataclass
class AlertsConfig:
    enabled: bool = True
    desktop_notifications: bool = True
    discord_webhook: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)


@dataclass
class ApiServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/trading.log"
    max_bytes: int = 10_485_760  # 10 MB
    backup_count: int = 5
    staleness_minutes: int = 5


@dataclass
class AppConfig:
    market_hours: MarketHoursConfig = field(default_factory=MarketHoursConfig)
    fetcher: FetcherConfig = field(default_factory=FetcherConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    api_server: ApiServerConfig = field(default_factory=ApiServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _merge_dict(dataclass_type, data: dict):
    """Recursively merge a dict into a dataclass, ignoring unknown keys."""
    if data is None:
        return dataclass_type()

    kwargs = {}
    for f in dataclass_type.__dataclass_fields__.values():
        if f.name in data:
            val = data[f.name]
            # If the field type is itself a dataclass, recurse
            if hasattr(f.type, '__dataclass_fields__') if isinstance(f.type, type) else False:
                kwargs[f.name] = _merge_dict(f.type, val)
            else:
                # Check default_factory for nested dataclasses
                if f.default_factory is not type(None) and callable(f.default_factory):
                    default_instance = f.default_factory()
                    if hasattr(default_instance, '__dataclass_fields__') and isinstance(val, dict):
                        kwargs[f.name] = _merge_dict(type(default_instance), val)
                    else:
                        kwargs[f.name] = val
                else:
                    kwargs[f.name] = val

    return dataclass_type(**kwargs)


_config_cache: Optional[AppConfig] = None


def load_config(config_path: str = None) -> AppConfig:
    """Load configuration from config.yaml, falling back to defaults."""
    global _config_cache

    if _config_cache is not None and config_path is None:
        return _config_cache

    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}

    config = _merge_dict(AppConfig, raw)
    _config_cache = config
    return config


def reset_config():
    """Reset configuration cache (useful for testing)."""
    global _config_cache
    _config_cache = None
