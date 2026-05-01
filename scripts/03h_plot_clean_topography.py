#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03h_plot_clean_topography.py

Publication-friendly scalp topography variants for the LEMON/MELON ERP analysis.

Why this script exists
----------------------
The first W4 topomap showed a meaningful posterior/centro-parietal positivity
for Face - Non-face, but the color scale was dominated by very large frontal-pole
values at Fp1/Fp2/Fpz. Those channels are highly sensitive to ocular/frontal
activity and can visually compress the posterior effect.

This script creates cleaner supporting figures:

1) no-Fp topomap
   - excludes Fp1, Fp2, Fpz from visualization.
   - recommended for the main report if the goal is to show the posterior/central W4 pattern.

2) robust-scale topomap
   - keeps all channels, including Fp1/Fp2/Fpz.
   - computes the color scale from non-Fp channels, so Fp channels may saturate.
   - useful as a transparency/sensitivity figure.

3) clean comparison panel
   - side-by-side figure with no-Fp and robust-scale versions.

Important interpretation
------------------------
These are visualization-only figures. They do not change the ERP statistics.
They are meant to support the ROI-level subject statistics, not replace them.

Recommended run
---------------
    python scripts/03h_plot_clean_topography.py --config configs/config.yaml

Optional:
    python scripts/03h_plot_clean_topography.py --config configs/config.yaml --window W4 --percentile 95

Inputs
------
    reports/topography/scalp_sens_face_vs_nonface_W4_channel_values.csv

Outputs
-------
    reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_no_fp.png/pdf
    reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_robust_scale.png/pdf
    reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_clean_panel.png/pdf
    reports/topography_clean/scalp_sens_face_vs_nonface_W4_channel_values_clean_used.csv
    reports/topography_clean/README.md
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

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


FP_CHANNELS = {"Fp1", "Fp2", "Fpz"}

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


def canonical_ch_name(ch: str) -> str:
    return CANONICAL_NAMES.get(str(ch).strip().lower(), str(ch).strip())


def build_info_for_channels(channels: List[str]) -> mne.Info:
    info = mne.create_info(ch_names=channels, sfreq=250.0, ch_types="eeg")
    montage = mne.channels.make_standard_montage("standard_1020")
    info.set_montage(montage, match_case=False, on_missing="ignore")
    return info


def filter_channels_with_positions(channels: List[str], values: np.ndarray) -> Tuple[List[str], np.ndarray]:
    info = build_info_for_channels(channels)
    pos = np.array([info["chs"][i]["loc"][:3] for i in range(len(channels))])
    good_pos = np.isfinite(pos).all(axis=1) & (np.linalg.norm(pos, axis=1) > 0)
    channels_good = [ch for ch, ok in zip(channels, good_pos) if ok]
    values_good = values[good_pos]
    return channels_good, values_good


def symmetric_vlim(values: np.ndarray, percentile: float | None = None) -> Tuple[float, float]:
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        vmax = 1.0
    elif percentile is None:
        vmax = float(np.nanmax(np.abs(vals)))
    else:
        vmax = float(np.nanpercentile(np.abs(vals), percentile))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0
    return -vmax, vmax


def prepare_channel_table(df: pd.DataFrame, window: str, min_subjects: int) -> pd.DataFrame:
    required = {"window", "channel", "mean_difference", "n_subjects"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    out = df.copy()
    out["channel"] = out["channel"].map(canonical_ch_name)
    out = out[(out["window"].astype(str) == window) & (out["n_subjects"] >= min_subjects)].copy()

    order = {ch: i for i, ch in enumerate(CHANNEL_ORDER)}
    out["_order"] = out["channel"].map(order).fillna(999).astype(int)
    out = out.sort_values(["_order", "channel"]).drop(columns=["_order"])

    if out.empty:
        raise ValueError(f"No channels available for window={window} with min_subjects={min_subjects}")

    out["is_fp_channel"] = out["channel"].isin(FP_CHANNELS)
    return out


def plot_topomap_from_table(
    table: pd.DataFrame,
    output_base: Path,
    title: str,
    vlim: Tuple[float, float],
    show_names: bool = True,
) -> None:
    channels = table["channel"].tolist()
    values = table["mean_difference"].to_numpy(dtype=float)

    channels, values = filter_channels_with_positions(channels, values)

    if len(channels) < 4:
        raise ValueError(f"Too few channels with valid montage positions: {channels}")

    info = build_info_for_channels(channels)

    fig, ax = plt.subplots(figsize=(6.7, 5.7))
    im, _ = mne.viz.plot_topomap(
        values,
        info,
        axes=ax,
        show=False,
        names=channels if show_names else None,
        sensors=True,
        contours=6,
        cmap="RdBu_r",
        vlim=vlim,
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


def plot_panel(
    no_fp_table: pd.DataFrame,
    all_table: pd.DataFrame,
    output_base: Path,
    no_fp_vlim: Tuple[float, float],
    robust_vlim: Tuple[float, float],
    window: str,
    percentile: float,
) -> None:
    panels = [
        (
            no_fp_table,
            f"{window}: no Fp channels\nscale from remaining channels",
            no_fp_vlim,
        ),
        (
            all_table,
            f"{window}: all channels, robust scale\nscale from non-Fp p{percentile:g}",
            robust_vlim,
        ),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    last_im = None

    for ax, (table, title, vlim) in zip(axes, panels):
        channels = table["channel"].tolist()
        values = table["mean_difference"].to_numpy(dtype=float)
        channels, values = filter_channels_with_positions(channels, values)
        info = build_info_for_channels(channels)

        last_im, _ = mne.viz.plot_topomap(
            values,
            info,
            axes=ax,
            show=False,
            names=channels,
            sensors=True,
            contours=6,
            cmap="RdBu_r",
            vlim=vlim,
        )
        ax.set_title(title, fontsize=11)

    cbar = fig.colorbar(last_im, ax=axes, fraction=0.025, pad=0.04)
    cbar.set_label("Face - Non-face mean amplitude difference")
    fig.suptitle("Clean scalp topography variants for Face - Non-face", fontsize=14)
    fig.tight_layout(rect=[0, 0, 0.94, 0.92])
    fig.savefig(output_base.with_suffix(".png"), dpi=300)
    fig.savefig(output_base.with_suffix(".pdf"))
    plt.close(fig)

    print(f"[OK] Wrote: {output_base.with_suffix('.png')}")
    print(f"[OK] Wrote: {output_base.with_suffix('.pdf')}")


def write_readme(
    out_dir: Path,
    input_csv: Path,
    window: str,
    min_subjects: int,
    percentile: float,
) -> None:
    text = f"""# Clean Topography Outputs

Generated by:

```bash
python scripts/03h_plot_clean_topography.py --config configs/config.yaml
```

## Input

```text
{input_csv}
```

## Window

```text
{window}
```

## Inclusion rule

Channels are included if they have values from at least:

```text
min_subjects = {min_subjects}
```

## Why these figures were generated

The original W4 topomap showed strong frontal-pole values at Fp1/Fp2/Fpz.
These channels can dominate the color scale and visually compress the posterior
Face - Non-face positivity.

Therefore, this script generates two cleaner visualization variants:

1. `*_topomap_no_fp.*`
   - Fp1, Fp2, and Fpz are removed from the visualization.
   - Recommended for the main report if the focus is posterior/central W4 distribution.

2. `*_topomap_robust_scale.*`
   - Fp1, Fp2, and Fpz are kept.
   - Color scale is computed from non-Fp channels using percentile {percentile:g}.
   - Frontal-pole channels may saturate, but the rest of the scalp remains interpretable.

3. `*_topomap_clean_panel.*`
   - Side-by-side comparison of both variants.

## Interpretation

These figures are supporting visualizations only. They do not modify the
subject-level ERP statistics. The main inferential results remain the planned
ROI-level W4 and W4-vs-W5 analyses.

Recommended wording:

> The W4 Face - Non-face scalp topography showed a posterior-to-centroparietal
> positive distribution. Because frontal-pole channels showed large opposite-polarity
> values and may be sensitive to residual ocular/frontal activity, a complementary
> no-Fp visualization was used to inspect the posterior scalp pattern.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")
    print(f"[OK] Wrote: {out_dir / 'README.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create clean W4 topography variants.")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--input", default="reports/topography/scalp_sens_face_vs_nonface_W4_channel_values.csv",
                        help="Channel values CSV from 03g_plot_w4_topography.py")
    parser.add_argument("--out-dir", default="reports/topography_clean", help="Output directory")
    parser.add_argument("--window", default="W4", help="Window to plot. Default: W4")
    parser.add_argument("--min-subjects", type=int, default=3, help="Minimum subjects per channel")
    parser.add_argument("--percentile", type=float, default=95.0,
                        help="Percentile of non-Fp absolute values for robust scale")
    parser.add_argument("--no-names", action="store_true", help="Do not draw channel names")
    args = parser.parse_args()

    config = load_yaml(Path(args.config))
    root = get_project_root(config)

    input_csv = Path(args.input)
    if not input_csv.is_absolute():
        input_csv = root / input_csv

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {input_csv}\n"
            "Run 03g first:\n"
            "python scripts/03g_plot_w4_topography.py --config configs/config.yaml"
        )

    df = pd.read_csv(input_csv)
    table = prepare_channel_table(df, window=args.window, min_subjects=args.min_subjects)

    no_fp = table[~table["is_fp_channel"]].copy()
    fp = table[table["is_fp_channel"]].copy()

    if no_fp.empty:
        raise ValueError("No non-Fp channels available after filtering.")

    no_fp_vlim = symmetric_vlim(no_fp["mean_difference"].to_numpy(dtype=float), percentile=None)
    robust_vlim = symmetric_vlim(no_fp["mean_difference"].to_numpy(dtype=float), percentile=args.percentile)

    used_csv = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_channel_values_clean_used.csv"
    table.to_csv(used_csv, index=False)
    print(f"[OK] Wrote: {used_csv}")

    # no-Fp topomap
    plot_topomap_from_table(
        table=no_fp,
        output_base=out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap_no_fp",
        title=f"Scalp topography: Face - Non-face, {args.window} no-Fp",
        vlim=no_fp_vlim,
        show_names=not args.no_names,
    )

    # robust-scale topomap with all channels
    plot_topomap_from_table(
        table=table,
        output_base=out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap_robust_scale",
        title=f"Scalp topography: Face - Non-face, {args.window} robust scale",
        vlim=robust_vlim,
        show_names=not args.no_names,
    )

    # panel
    plot_panel(
        no_fp_table=no_fp,
        all_table=table,
        output_base=out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap_clean_panel",
        no_fp_vlim=no_fp_vlim,
        robust_vlim=robust_vlim,
        window=args.window,
        percentile=args.percentile,
    )

    # summary
    summary_rows = []
    for label, sub in [("all", table), ("no_fp", no_fp), ("fp_only", fp)]:
        vals = sub["mean_difference"].to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        summary_rows.append({
            "set": label,
            "n_channels": len(sub),
            "mean": float(np.nanmean(vals)) if vals.size else np.nan,
            "median": float(np.nanmedian(vals)) if vals.size else np.nan,
            "min": float(np.nanmin(vals)) if vals.size else np.nan,
            "max": float(np.nanmax(vals)) if vals.size else np.nan,
            "vlim_low_no_fp_plot": no_fp_vlim[0] if label == "no_fp" else np.nan,
            "vlim_high_no_fp_plot": no_fp_vlim[1] if label == "no_fp" else np.nan,
            "vlim_low_robust_plot": robust_vlim[0] if label == "all" else np.nan,
            "vlim_high_robust_plot": robust_vlim[1] if label == "all" else np.nan,
        })

    summary = pd.DataFrame(summary_rows)
    summary_csv = out_dir / f"scalp_sens_face_vs_nonface_{args.window}_clean_topography_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"[OK] Wrote: {summary_csv}")

    write_readme(
        out_dir=out_dir,
        input_csv=input_csv,
        window=args.window,
        min_subjects=args.min_subjects,
        percentile=args.percentile,
    )

    print("\n=== Frontal-pole channels ===")
    if fp.empty:
        print("None")
    else:
        print(fp[["channel", "n_subjects", "mean_difference", "sem_difference"]].to_string(index=False))

    print("\n=== Clean top positive non-Fp channels ===")
    print(no_fp.sort_values("mean_difference", ascending=False)[
        ["channel", "n_subjects", "mean_difference", "sem_difference"]
    ].head(10).to_string(index=False))

    print("\n=== Recommended main-report figure ===")
    print(out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap_no_fp.png")
    print("\n=== Recommended supplement/transparency figure ===")
    print(out_dir / f"scalp_sens_face_vs_nonface_{args.window}_topomap_clean_panel.png")


if __name__ == "__main__":
    main()
