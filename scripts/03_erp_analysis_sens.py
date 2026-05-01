#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03_erp_analysis_sens.py

Sensitivity ERP window extraction for the LEMON/MELON Emotional Affect analysis.

Why this script exists
----------------------
The previous subject-level statistics were based on reports/tables/window_amplitudes.csv.
That table usually contains the main ERP epochs, typically ending at 600 ms, so it can
support W1-W4 subject-level statistics but not W5 = 600-800 ms.

This script reads the already-preprocessed sensitivity epochs, for example:

    output/processed/sub-200/scalp_sens-epo.fif
    output/processed/sub-200/ear_full_sens-epo.fif
    output/processed/sub-200/ear_strict_sens-epo.fif

and produces a new table:

    reports/tables/window_amplitudes_sens.csv

which should include:

    W1: 80-130 ms
    W2: 130-220 ms
    W3: 220-320 ms
    W4: 320-600 ms
    W5: 600-800 ms

Then you can run subject-level statistics on this sensitivity table:

    python scripts/03d_subject_level_difference_stats.py ^
        --config configs/config.yaml ^
        --window-table reports/tables/window_amplitudes_sens.csv ^
        --condition-counts reports/tables/condition_counts_sens.csv ^
        --w5-summary reports/erp_diff_sens/difference_window_summary_w5.csv ^
        --out-dir reports/stats_sens ^
        --fig-dir reports/figures_sens

Outputs
-------
    reports/tables/window_amplitudes_sens.csv
    reports/tables/condition_counts_sens.csv
    reports/tables/roi_channel_usage_sens.csv
    reports/tables/channel_nan_report_sens.csv
    reports/tables/skipped_modality_epochs_sens.csv

Notes
-----
- This script is designed to be robust to subject-specific bad-channel removal.
- ROI means are computed from available ROI channels only.
- If an ROI has no available channels for a subject/modality, it is skipped.
- It does not redo preprocessing; it only analyzes existing sensitivity epochs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import mne
except Exception as exc:
    raise RuntimeError("mne is required. Please install MNE-Python.") from exc

try:
    import yaml
except Exception:
    yaml = None


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------

DEFAULT_WINDOWS_MS = {
    "W1": [80, 130],
    "W2": [130, 220],
    "W3": [220, 320],
    "W4": [320, 600],
    "W5": [600, 800],
}

DEFAULT_ROIS = {
    "scalp": {
        "face_roi": ["P7", "P8", "TP7", "TP8", "O1", "O2"],
        "central_roi": ["Fz", "Cz", "Pz"],
        "late_roi": ["Pz", "CP1", "CP2", "Cz"],
    },
    "ear": {
        "ear_full": ["Fpz", "M1", "M2", "EL1", "EL3", "EL4", "EL5", "ER1", "ER2", "ER3", "ER4"],
        "ear_strict": ["M1", "M2", "EL1", "EL3", "EL4", "EL5", "ER1", "ER2", "ER3", "ER4"],
        "ear_left": ["EL1", "EL3", "EL4", "EL5"],
        "ear_right": ["ER1", "ER2", "ER3", "ER4"],
        "ear_mastoid": ["M1", "M2"],
    },
}

MODALITIES = {
    "scalp_sens": {
        "file": "scalp_sens-epo.fif",
        "roi_group": "scalp",
    },
    "ear_full_sens": {
        "file": "ear_full_sens-epo.fif",
        "roi_group": "ear",
    },
    "ear_strict_sens": {
        "file": "ear_strict_sens-epo.fif",
        "roi_group": "ear",
    },
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)
    return obj or {}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_ch_name(name: str) -> str:
    """
    Normalize only for matching. Preserve original channel names in output.
    """
    return str(name).strip().lower()


def get_windows(config: dict) -> Dict[str, List[float]]:
    windows = (
        config.get("erp_windows_ms")
        or config.get("erp_windows")
        or config.get("windows")
        or DEFAULT_WINDOWS_MS
    )
    # Ensure W5 exists even if config has not been patched.
    windows = {str(k): list(v) for k, v in windows.items()}
    if "W5" not in windows:
        windows["W5"] = [600, 800]
    return windows


def get_project_root(config: dict, config_path: Path) -> Path:
    """
    Try to infer project root from config. If unavailable, use current working directory.
    """
    for key in ["root", "root_dir", "data_root", "bids_root", "project_root"]:
        if key in config and config[key]:
            p = Path(config[key])
            return p
    return Path.cwd()


def get_processed_dir(config: dict, root: Path) -> Path:
    for key in ["processed_dir", "output_processed_dir"]:
        if key in config and config[key]:
            p = Path(config[key])
            return p if p.is_absolute() else root / p
    return root / "output" / "processed"


def get_manifest_path(config: dict, root: Path) -> Path:
    for key in ["manifest", "manifest_path", "subject_manifest"]:
        if key in config and config[key]:
            p = Path(config[key])
            return p if p.is_absolute() else root / p
    return root / "output" / "manifests" / "subject_manifest.csv"


def subject_id_from_processed_dir(path: Path) -> str:
    name = path.name
    if name.startswith("sub-"):
        return name.replace("sub-", "")
    return name


def get_subjects(
    subjects_arg: Optional[List[str]],
    manifest_path: Path,
    processed_dir: Path,
) -> List[str]:
    if subjects_arg:
        return [str(s).replace("sub-", "") for s in subjects_arg]

    # Prefer manifest if available.
    if manifest_path.exists():
        try:
            m = pd.read_csv(manifest_path)
            # Try common column names.
            for col in ["subject_id", "subject", "participant_id", "sub"]:
                if col in m.columns:
                    vals = m[col].dropna().astype(str).str.replace("sub-", "", regex=False).tolist()
                    # If manifest has a usability column, prefer usable/main rows.
                    for usable_col in ["usable", "is_usable", "main", "is_main", "include"]:
                        if usable_col in m.columns:
                            mm = m[m[usable_col].astype(str).str.lower().isin(["true", "1", "yes", "main", "usable"])]
                            if len(mm) > 0:
                                vals = mm[col].dropna().astype(str).str.replace("sub-", "", regex=False).tolist()
                            break
                    return sorted(set(vals), key=lambda x: int(x) if x.isdigit() else x)
        except Exception:
            pass

    # Fallback: detect processed subject folders.
    if processed_dir.exists():
        subs = [
            subject_id_from_processed_dir(p)
            for p in processed_dir.iterdir()
            if p.is_dir() and p.name.startswith("sub-")
        ]
        return sorted(set(subs), key=lambda x: int(x) if x.isdigit() else x)

    return []


def pick_metadata_column(metadata: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in metadata.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def make_condition_masks(metadata: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Returns masks:
        face
        non_face
        emotional
        neutral
    """
    n = len(metadata)
    masks = {
        "face": np.zeros(n, dtype=bool),
        "non_face": np.zeros(n, dtype=bool),
        "emotional": np.zeros(n, dtype=bool),
        "neutral": np.zeros(n, dtype=bool),
    }

    type_col = pick_metadata_column(metadata, ["type", "stim_type", "category"])
    expr_col = pick_metadata_column(metadata, ["expression", "emotion", "expr"])

    if type_col is not None:
        typ = metadata[type_col].astype(str).str.lower().str.strip()
        masks["face"] = typ.eq("face").to_numpy()
        masks["non_face"] = typ.isin(["non_face", "non-face", "nonface", "tree", "object"]).to_numpy()

    if expr_col is not None:
        expr = metadata[expr_col].astype(str).str.lower().str.strip()
        masks["neutral"] = expr.eq("neutral").to_numpy()
        masks["emotional"] = expr.isin(["happy", "angry", "afraid", "fear", "fearful"]).to_numpy()

    return masks


def select_channels(epochs: mne.Epochs, desired: List[str]) -> Tuple[List[str], List[str]]:
    """
    Return available original channel names and missing desired names.
    Matching is case-insensitive.
    """
    ch_map = {normalize_ch_name(ch): ch for ch in epochs.ch_names}
    available = []
    missing = []
    for ch in desired:
        key = normalize_ch_name(ch)
        if key in ch_map:
            available.append(ch_map[key])
        else:
            missing.append(ch)
    return available, missing


def channel_nan_report(epochs: mne.Epochs, subject_id: str, modality: str) -> List[dict]:
    rows = []
    data = epochs.get_data(copy=True)
    n_total = data.shape[0] * data.shape[2] if data.ndim == 3 else np.nan

    for ci, ch in enumerate(epochs.ch_names):
        arr = data[:, ci, :]
        n_nan = int(np.isnan(arr).sum())
        nan_pct = float(100 * n_nan / n_total) if n_total and np.isfinite(n_total) else np.nan
        finite = arr[np.isfinite(arr)]
        rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "channel": ch,
            "n_nan": n_nan,
            "nan_pct": nan_pct,
            "finite_min": float(np.min(finite)) if finite.size else np.nan,
            "finite_max": float(np.max(finite)) if finite.size else np.nan,
            "finite_std": float(np.std(finite)) if finite.size else np.nan,
        })
    return rows


def mean_amplitude_for_roi_window(
    epochs: mne.Epochs,
    mask: np.ndarray,
    channels: List[str],
    start_ms: float,
    end_ms: float,
) -> float:
    if mask.sum() == 0 or len(channels) == 0:
        return np.nan

    e = epochs[mask].copy().pick_channels(channels, ordered=False)
    data = e.get_data(copy=True)  # epochs, channels, times
    times_ms = e.times * 1000.0
    tmask = (times_ms >= start_ms) & (times_ms <= end_ms)

    if tmask.sum() == 0:
        return np.nan

    segment = data[:, :, tmask]
    if not np.isfinite(segment).any():
        return np.nan

    return float(np.nanmean(segment))


def compute_subject_modality(
    subject_id: str,
    modality: str,
    epochs_path: Path,
    roi_group: str,
    windows: Dict[str, List[float]],
) -> Tuple[List[dict], List[dict], List[dict], List[dict], List[dict]]:
    """
    Returns:
        amplitude_rows
        condition_count_rows
        roi_usage_rows
        nan_rows
        skipped_rows
    """
    amplitude_rows = []
    condition_count_rows = []
    roi_usage_rows = []
    skipped_rows = []

    if not epochs_path.exists():
        skipped_rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "reason": "missing_epoch_file",
            "path": str(epochs_path),
        })
        return amplitude_rows, condition_count_rows, roi_usage_rows, [], skipped_rows

    try:
        epochs = mne.read_epochs(epochs_path, preload=True, verbose="ERROR")
    except Exception as exc:
        skipped_rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "reason": f"read_error: {exc}",
            "path": str(epochs_path),
        })
        return amplitude_rows, condition_count_rows, roi_usage_rows, [], skipped_rows

    if len(epochs) == 0:
        skipped_rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "reason": "empty_epochs",
            "path": str(epochs_path),
        })
        return amplitude_rows, condition_count_rows, roi_usage_rows, [], skipped_rows

    if epochs.metadata is None:
        skipped_rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "reason": "missing_metadata",
            "path": str(epochs_path),
        })
        return amplitude_rows, condition_count_rows, roi_usage_rows, channel_nan_report(epochs, subject_id, modality), skipped_rows

    metadata = epochs.metadata.reset_index(drop=True)
    masks = make_condition_masks(metadata)

    contrasts = {
        "face_vs_nonface": ["face", "non_face"],
        "emotional_vs_neutral": ["emotional", "neutral"],
    }

    # Condition counts.
    for contrast, conds in contrasts.items():
        for cond in conds:
            condition_count_rows.append({
                "subject_id": subject_id,
                "modality": modality,
                "contrast": contrast,
                "condition": cond,
                "n_epochs": int(masks[cond].sum()),
            })

    rois = DEFAULT_ROIS[roi_group]

    for roi_name, desired_channels in rois.items():
        available, missing = select_channels(epochs, desired_channels)

        roi_usage_rows.append({
            "subject_id": subject_id,
            "modality": modality,
            "roi": roi_name,
            "desired_channels": ",".join(desired_channels),
            "available_channels": ",".join(available),
            "missing_channels": ",".join(missing),
            "n_available": len(available),
            "n_missing": len(missing),
        })

        if len(available) == 0:
            skipped_rows.append({
                "subject_id": subject_id,
                "modality": modality,
                "reason": f"no_available_channels_for_roi:{roi_name}",
                "path": str(epochs_path),
            })
            continue

        for contrast, conds in contrasts.items():
            for cond in conds:
                for window_name, (start_ms, end_ms) in windows.items():
                    amp = mean_amplitude_for_roi_window(
                        epochs=epochs,
                        mask=masks[cond],
                        channels=available,
                        start_ms=float(start_ms),
                        end_ms=float(end_ms),
                    )

                    amplitude_rows.append({
                        "subject_id": subject_id,
                        "modality": modality,
                        "contrast": contrast,
                        "condition": cond,
                        "roi": roi_name,
                        "window": window_name,
                        "start_ms": float(start_ms),
                        "end_ms": float(end_ms),
                        "mean_amplitude": amp,
                        "n_epochs_condition": int(masks[cond].sum()),
                        "n_roi_channels": len(available),
                        "available_channels": ",".join(available),
                    })

    return (
        amplitude_rows,
        condition_count_rows,
        roi_usage_rows,
        channel_nan_report(epochs, subject_id, modality),
        skipped_rows,
    )


def sort_output(df: pd.DataFrame, windows: Dict[str, List[float]]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    window_order = {w: i for i, w in enumerate(windows.keys())}
    if "window" in df.columns:
        df["_window_order"] = df["window"].map(window_order).fillna(999).astype(int)
    sort_cols = [c for c in ["subject_id", "modality", "contrast", "condition", "roi", "_window_order"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
    if "_window_order" in df.columns:
        df = df.drop(columns=["_window_order"])
    return df


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract ERP window amplitudes from sensitivity epochs, including W5 = 600-800 ms."
    )
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--subjects", nargs="*", default=None, help="Optional subject IDs, e.g. --subjects 200 201")
    parser.add_argument("--processed-dir", default=None, help="Override processed directory")
    parser.add_argument("--out-dir", default="reports/tables", help="Output table directory")
    parser.add_argument("--include", nargs="*", default=None, choices=list(MODALITIES.keys()), help="Optional modality subset")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_yaml(config_path)
    root = get_project_root(config, config_path)

    processed_dir = Path(args.processed_dir) if args.processed_dir else get_processed_dir(config, root)
    if not processed_dir.is_absolute():
        processed_dir = root / processed_dir

    manifest_path = get_manifest_path(config, root)
    subjects = get_subjects(args.subjects, manifest_path, processed_dir)

    if not subjects:
        print("[ERROR] No subjects found. Use --subjects or check manifest/processed directory.", file=sys.stderr)
        sys.exit(1)

    windows = get_windows(config)
    modalities = args.include if args.include else list(MODALITIES.keys())

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    ensure_dir(out_dir)

    all_amp_rows = []
    all_count_rows = []
    all_roi_rows = []
    all_nan_rows = []
    all_skip_rows = []

    print(f"[INFO] Processed dir: {processed_dir}")
    print(f"[INFO] Subjects ({len(subjects)}): {', '.join(subjects)}")
    print(f"[INFO] Modalities: {', '.join(modalities)}")
    print("[INFO] Windows:")
    for w, rng in windows.items():
        print(f"  {w}: {rng[0]}-{rng[1]} ms")

    for sid in subjects:
        sub_dir = processed_dir / f"sub-{sid}"
        for modality in modalities:
            spec = MODALITIES[modality]
            epochs_path = sub_dir / spec["file"]

            amp_rows, count_rows, roi_rows, nan_rows, skip_rows = compute_subject_modality(
                subject_id=str(sid),
                modality=modality,
                epochs_path=epochs_path,
                roi_group=spec["roi_group"],
                windows=windows,
            )

            all_amp_rows.extend(amp_rows)
            all_count_rows.extend(count_rows)
            all_roi_rows.extend(roi_rows)
            all_nan_rows.extend(nan_rows)
            all_skip_rows.extend(skip_rows)

            if amp_rows:
                print(f"[OK] sub-{sid} {modality}: extracted {len(amp_rows)} rows")
            else:
                print(f"[WARN] sub-{sid} {modality}: no amplitude rows")

    amp_df = sort_output(pd.DataFrame(all_amp_rows), windows)
    count_df = sort_output(pd.DataFrame(all_count_rows), windows)
    roi_df = sort_output(pd.DataFrame(all_roi_rows), windows)
    nan_df = sort_output(pd.DataFrame(all_nan_rows), windows)
    skip_df = sort_output(pd.DataFrame(all_skip_rows), windows)

    paths = {
        "amplitudes": out_dir / "window_amplitudes_sens.csv",
        "counts": out_dir / "condition_counts_sens.csv",
        "roi": out_dir / "roi_channel_usage_sens.csv",
        "nan": out_dir / "channel_nan_report_sens.csv",
        "skipped": out_dir / "skipped_modality_epochs_sens.csv",
    }

    amp_df.to_csv(paths["amplitudes"], index=False)
    count_df.to_csv(paths["counts"], index=False)
    roi_df.to_csv(paths["roi"], index=False)
    nan_df.to_csv(paths["nan"], index=False)
    skip_df.to_csv(paths["skipped"], index=False)

    print(f"[OK] Wrote sensitivity ERP window table: {paths['amplitudes']}")
    print(f"[OK] Wrote sensitivity condition counts: {paths['counts']}")
    print(f"[OK] Wrote sensitivity ROI channel usage: {paths['roi']}")
    print(f"[OK] Wrote sensitivity channel NaN report: {paths['nan']}")
    print(f"[OK] Wrote sensitivity skipped modality report: {paths['skipped']}")

    if len(amp_df) == 0:
        print("[ERROR] No amplitude rows were generated.", file=sys.stderr)
        sys.exit(2)

    n_nan = int(amp_df["mean_amplitude"].isna().sum())
    if n_nan:
        print(f"[WARN] mean_amplitude contains {n_nan} NaN rows. Inspect ROI/channel usage and skipped reports.")
        nan_preview = amp_df[amp_df["mean_amplitude"].isna()].head(20)
        with pd.option_context("display.max_columns", None, "display.width", 180):
            print(nan_preview.to_string(index=False))
    else:
        print("[OK] No NaNs in sensitivity mean_amplitude.")

    # Quick sanity check for W5.
    if "W5" in set(amp_df["window"].astype(str)):
        w5 = amp_df[amp_df["window"].astype(str) == "W5"]
        print(f"[OK] W5 rows present: {len(w5)}")
    else:
        print("[WARN] W5 was not generated. Check config windows and sensitivity epoch time range.")


if __name__ == "__main__":
    main()
