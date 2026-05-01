#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03g_plot_w4_topography.py

Scalp topography for the LEMON/MELON Emotional Affect ERP analysis.

Goal
----
Create scalp topographic maps for the Face - Non-face ERP difference in W4
(320-600 ms), using the already-preprocessed scalp sensitivity epochs:

    output/processed/sub-XXX/scalp_sens-epo.fif

Recommended run
---------------
    python scripts/03g_plot_w4_topography.py --config configs/config.yaml

Optional all-window panel:
    python scripts/03g_plot_w4_topography.py --config configs/config.yaml --all-windows

Main outputs
------------
    reports/topography/scalp_sens_face_vs_nonface_W4_topomap.png
    reports/topography/scalp_sens_face_vs_nonface_W4_topomap.pdf
    reports/topography/scalp_sens_face_vs_nonface_W4_channel_values.csv
    reports/topography/scalp_sens_face_vs_nonface_W4_subject_channel_values.csv
    reports/topography/scalp_sens_face_vs_nonface_W4_channel_n_subjects.csv
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

try:
    import yaml
except Exception:
    yaml = None

try:
    import mne
except Exception as exc:
    raise RuntimeError("MNE-Python is required for topography plotting.") from exc

import matplotlib.pyplot as plt


DEFAULT_WINDOWS_MS = {
    "W1": [80, 130],
    "W2": [130, 220],
    "W3": [220, 320],
    "W4": [320, 600],
    "W5": [600, 800],
}

SCALP_FILE = "scalp_sens-epo.fif"

CANONICAL_NAMES = {
    "fp1": "Fp1", "fp2": "Fp2", "fpz": "Fpz",
    "f7": "F7", "f3": "F3", "fz": "Fz", "f4": "F4", "f8": "F8",
    "fc5": "FC5", "fc1": "FC1", "fc2": "FC2", "fc6": "FC6",
    "t7": "T7", "c3": "C3", "cz": "Cz", "c4": "C4", "t8": "T8",
    "tp7": "TP7", "cp5": "CP5", "cp1": "CP1", "cp2": "CP2", "cp6": "CP6", "tp8": "TP8",
    "p7": "P7", "p3": "P3", "pz": "Pz", "p4": "P4", "p8": "P8",
    "o1": "O1", "o2": "O2",
}

CHANNEL_ORDER = [
    "Fp1", "Fpz", "Fp2",
    "F7", "F3", "Fz", "F4", "F8",
    "FC5", "FC1", "FC2", "FC6",
    "T7", "C3", "Cz", "C4", "T8",
    "TP7", "CP5", "CP1", "CP2", "CP6", "TP8",
    "P7", "P3", "Pz", "P4", "P8",
    "O1", "O2",
]


def load_yaml(path: Path) -> dict:
    if path.exists() and yaml is not None:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_project_root(config: dict) -> Path:
    for key in ["root", "root_dir", "data_root", "bids_root", "project_root"]:
        if config.get(key):
            return Path(config[key])
    return Path.cwd()


def get_processed_dir(config: dict, root: Path) -> Path:
    for key in ["processed_dir", "output_processed_dir"]:
        if config.get(key):
            p = Path(config[key])
            return p if p.is_absolute() else root / p
    return root / "output" / "processed"


def get_manifest_path(config: dict, root: Path) -> Path:
    for key in ["manifest", "manifest_path", "subject_manifest"]:
        if config.get(key):
            p = Path(config[key])
            return p if p.is_absolute() else root / p
    return root / "output" / "manifests" / "subject_manifest.csv"


def get_windows(config: dict) -> Dict[str, List[float]]:
    windows = (
        config.get("erp_windows_ms")
        or config.get("erp_windows")
        or config.get("windows")
        or DEFAULT_WINDOWS_MS
    )
    windows = {str(k): list(v) for k, v in windows.items()}
    if "W5" not in windows:
        windows["W5"] = [600, 800]
    return windows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def canonical_ch_name(ch: str) -> str:
    return CANONICAL_NAMES.get(str(ch).strip().lower(), str(ch).strip())


def subject_sort_key(s: str):
    s2 = str(s).replace("sub-", "")
    return int(s2) if s2.isdigit() else s2


def get_subjects(subjects_arg: Optional[List[str]], manifest_path: Path, processed_dir: Path) -> List[str]:
    if subjects_arg:
        return sorted([str(s).replace("sub-", "") for s in subjects_arg], key=subject_sort_key)

    if manifest_path.exists():
        try:
            df = pd.read_csv(manifest_path)
            for col in ["subject_id", "subject", "participant_id", "sub"]:
                if col in df.columns:
                    vals = df[col].dropna().astype(str).str.replace("sub-", "", regex=False).tolist()
                    for usable_col in ["usable", "is_usable", "main", "is_main", "include"]:
                        if usable_col in df.columns:
                            mask = df[usable_col].astype(str).str.lower().isin(["true", "1", "yes", "main", "usable"])
                            if mask.sum() > 0:
                                vals = df.loc[mask, col].dropna().astype(str).str.replace("sub-", "", regex=False).tolist()
                            break
                    return sorted(set(vals), key=subject_sort_key)
        except Exception:
            pass

    if processed_dir.exists():
        vals = []
        for p in processed_dir.iterdir():
            if p.is_dir() and p.name.startswith("sub-") and (p / SCALP_FILE).exists():
                vals.append(p.name.replace("sub-", ""))
        return sorted(set(vals), key=subject_sort_key)

    return []


def pick_metadata_col(metadata: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    lower = {c.lower(): c for c in metadata.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def condition_masks(metadata: pd.DataFrame) -> Dict[str, np.ndarray]:
    n = len(metadata)
    masks = {
        "face": np.zeros(n, dtype=bool),
        "non_face": np.zeros(n, dtype=bool),
    }

    type_col = pick_metadata_col(metadata, ["type", "stim_type", "category"])
    if type_col is not None:
        typ = metadata[type_col].astype(str).str.lower().str.strip()
        masks["face"] = typ.eq("face").to_numpy()
        masks["non_face"] = typ.isin(["non_face", "non-face", "nonface", "tree", "object"]).to_numpy()

    return masks


def rename_epochs_to_canonical(epochs: mne.Epochs) -> mne.Epochs:
    rename = {}
    seen = set()
    for ch in epochs.ch_names:
        can = canonical_ch_name(ch)
        # Avoid accidental duplicate names.
        if can in seen and can != ch:
            continue
        seen.add(can)
        if can != ch:
            rename[ch] = can
    if rename:
        epochs = epochs.copy().rename_channels(rename)
    return epochs


def compute_subject_channel_difference(
    epochs: mne.Epochs,
    subject_id: str,
    window_name: str,
    start_ms: float,
    end_ms: float,
) -> List[dict]:
    if epochs.metadata is None:
        return []

    metadata = epochs.metadata.reset_index(drop=True)
    masks = condition_masks(metadata)
    face_mask = masks["face"]
    nonface_mask = masks["non_face"]

    if face_mask.sum() == 0 or nonface_mask.sum() == 0:
        return []

    times_ms = epochs.times * 1000.0
    tmask = (times_ms >= start_ms) & (times_ms <= end_ms)
    if tmask.sum() == 0:
        return []

    data = epochs.get_data(copy=True)
    rows = []

    for ci, ch in enumerate(epochs.ch_names):
        can_ch = canonical_ch_name(ch)
        segment = data[:, ci, :][:, tmask]

        face_segment = segment[face_mask, :]
        nonface_segment = segment[nonface_mask, :]

        face_val = float(np.nanmean(face_segment)) if np.isfinite(face_segment).any() else np.nan
        nonface_val = float(np.nanmean(nonface_segment)) if np.isfinite(nonface_segment).any() else np.nan
        diff = face_val - nonface_val if np.isfinite(face_val) and np.isfinite(nonface_val) else np.nan

        rows.append({
            "subject_id": str(subject_id),
            "window": window_name,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "channel": can_ch,
            "n_face_epochs": int(face_mask.sum()),
            "n_nonface_epochs": int(nonface_mask.sum()),
            "face_mean": face_val,
            "nonface_mean": nonface_val,
            "difference": diff,
        })

    return rows


def aggregate_channel_values(subject_rows: pd.DataFrame, min_subjects: int = 3) -> pd.DataFrame:
    if subject_rows.empty:
        return pd.DataFrame()

    g = (
        subject_rows
        .dropna(subset=["difference"])
        .groupby(["window", "start_ms", "end_ms", "channel"], dropna=False)
        .agg(
            n_subjects=("subject_id", "nunique"),
            mean_difference=("difference", "mean"),
            median_difference=("difference", "median"),
            std_difference=("difference", "std"),
            sem_difference=("difference", lambda x: np.nanstd(x, ddof=1) / math.sqrt(len(x)) if len(x) > 1 else np.nan),
        )
        .reset_index()
    )

    g["include_in_topomap"] = g["n_subjects"] >= min_subjects
    order = {ch: i for i, ch in enumerate(CHANNEL_ORDER)}
    g["_order"] = g["channel"].map(order).fillna(999).astype(int)
    g = g.sort_values(["window", "_order", "channel"]).drop(columns=["_order"])
    return g


def build_info_for_channels(channels: List[str]) -> mne.Info:
    info = mne.create_info(ch_names=channels, sfreq=250.0, ch_types="eeg")
    montage = mne.channels.make_standard_montage("standard_1020")
    info.set_montage(montage, match_case=False, on_missing="ignore")
    return info


def filter_channels_with_positions(channels: List[str], values: np.ndarray):
    info = build_info_for_channels(channels)
    pos = np.array([info["chs"][i]["loc"][:3] for i in range(len(channels))])
    good_pos = np.isfinite(pos).all(axis=1) & (np.linalg.norm(pos, axis=1) > 0)
    channels_good = [ch for ch, ok in zip(channels, good_pos) if ok]
    values_good = values[good_pos]
    return channels_good, values_good


def plot_single_topomap(
    channel_values: pd.DataFrame,
    window_name: str,
    output_base: Path,
    title: str,
    min_subjects: int = 3,
) -> None:
    sub = channel_values[
        (channel_values["window"] == window_name)
        & (channel_values["include_in_topomap"])
    ].copy()

    if sub.empty:
        raise RuntimeError(f"No channels available for topomap in {window_name} with min_subjects={min_subjects}")

    channels = sub["channel"].tolist()
    values = sub["mean_difference"].to_numpy(dtype=float)
    channels, values = filter_channels_with_positions(channels, values)

    if len(channels) < 4:
        raise RuntimeError(f"Too few channels with valid montage positions for topomap: {channels}")

    info = build_info_for_channels(channels)
    vmax = np.nanmax(np.abs(values))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im, _ = mne.viz.plot_topomap(
        values,
        info,
        axes=ax,
        show=False,
        names=channels,
        sensors=True,
        contours=6,
        cmap="RdBu_r",
        vlim=(-vmax, vmax),
    )
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Face - Non-face mean amplitude difference")
    ax.set_title(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(output_base.with_suffix(".png"), dpi=300)
    fig.savefig(output_base.with_suffix(".pdf"))
    plt.close(fig)

    print(f"[OK] Wrote: {output_base.with_suffix('.png')}")
    print(f"[OK] Wrote: {output_base.with_suffix('.pdf')}")


def plot_all_windows_topomap(
    channel_values: pd.DataFrame,
    windows_to_plot: List[str],
    output_base: Path,
    min_subjects: int = 3,
) -> None:
    vals_all = []
    panel_data = []

    for w in windows_to_plot:
        sub = channel_values[
            (channel_values["window"] == w)
            & (channel_values["include_in_topomap"])
        ].copy()
        if sub.empty:
            continue

        channels = sub["channel"].tolist()
        values = sub["mean_difference"].to_numpy(dtype=float)
        channels, values = filter_channels_with_positions(channels, values)

        if len(channels) >= 4:
            vals_all.extend(values[np.isfinite(values)].tolist())
            panel_data.append((w, channels, values))

    if not panel_data:
        raise RuntimeError("No windows available for all-window topomap.")

    vmax = np.nanmax(np.abs(vals_all))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    n = len(panel_data)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n, 4.2))
    if n == 1:
        axes = [axes]

    last_im = None
    for ax, (w, channels, values) in zip(axes, panel_data):
        info = build_info_for_channels(channels)
        last_im, _ = mne.viz.plot_topomap(
            values,
            info,
            axes=ax,
            show=False,
            names=None,
            sensors=True,
            contours=5,
            cmap="RdBu_r",
            vlim=(-vmax, vmax),
        )
        ax.set_title(w, fontsize=11)

    cbar = fig.colorbar(last_im, ax=axes, fraction=0.025, pad=0.04)
    cbar.set_label("Face - Non-face mean amplitude difference")
    fig.suptitle("Scalp topography across ERP windows", fontsize=14)
    fig.tight_layout(rect=[0, 0, 0.95, 0.92])
    fig.savefig(output_base.with_suffix(".png"), dpi=300)
    fig.savefig(output_base.with_suffix(".pdf"))
    plt.close(fig)

    print(f"[OK] Wrote: {output_base.with_suffix('.png')}")
    print(f"[OK] Wrote: {output_base.with_suffix('.pdf')}")


def write_readme(out_dir: Path, min_subjects: int) -> None:
    text = f"""# Scalp Topography Outputs

Generated by:

```bash
python scripts/03g_plot_w4_topography.py --config configs/config.yaml --all-windows
```

## Main topography

- `scalp_sens_face_vs_nonface_W4_topomap.png`
- `scalp_sens_face_vs_nonface_W4_topomap.pdf`

This figure shows the scalp distribution of the Face - Non-face mean amplitude
difference in W4 = 320-600 ms.

## Optional all-window topography

- `scalp_sens_face_vs_nonface_W1_W5_topomaps.png`
- `scalp_sens_face_vs_nonface_W1_W5_topomaps.pdf`

## CSV files

- `scalp_sens_face_vs_nonface_W4_subject_channel_values.csv`
  - Subject-level Face and Non-face values per channel.

- `scalp_sens_face_vs_nonface_W4_channel_values.csv`
  - Channel-level group summary across all extracted windows.

- `scalp_sens_face_vs_nonface_W4_channel_n_subjects.csv`
  - Number of subjects contributing to each W4 channel.

## Inclusion rule

Channels are included in the topomap if they have valid values from at least:

```text
min_subjects = {min_subjects}
```

This is needed because some subjects have bad channels removed during QC.

## Interpretation

This topography is a supporting scalp-only visualization. It supports the ROI-based
ERP findings but is not a standalone inferential test.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")
    print(f"[OK] Wrote: {out_dir / 'README.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot scalp W4 topography for Face - Non-face ERP difference.")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--subjects", nargs="*", default=None, help="Optional subject IDs")
    parser.add_argument("--processed-dir", default=None, help="Override processed dir")
    parser.add_argument("--out-dir", default="reports/topography", help="Output directory")
    parser.add_argument("--window", default="W4", help="Window to plot. Default: W4")
    parser.add_argument("--min-subjects", type=int, default=3, help="Minimum subjects per channel for topomap")
    parser.add_argument("--all-windows", action="store_true", help="Also plot W1-W5 topomaps in one panel")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_yaml(config_path)
    root = get_project_root(config)
    windows = get_windows(config)

    if args.window not in windows:
        print(f"[ERROR] Window {args.window} not found in config. Available: {list(windows)}", file=sys.stderr)
        sys.exit(1)

    processed_dir = Path(args.processed_dir) if args.processed_dir else get_processed_dir(config, root)
    if not processed_dir.is_absolute():
        processed_dir = root / processed_dir

    manifest_path = get_manifest_path(config, root)
    subjects = get_subjects(args.subjects, manifest_path, processed_dir)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    ensure_dir(out_dir)

    print(f"[INFO] Processed dir: {processed_dir}")
    print(f"[INFO] Output dir: {out_dir}")
    print(f"[INFO] Subjects candidate count: {len(subjects)}")
    print(f"[INFO] Main window: {args.window} = {windows[args.window][0]}-{windows[args.window][1]} ms")

    all_rows = []
    skipped = []

    for sid in subjects:
        epo_path = processed_dir / f"sub-{sid}" / SCALP_FILE
        if not epo_path.exists():
            skipped.append({"subject_id": sid, "reason": "missing_scalp_sens_epoch_file", "path": str(epo_path)})
            continue

        try:
            epochs = mne.read_epochs(epo_path, preload=True, verbose="ERROR")
            epochs = rename_epochs_to_canonical(epochs)
            epochs.pick_types(eeg=True, exclude=[])
        except Exception as exc:
            skipped.append({"subject_id": sid, "reason": f"read_error:{exc}", "path": str(epo_path)})
            continue

        if len(epochs) == 0:
            skipped.append({"subject_id": sid, "reason": "empty_epochs", "path": str(epo_path)})
            continue

        if epochs.metadata is None:
            skipped.append({"subject_id": sid, "reason": "missing_metadata", "path": str(epo_path)})
            continue

        subject_added = 0
        for w, (start_ms, end_ms) in windows.items():
            rows = compute_subject_channel_difference(
                epochs=epochs,
                subject_id=sid,
                window_name=w,
                start_ms=float(start_ms),
                end_ms=float(end_ms),
            )
            all_rows.extend(rows)
            subject_added += len(rows)

        print(f"[OK] sub-{sid}: added {subject_added} channel-window rows")

    subject_df = pd.DataFrame(all_rows)
    skipped_df = pd.DataFrame(skipped)

    subject_out = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_subject_channel_values.csv"
    skipped_out = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_skipped_subjects.csv"

    if subject_df.empty:
        subject_df.to_csv(subject_out, index=False)
        skipped_df.to_csv(skipped_out, index=False)
        print("[ERROR] No subject-channel rows generated. Cannot plot topography.", file=sys.stderr)
        sys.exit(2)

    subject_df.to_csv(subject_out, index=False)
    skipped_df.to_csv(skipped_out, index=False)

    channel_df = aggregate_channel_values(subject_df, min_subjects=args.min_subjects)
    channel_out = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_channel_values.csv"
    channel_df.to_csv(channel_out, index=False)

    nsub = channel_df[channel_df["window"] == args.window][["channel", "n_subjects", "include_in_topomap"]].copy()
    nsub_out = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_channel_n_subjects.csv"
    nsub.to_csv(nsub_out, index=False)

    print(f"[OK] Wrote subject-channel values: {subject_out}")
    print(f"[OK] Wrote channel summary: {channel_out}")
    print(f"[OK] Wrote channel n-subjects: {nsub_out}")
    print(f"[OK] Wrote skipped subjects: {skipped_out}")

    start_ms, end_ms = windows[args.window]
    plot_single_topomap(
        channel_values=channel_df,
        window_name=args.window,
        output_base=out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap",
        title=f"Scalp topography: Face - Non-face, {args.window} ({start_ms}-{end_ms} ms)",
        min_subjects=args.min_subjects,
    )

    if args.all_windows:
        windows_to_plot = [w for w in ["W1", "W2", "W3", "W4", "W5"] if w in windows]
        plot_all_windows_topomap(
            channel_values=channel_df,
            windows_to_plot=windows_to_plot,
            output_base=out_dir / "scalp_sens_face_vs_nonface_W1_W5_topomaps",
            min_subjects=args.min_subjects,
        )

    wsub = channel_df[(channel_df["window"] == args.window) & (channel_df["include_in_topomap"])].copy()
    wsub = wsub.sort_values("mean_difference", ascending=False)

    print("\n=== Top positive channels ===")
    with pd.option_context("display.max_columns", None, "display.width", 140):
        print(wsub[["channel", "n_subjects", "mean_difference", "sem_difference"]].head(10).to_string(index=False))

    print("\n=== Top negative channels ===")
    with pd.option_context("display.max_columns", None, "display.width", 140):
        print(wsub[["channel", "n_subjects", "mean_difference", "sem_difference"]].tail(10).to_string(index=False))

    write_readme(out_dir, args.min_subjects)


if __name__ == "__main__":
    main()
