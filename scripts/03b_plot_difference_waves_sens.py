#!/usr/bin/env python
"""
03b_plot_difference_waves_sens.py

Sensitivity version of ERP difference-wave plotting.

This script is identical in spirit to 03b_plot_difference_waves.py, but it uses
the sensitivity epoch files:

  scalp_sens-epo.fif
  ear_full_sens-epo.fif
  ear_strict_sens-epo.fif

and writes outputs to:

  reports/erp_diff_sens/

Contrasts:
  - Face - Non-face
  - Emotional - Neutral

Usage:
  python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml
  python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml --subjects 200 201 202
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import yaml
import mne

import matplotlib.pyplot as plt


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_output_root(cfg: dict) -> Path:
    return Path(cfg.get("output_root", "output"))


def get_subjects(cfg: dict, cli_subjects: Optional[List[str]]) -> List[str]:
    if cli_subjects:
        return [str(s) for s in cli_subjects]
    if "main_subjects" in cfg:
        return [str(s) for s in cfg["main_subjects"]]
    if "subjects_expected" in cfg:
        excluded = set(str(s) for s in cfg.get("subjects_exclude_main", []))
        return [str(s) for s in cfg["subjects_expected"] if str(s) not in excluded]
    raise ValueError("No subjects provided and no main_subjects/subjects_expected found in config.")


SCALP_ROIS: Dict[str, List[str]] = {
    "face_roi": ["P7", "P8", "TP7", "TP8", "O1", "O2"],
    "central_roi": ["Fz", "Cz", "Pz"],
    "late_roi": ["Pz", "CP1", "CP2", "Cz"],
}

EAR_ROIS: Dict[str, List[str]] = {
    "ear_full": ["Fpz", "M1", "M2", "EL1", "EL3", "EL4", "EL5", "ER1", "ER2", "ER3", "ER4"],
    "ear_strict": ["M1", "M2", "EL1", "EL3", "EL4", "EL5", "ER1", "ER2", "ER3", "ER4"],
    "ear_left": ["EL1", "EL3", "EL4", "EL5"],
    "ear_right": ["ER1", "ER2", "ER3", "ER4"],
    "ear_mastoid": ["M1", "M2"],
}


# Sensitivity epoch keys
PLOTS_TO_GENERATE: List[Tuple[str, str, str]] = [
    # Scalp sensitivity epochs
    ("scalp_sens", "face_vs_nonface", "face_roi"),
    ("scalp_sens", "face_vs_nonface", "central_roi"),
    ("scalp_sens", "face_vs_nonface", "late_roi"),
    ("scalp_sens", "emotional_vs_neutral", "face_roi"),

    # Ear sensitivity epochs
    ("ear_full_sens", "face_vs_nonface", "ear_full"),
    ("ear_strict_sens", "face_vs_nonface", "ear_strict"),
    ("ear_full_sens", "face_vs_nonface", "ear_right"),
    ("ear_full_sens", "emotional_vs_neutral", "ear_right"),
]


CONTRAST_LABELS = {
    "face_vs_nonface": ("face", "non_face", "Face - Non-face"),
    "emotional_vs_neutral": ("emotional", "neutral", "Emotional - Neutral"),
}


def get_roi_channels(modality_key: str, roi: str) -> List[str]:
    if modality_key.startswith("scalp"):
        return SCALP_ROIS[roi]
    return EAR_ROIS[roi]


def epoch_path(output_root: Path, sid: str, modality_key: str) -> Path:
    return output_root / "processed" / f"sub-{sid}" / f"{modality_key}-epo.fif"


def metadata_path(output_root: Path, sid: str) -> Path:
    return output_root / "processed" / f"sub-{sid}" / "metadata.csv"


def load_epochs_and_metadata(output_root: Path, sid: str, modality_key: str):
    p = epoch_path(output_root, sid, modality_key)
    if not p.exists():
        return None, None, f"missing_epoch_file:{p}"

    try:
        epochs = mne.read_epochs(p, preload=True, verbose="ERROR")
    except Exception as exc:
        return None, None, f"read_epochs_error:{exc}"

    if epochs.metadata is not None and len(epochs.metadata) == len(epochs):
        meta = epochs.metadata.copy()
    else:
        mp = metadata_path(output_root, sid)
        if not mp.exists():
            return None, None, f"missing_metadata_file:{mp}"
        meta = pd.read_csv(mp)
        if len(meta) != len(epochs):
            return None, None, f"metadata_length_mismatch:meta={len(meta)} epochs={len(epochs)}"

    return epochs, meta, ""


def build_condition_masks(meta: pd.DataFrame, contrast: str):
    if contrast == "face_vs_nonface":
        if "type" not in meta.columns:
            raise ValueError("Metadata has no 'type' column.")
        typ = meta["type"].astype(str).str.lower().str.strip()
        mask_a = (typ == "face").to_numpy()
        mask_b = (typ == "non_face").to_numpy()
        return mask_a, mask_b, "face", "non_face"

    if contrast == "emotional_vs_neutral":
        if "expression" not in meta.columns:
            raise ValueError("Metadata has no 'expression' column.")
        expr = meta["expression"].astype(str).str.lower().str.strip()
        mask_a = expr.isin(["happy", "angry", "afraid"]).to_numpy()
        mask_b = (expr == "neutral").to_numpy()
        return mask_a, mask_b, "emotional", "neutral"

    raise ValueError(f"Unknown contrast: {contrast}")


def compute_subject_difference(
    epochs: mne.Epochs,
    meta: pd.DataFrame,
    contrast: str,
    requested_channels: List[str],
):
    available = [ch for ch in requested_channels if ch in epochs.ch_names]
    missing = [ch for ch in requested_channels if ch not in epochs.ch_names]

    summary = {
        "requested_channels": ",".join(requested_channels),
        "used_channels": ",".join(available),
        "missing_channels": ",".join(missing),
        "n_used_channels": len(available),
        "n_a": 0,
        "n_b": 0,
        "status": "ok",
        "note": "",
    }

    if len(available) == 0:
        summary["status"] = "skipped"
        summary["note"] = "no_roi_channels_available"
        return None, summary

    mask_a, mask_b, cond_a, cond_b = build_condition_masks(meta, contrast)
    summary["n_a"] = int(mask_a.sum())
    summary["n_b"] = int(mask_b.sum())

    if mask_a.sum() == 0 or mask_b.sum() == 0:
        summary["status"] = "skipped"
        summary["note"] = f"empty_condition:{cond_a}={mask_a.sum()},{cond_b}={mask_b.sum()}"
        return None, summary

    ep_roi = epochs.copy().pick(available)
    data = ep_roi.get_data()

    with np.errstate(invalid="ignore"):
        wave_a = np.nanmean(data[mask_a, :, :], axis=(0, 1))
        wave_b = np.nanmean(data[mask_b, :, :], axis=(0, 1))
        diff = wave_a - wave_b

    if np.all(np.isnan(diff)):
        summary["status"] = "skipped"
        summary["note"] = "all_nan_difference_wave"
        return None, summary

    return diff, summary


def sem_ignore_nan(x: np.ndarray, axis: int = 0) -> np.ndarray:
    n = np.sum(np.isfinite(x), axis=axis)
    sd = np.nanstd(x, axis=axis, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return sd / np.sqrt(n)


def add_erp_windows(ax, cfg: dict):
    windows = cfg.get("erp_windows_ms", {
        "W1": [80, 130],
        "W2": [130, 220],
        "W3": [220, 320],
        "W4": [320, 600],
    })

    for name, (start, end) in windows.items():
        ax.axvspan(start, end, alpha=0.08)
        ax.text(
            (start + end) / 2,
            0.98,
            name,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=8,
        )


def plot_difference_wave(
    times_ms: np.ndarray,
    diffs: np.ndarray,
    modality_key: str,
    contrast: str,
    roi: str,
    n_subjects: int,
    out_png: Path,
    cfg: dict,
):
    mean = np.nanmean(diffs, axis=0)
    sem = sem_ignore_nan(diffs, axis=0)

    title_label = CONTRAST_LABELS[contrast][2]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(times_ms, mean, linewidth=2, label=f"{title_label}")
    ax.fill_between(times_ms, mean - sem, mean + sem, alpha=0.25, label="± SEM")

    ax.axvline(0, linestyle="--", linewidth=1)
    ax.axhline(0, linestyle="-", linewidth=0.8)

    add_erp_windows(ax, cfg)

    ax.set_title(f"{title_label} | {modality_key} | {roi} | n={n_subjects}")
    ax.set_xlabel("Time from stimulus onset (ms)")
    ax.set_ylabel("Difference amplitude (a.u. / µV if scaled)")
    ax.legend(loc="best", frameon=False)
    ax.set_xlim(times_ms[0], times_ms[-1])

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument("--output-dir", default="reports/erp_diff_sens")
    args = parser.parse_args()

    cfg = load_config(args.config)
    output_root = get_output_root(cfg)
    subjects = get_subjects(cfg, args.subjects)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_subject_rows = []
    grand_rows = []

    for modality_key, contrast, roi in PLOTS_TO_GENERATE:
        requested_channels = get_roi_channels(modality_key, roi)
        subject_diffs = []
        used_subjects = []
        times_ms = None

        for sid in subjects:
            epochs, meta, err = load_epochs_and_metadata(output_root, sid, modality_key)
            row_base = {
                "subject_id": sid,
                "modality": modality_key,
                "contrast": contrast,
                "roi": roi,
            }

            if epochs is None:
                all_subject_rows.append({
                    **row_base,
                    "status": "skipped",
                    "note": err,
                    "requested_channels": ",".join(requested_channels),
                    "used_channels": "",
                    "missing_channels": "",
                    "n_used_channels": 0,
                    "n_a": 0,
                    "n_b": 0,
                })
                continue

            diff, summary = compute_subject_difference(epochs, meta, contrast, requested_channels)
            all_subject_rows.append({**row_base, **summary})

            if diff is None:
                continue

            subject_diffs.append(diff)
            used_subjects.append(sid)
            if times_ms is None:
                times_ms = epochs.times * 1000.0

        label = f"{modality_key}_{contrast}_{roi}"
        if len(subject_diffs) == 0:
            print(f"[WARN] {label}: no usable subjects; skipped plot.")
            continue

        diffs = np.vstack(subject_diffs)
        n_subjects = diffs.shape[0]

        out_png = out_dir / f"{label}.png"
        plot_difference_wave(times_ms, diffs, modality_key, contrast, roi, n_subjects, out_png, cfg)

        mean = np.nanmean(diffs, axis=0)
        sem = sem_ignore_nan(diffs, axis=0)
        grand_df = pd.DataFrame({
            "time_ms": times_ms,
            "mean_diff": mean,
            "sem": sem,
            "n_subjects": n_subjects,
        })
        grand_csv = out_dir / f"{label}_grand_average.csv"
        grand_df.to_csv(grand_csv, index=False)

        grand_rows.append({
            "modality": modality_key,
            "contrast": contrast,
            "roi": roi,
            "n_subjects": n_subjects,
            "subjects": ",".join(used_subjects),
            "plot": str(out_png),
            "grand_average_csv": str(grand_csv),
        })

        print(f"[OK] {label}: n={n_subjects}, wrote {out_png}")

    subj_summary = pd.DataFrame(all_subject_rows)
    subj_summary.to_csv(out_dir / "difference_wave_subject_summary.csv", index=False)

    grand_summary = pd.DataFrame(grand_rows)
    grand_summary.to_csv(out_dir / "difference_wave_grand_summary.csv", index=False)

    print(f"[OK] Wrote subject summary: {out_dir / 'difference_wave_subject_summary.csv'}")
    print(f"[OK] Wrote grand summary: {out_dir / 'difference_wave_grand_summary.csv'}")


if __name__ == "__main__":
    main()
