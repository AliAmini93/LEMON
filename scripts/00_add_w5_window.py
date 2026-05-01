#!/usr/bin/env python
"""
00_add_w5_window.py

Add W5 / Post-W4 window (600-800 ms) to configs/config.yaml.

Usage:
  python scripts/00_add_w5_window.py --config configs/config.yaml

This script:
  1. Creates a backup: config.yaml.bak_before_w5
  2. Adds/updates:
       erp_windows_ms:
         W1: [80, 130]
         W2: [130, 220]
         W3: [220, 320]
         W4: [320, 600]
         W5: [600, 800]
  3. Preserves other config fields.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import yaml


DEFAULT_WINDOWS = {
    "W1": [80, 130],
    "W2": [130, 220],
    "W3": [220, 320],
    "W4": [320, 600],
    "W5": [600, 800],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    backup_path = config_path.with_suffix(config_path.suffix + ".bak_before_w5")
    if not backup_path.exists():
        shutil.copy2(config_path, backup_path)
        print(f"[OK] Backup created: {backup_path}")
    else:
        print(f"[OK] Backup already exists: {backup_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    existing = cfg.get("erp_windows_ms", {})
    if existing is None:
        existing = {}

    # Preserve existing W1-W4 if already present, otherwise fill defaults.
    windows = {}
    for key in ["W1", "W2", "W3", "W4"]:
        windows[key] = existing.get(key, DEFAULT_WINDOWS[key])

    # Add/update W5.
    windows["W5"] = [600, 800]

    cfg["erp_windows_ms"] = windows

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

    print(f"[OK] Updated config: {config_path}")
    print("[OK] erp_windows_ms:")
    for k, v in cfg["erp_windows_ms"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
