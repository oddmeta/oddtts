"""Config loader — manages ~/.config/oddtts/config.json.

- load_config(): load config.json, create from defaults if missing
- save_config(): write current config to config.json
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "oddtts"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _to_serializable(val):
    from oddtts.oddtts_params import ODDTTS_TYPE
    if isinstance(val, ODDTTS_TYPE):
        return val.name
    return val


def _from_serializable(key, val, defaults):
    from oddtts.oddtts_params import ODDTTS_TYPE
    if key == "tts_type" and isinstance(val, str):
        try:
            return ODDTTS_TYPE[val]
        except KeyError:
            return defaults.get(key, val)
    return val


def load_config(defaults: dict) -> dict:
    """Load config.json, merging with defaults. Create file if missing."""
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        serializable = {k: _to_serializable(v) for k, v in defaults.items()}
        CONFIG_FILE.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return dict(defaults)

    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    merged = dict(defaults)
    for k, v in raw.items():
        merged[k] = _from_serializable(k, v, defaults)
    return merged


def save_config(cfg: dict) -> None:
    """Write current config to config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {k: _to_serializable(v) for k, v in cfg.items()}
    CONFIG_FILE.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
