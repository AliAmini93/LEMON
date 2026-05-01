#!/usr/bin/env python
"""
03c_summarize_difference_windows.py

Summarize ERP difference-wave grand averages by predefined ERP windows.

Input:
  reports/erp_diff/*_grand_average.csv

Each input CSV is expected to contain:
  - time_ms
  - mean_diff
  - sem
  - n_subjects

Output:
  reports/erp_diff/difference_window_summary.csv

For each file × window, computes:
  - mean_difference: average of mean_diff within the window
  - sem_average: average SEM within the window
  - peak_positive: max mean_diff within the window
  - peak_positive_time_ms
  - peak_negative: min mean_diff within the window
  - peak_negative_time_ms
  - abs_peak: largest absolute deflection in the window
  - abs_peak_time_ms
  - window_area: trapezoidal area under mean_diff in the window
  - n_timepoints

Usage:
  python scripts/03c_summarize_difference_windows.py --config configs/config.yaml
  python scripts/03c_summarize_difference_windows.py --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yaml


DEFAULT_WINDOWS_MS = {
    "W1": [80, 130],
    "W2": [130, 220],
    "W3": [220, 320],
    "W4": [320, 600],
}

KNOWN_CONTRASTS = [
    "face_vs_nonface",
    "emotional_vs_neutral",
]


def load_config(path: str | Path | None) -> dict:
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_windows(cfg: dict) -> Dict[str, Tuple[float, float]]:
    windows = cfg.get("erp_windows_ms", DEFAULT_WINDOWS_MS)
    return {name: (float(v[0]), float(v[1])) for name, v in windows.items()}


def parse_grand_average_filename(path: Path) -> dict:
    """
    Parse filenames such as:
      scalp_main_face_vs_nonface_face_roi_grand_average.csv
      ear_full_main_emotional_vs_neutral_ear_right_grand_average.csv

    Returns modality, contrast, roi.
    """
    stem = path.name.replace("_grand_average.csv", "")

    for contrast in KNOWN_CONTRASTS:
        marker = f"_{contrast}_"
        if marker in stem:
            modality, roi = stem.split(marker, 1)
            return {
                "modality": modality,
                "contrast": contrast,
                "roi": roi,
                "source_file": str(path),
            }

    return {
        "modality": "unknown",
        "contrast": "unknown",
        "roi": stem,
        "source_file": str(path),
    }


def summarize_window(df: pd.DataFrame, start_ms: float, end_ms: float) -> dict:
    required = {"time_ms", "mean_diff", "sem"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    mask = (df["time_ms"] >= start_ms) & (df["time_ms"] <= end_ms)
    sub = df.loc[mask].copy()

    if len(sub) == 0:
        return {
            "n_timepoints": 0,
            "mean_difference": np.nan,
            "sem_average": np.nan,
            "peak_positive": np.nan,
            "peak_positive_time_ms": np.nan,
            "peak_negative": np.nan,
            "peak_negative_time_ms": np.nan,
            "abs_peak": np.nan,
            "abs_peak_time_ms": np.nan,
            "window_area": np.nan,
        }

    time = sub["time_ms"].to_numpy(dtype=float)
    y = sub["mean_diff"].to_numpy(dtype=float)
    sem = sub["sem"].to_numpy(dtype=float)

    finite_y = np.isfinite(y)
    if not finite_y.any():
        return {
            "n_timepoints": len(sub),
            "mean_difference": np.nan,
            "sem_average": np.nan,
            "peak_positive": np.nan,
            "peak_positive_time_ms": np.nan,
            "peak_negative": np.nan,
            "peak_negative_time_ms": np.nan,
            "abs_peak": np.nan,
            "abs_peak_time_ms": np.nan,
            "window_area": np.nan,
        }

    # Positive peak
    pos_idx = int(np.nanargmax(y))
    neg_idx = int(np.nanargmin(y))
    abs_idx = int(np.nanargmax(np.abs(y)))

    # Trapezoidal area, ignoring NaNs by using only finite samples.
    if finite_y.sum() >= 2:
        area = float(np.trapz(y[finite_y], time[finite_y]))
    else:
        area = np.nan

    return {
        "n_timepoints": int(len(sub)),
        "mean_difference": float(np.nanmean(y)),
        "sem_average": float(np.nanmean(sem)),
        "peak_positive": float(y[pos_idx]),
        "peak_positive_time_ms": float(time[pos_idx]),
        "peak_negative": float(y[neg_idx]),
        "peak_negative_time_ms": float(time[neg_idx]),
        "abs_peak": float(y[abs_idx]),
        "abs_peak_time_ms": float(time[abs_idx]),
        "window_area": area,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--input-dir", default="reports/erp_diff")
    parser.add_argument("--output", default="reports/erp_diff/difference_window_summary.csv")
    args = parser.parse_args()

    cfg = load_config(args.config)
    windows = get_windows(cfg)

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*_grand_average.csv"))

    if not files:
        raise FileNotFoundError(f"No *_grand_average.csv files found in {input_dir}")

    rows = []

    for path in files:
        info = parse_grand_average_filename(path)

        df = pd.read_csv(path)

        n_subjects = np.nan
        if "n_subjects" in df.columns:
            n_subjects_values = df["n_subjects"].dropna().unique()
            if len(n_subjects_values) > 0:
                n_subjects = int(n_subjects_values[0])

        for window_name, (start_ms, end_ms) in windows.items():
            s = summarize_window(df, start_ms, end_ms)
            rows.append({
                **info,
                "window": window_name,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "n_subjects": n_subjects,
                **s,
            })

    out_df = pd.DataFrame(rows)

    # Nice ordering for human inspection
    col_order = [
        "modality",
        "contrast",
        "roi",
        "window",
        "start_ms",
        "end_ms",
        "n_subjects",
        "n_timepoints",
        "mean_difference",
        "sem_average",
        "peak_positive",
        "peak_positive_time_ms",
        "peak_negative",
        "peak_negative_time_ms",
        "abs_peak",
        "abs_peak_time_ms",
        "window_area",
        "source_file",
    ]
    out_df = out_df[col_order]

    out_df.to_csv(output_path, index=False)

    print(f"[OK] Read {len(files)} grand-average files from: {input_dir}")
    print(f"[OK] Wrote window summary: {output_path}")
    print("\nTop rows:")
    print(out_df.head(12).to_string(index=False))

    # Also print strongest absolute peaks for quick inspection
    print("\nStrongest absolute window effects:")
    strongest = (
        out_df
        .sort_values("abs_peak", key=lambda s: s.abs(), ascending=False)
        .head(10)
    )
    print(
        strongest[
            [
                "modality",
                "contrast",
                "roi",
                "window",
                "mean_difference",
                "abs_peak",
                "abs_peak_time_ms",
                "n_subjects",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
