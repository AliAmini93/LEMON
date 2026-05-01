#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03f_make_publication_erp_figures.py

Publication/report-ready ERP figure patch for the LEMON/MELON Emotional Affect analysis.

Why this patch exists
---------------------
The previous final figures were scientifically correct, but two things can be improved
for reporting:
  1. Add statistical annotations to the most important W4 effects.
  2. Make the W4/W5 subject-level comparison easier to read, especially when one ROI
     contains a large outlier.

This script does not redo preprocessing or ERP extraction. It only uses the existing
summary files.

Recommended run:
    python scripts/03f_make_publication_erp_figures.py --config configs/config.yaml

Expected inputs:
    reports/erp_diff_sens/*_grand_average.csv
    reports/stats_sens/subject_level_window_differences.csv
    reports/stats_sens/subject_level_difference_stats.csv
    reports/stats_sens/w4_w5_interpretation_summary.csv

Outputs:
    reports/final_figures_v2/figure_01_difference_waves_v2.png/.pdf
    reports/final_figures_v2/figure_02_w4_subject_boxplot_compact_v2.png/.pdf
    reports/final_figures_v2/figure_02b_w4_subject_boxplot_all_v2.png/.pdf
    reports/final_figures_v2/figure_03_w4_w5_summary_v2.png/.pdf
    reports/final_figures_v2/figure_04_w4_w5_paired_subjects_compact_v2.png/.pdf
    reports/final_figures_v2/figure_05_w4_minus_w5_boxplot_v2.png/.pdf
    reports/final_figures_v2/publication_figure_stats_summary.csv
    reports/final_figures_v2/publication_w4_w5_paired_stats.csv
    reports/final_figures_v2/README.md

Scientific framing:
    The main effect is Face - Non-face stimulus-locked ERP difference.
    Avoid framing the current result as participant-level emotion recognition.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yaml
except Exception:
    yaml = None

import matplotlib.pyplot as plt

try:
    from scipy import stats
except Exception:
    stats = None


DEFAULT_WINDOWS_MS = {
    "W1": [80, 130],
    "W2": [130, 220],
    "W3": [220, 320],
    "W4": [320, 600],
    "W5": [600, 800],
}

PANEL_DEFS = [
    ("scalp_sens", "late_roi", "Scalp EEG: late ROI"),
    ("scalp_sens", "face_roi", "Scalp EEG: face ROI"),
    ("ear_strict_sens", "ear_strict", "Ear-EEG: strict-ear montage"),
    ("ear_full_sens", "ear_right", "Ear-EEG: right-ear ROI"),
]

COMPACT_EFFECTS = [
    ("scalp_sens", "late_roi", "Scalp\nlate ROI"),
    ("scalp_sens", "face_roi", "Scalp\nface ROI"),
    ("ear_strict_sens", "ear_strict", "Ear\nstrict"),
    ("ear_full_sens", "ear_right", "Ear\nright"),
]

ALL_EFFECTS = [
    ("scalp_sens", "late_roi", "Scalp\nlate ROI"),
    ("scalp_sens", "face_roi", "Scalp\nface ROI"),
    ("scalp_sens", "central_roi", "Scalp\ncentral ROI"),
    ("ear_strict_sens", "ear_strict", "Ear\nstrict"),
    ("ear_full_sens", "ear_right", "Ear\nright"),
    ("ear_full_sens", "ear_full", "Ear\nfull"),
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


def infer_column(df: pd.DataFrame, candidates: Iterable[str], required: bool = True) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in df.columns:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    if required:
        raise ValueError(f"Could not infer column from {list(candidates)}. Available: {list(df.columns)}")
    return None


def read_grand_average(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    time_col = infer_column(df, ["time_ms", "time", "times", "t_ms"])
    mean_col = infer_column(df, ["mean_difference", "grand_mean", "mean", "difference"])
    sem_col = infer_column(df, ["sem", "sem_difference", "sem_average", "grand_sem", "stderr"], required=False)

    out = pd.DataFrame({
        "time_ms": pd.to_numeric(df[time_col], errors="coerce"),
        "mean_difference": pd.to_numeric(df[mean_col], errors="coerce"),
    })
    out["sem"] = pd.to_numeric(df[sem_col], errors="coerce") if sem_col else np.nan
    out = out.dropna(subset=["time_ms", "mean_difference"]).sort_values("time_ms")
    return out


def p_text(p: float) -> str:
    if not np.isfinite(p):
        return "p=n/a"
    if p < 0.001:
        return "p<.001"
    return f"p={p:.3f}".replace("0.", ".")


def dz_text(dz: float) -> str:
    if not np.isfinite(dz):
        return "dz=n/a"
    return f"dz={dz:.2f}"


def get_w4_stats(stats_df: pd.DataFrame, modality: str, roi: str) -> dict:
    sub = stats_df[
        (stats_df["modality"] == modality)
        & (stats_df["roi"] == roi)
        & (stats_df["contrast"] == "face_vs_nonface")
        & (stats_df["window"].astype(str) == "W4")
    ]
    if len(sub) == 0:
        return {}
    return sub.iloc[0].to_dict()


def shade_windows(ax, windows: Dict[str, List[float]]) -> None:
    # Shade W4 and W5. Keep W1-W3 as text labels only.
    y0, y1 = ax.get_ylim()
    if "W4" in windows:
        ax.axvspan(windows["W4"][0], windows["W4"][1], alpha=0.10, zorder=0)
    if "W5" in windows:
        ax.axvspan(windows["W5"][0], windows["W5"][1], alpha=0.05, zorder=0)
    # Add window labels after shading.
    y_text = y0 + 0.93 * (y1 - y0)
    for w, rng in windows.items():
        if w in ["W1", "W2", "W3", "W4", "W5"]:
            ax.text(np.mean(rng), y_text, w, ha="center", va="top", fontsize=8)


def set_panel_label(ax, label: str) -> None:
    ax.text(
        -0.10, 1.08, label,
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        va="top",
        ha="right",
    )


def grand_average_file(diff_dir: Path, modality: str, roi: str) -> Path:
    return diff_dir / f"{modality}_face_vs_nonface_{roi}_grand_average.csv"


def make_figure_01(diff_dir: Path, stats_df: pd.DataFrame, out_dir: Path, windows: Dict[str, List[float]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    axes = axes.flatten()
    panel_letters = ["A", "B", "C", "D"]

    for ax, (modality, roi, title), letter in zip(axes, PANEL_DEFS, panel_letters):
        path = grand_average_file(diff_dir, modality, roi)
        if not path.exists():
            ax.set_title(f"Missing file:\n{path.name}")
            ax.axis("off")
            continue

        df = read_grand_average(path)
        x = df["time_ms"].to_numpy()
        y = df["mean_difference"].to_numpy()
        sem = df["sem"].to_numpy()

        ax.plot(x, y, linewidth=2, label="Face - Non-face")
        if np.isfinite(sem).any():
            ax.fill_between(x, y - sem, y + sem, alpha=0.20, linewidth=0, label="± SEM")

        ax.axhline(0, linestyle="--", linewidth=1)
        ax.axvline(0, linestyle=":", linewidth=1)
        ax.set_xlim(-200, 800)

        st = get_w4_stats(stats_df, modality, roi)
        p = st.get("p_ttest", np.nan)
        dz = st.get("effect_size_dz", np.nan)
        n = st.get("n_subjects", np.nan)
        stat_line = f"W4: {p_text(p)}, {dz_text(dz)}, n={int(n) if np.isfinite(n) else 'n/a'}"

        ax.set_title(f"{title}\n{stat_line}", fontsize=11)
        ax.set_xlabel("Time from stimulus onset (ms)")
        ax.set_ylabel("Difference amplitude")
        shade_windows(ax, windows)
        set_panel_label(ax, letter)
        ax.legend(loc="upper left", fontsize=8, frameon=False)

    fig.suptitle("Face - Non-face ERP difference waves", fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_dir / "figure_01_difference_waves_v2.png", dpi=300)
    fig.savefig(out_dir / "figure_01_difference_waves_v2.pdf")
    plt.close(fig)
    print(f"[OK] Wrote: {out_dir / 'figure_01_difference_waves_v2.png'}")


def make_boxplot(subject_diffs: pd.DataFrame, stats_df: pd.DataFrame, effects: List[Tuple[str, str, str]], out_path_base: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(max(8, len(effects) * 1.45), 5.4))

    values = []
    labels = []
    annotations = []
    for modality, roi, label in effects:
        sub = subject_diffs[
            (subject_diffs["contrast"] == "face_vs_nonface")
            & (subject_diffs["window"].astype(str) == "W4")
            & (subject_diffs["modality"] == modality)
            & (subject_diffs["roi"] == roi)
        ]
        vals = sub["difference"].dropna().to_numpy()
        if len(vals) == 0:
            continue

        values.append(vals)
        labels.append(label)

        st = get_w4_stats(stats_df, modality, roi)
        annotations.append(
            f"{p_text(st.get('p_ttest', np.nan))}\n{dz_text(st.get('effect_size_dz', np.nan))}"
        )

    if not values:
        print(f"[WARN] No data for boxplot: {title}")
        return

    positions = np.arange(1, len(values) + 1)
    ax.boxplot(values, positions=positions, showmeans=True)
    for pos, vals in zip(positions, values):
        jitter = np.linspace(-0.08, 0.08, len(vals)) if len(vals) > 1 else np.array([0.0])
        ax.scatter(np.full(len(vals), pos) + jitter, vals, s=26, alpha=0.75, zorder=3)

    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Subject-level difference")
    ax.set_title(title)

    # Annotation placement.
    all_vals = np.concatenate(values)
    y_min, y_max = np.nanmin(all_vals), np.nanmax(all_vals)
    y_range = y_max - y_min if y_max > y_min else 1
    ax.set_ylim(y_min - 0.12 * y_range, y_max + 0.22 * y_range)
    ann_y = y_max + 0.08 * y_range
    for pos, text in zip(positions, annotations):
        ax.text(pos, ann_y, text, ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path_base.with_suffix(".png"), dpi=300)
    fig.savefig(out_path_base.with_suffix(".pdf"))
    plt.close(fig)
    print(f"[OK] Wrote: {out_path_base.with_suffix('.png')}")


def make_figure_03(w4w5: pd.DataFrame, paired: pd.DataFrame, out_dir: Path) -> None:
    rows = []
    for modality, roi, label in ALL_EFFECTS:
        sub = w4w5[(w4w5["modality"] == modality) & (w4w5["roi"] == roi)]
        if len(sub) == 0:
            continue
        r = sub.iloc[0].to_dict()
        r["label"] = label
        pr = paired[(paired["modality"] == modality) & (paired["roi"] == roi)]
        r["paired_p"] = pr.iloc[0]["p_ttest"] if len(pr) else np.nan
        rows.append(r)

    df = pd.DataFrame(rows)
    if df.empty:
        print("[WARN] No W4/W5 data available for figure 03.")
        return

    x = np.arange(len(df))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.bar(x - width / 2, df["w4_mean_difference"], width, yerr=df.get("w4_sem_average"), capsize=4, label="W4: 320-600 ms")
    ax.bar(x + width / 2, df["w5_mean_difference"], width, yerr=df.get("w5_sem_average"), capsize=4, label="W5: 600-800 ms")
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(df["label"], rotation=25, ha="right")
    ax.set_ylabel("Grand-average difference")
    ax.set_title("Face - Non-face: W4 versus W5")

    # p-value annotations for paired W4-W5 drop.
    y_top = np.nanmax([
        (df["w4_mean_difference"] + df.get("w4_sem_average", 0)).max(),
        (df["w5_mean_difference"] + df.get("w5_sem_average", 0)).max(),
    ])
    y_bottom = np.nanmin([
        (df["w4_mean_difference"] - df.get("w4_sem_average", 0)).min(),
        (df["w5_mean_difference"] - df.get("w5_sem_average", 0)).min(),
    ])
    y_range = y_top - y_bottom if y_top > y_bottom else 1
    ax.set_ylim(y_bottom - 0.10 * y_range, y_top + 0.24 * y_range)

    for i, p in enumerate(df["paired_p"].to_numpy()):
        ax.text(i, y_top + 0.06 * y_range, f"W4-W5\n{p_text(p)}", ha="center", va="bottom", fontsize=8)

    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(out_dir / "figure_03_w4_w5_summary_v2.png", dpi=300)
    fig.savefig(out_dir / "figure_03_w4_w5_summary_v2.pdf")
    plt.close(fig)
    print(f"[OK] Wrote: {out_dir / 'figure_03_w4_w5_summary_v2.png'}")


def paired_stats(subject_diffs: pd.DataFrame, effects: List[Tuple[str, str, str]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    stats_rows = []

    for modality, roi, label in effects:
        sub = subject_diffs[
            (subject_diffs["contrast"] == "face_vs_nonface")
            & (subject_diffs["modality"] == modality)
            & (subject_diffs["roi"] == roi)
            & (subject_diffs["window"].isin(["W4", "W5"]))
        ].copy()

        wide = sub.pivot_table(index="subject_id", columns="window", values="difference", aggfunc="mean")
        if "W4" not in wide.columns or "W5" not in wide.columns:
            continue
        wide = wide.dropna(subset=["W4", "W5"])

        if len(wide) == 0:
            continue

        diff = wide["W4"] - wide["W5"]
        n = len(diff)
        p_t, t_stat, p_w, w_stat, dz = np.nan, np.nan, np.nan, np.nan, np.nan
        if stats is not None and n > 1 and diff.std(ddof=1) > 0:
            tres = stats.ttest_1samp(diff, 0)
            p_t, t_stat = float(tres.pvalue), float(tres.statistic)
            try:
                wres = stats.wilcoxon(diff)
                p_w, w_stat = float(wres.pvalue), float(wres.statistic)
            except Exception:
                pass
            dz = float(diff.mean() / diff.std(ddof=1))

        for sid, r in wide.iterrows():
            rows.append({
                "subject_id": str(sid),
                "modality": modality,
                "roi": roi,
                "label": label,
                "W4": r["W4"],
                "W5": r["W5"],
                "W4_minus_W5": r["W4"] - r["W5"],
            })

        stats_rows.append({
            "modality": modality,
            "roi": roi,
            "label": label,
            "n_subjects": n,
            "mean_w4": float(wide["W4"].mean()),
            "mean_w5": float(wide["W5"].mean()),
            "mean_w4_minus_w5": float(diff.mean()),
            "sem_w4_minus_w5": float(diff.std(ddof=1) / math.sqrt(n)) if n > 1 else np.nan,
            "n_w4_gt_w5": int((diff > 0).sum()),
            "n_w4_lt_w5": int((diff < 0).sum()),
            "positive_pct": float(100 * (diff > 0).sum() / n),
            "t_stat": t_stat,
            "p_ttest": p_t,
            "wilcoxon_stat": w_stat,
            "p_wilcoxon": p_w,
            "effect_size_dz": dz,
        })

    stats_df = pd.DataFrame(stats_rows)
    if len(stats_df):
        stats_df["p_fdr_ttest"] = bh_fdr(stats_df["p_ttest"])
        stats_df["p_fdr_wilcoxon"] = bh_fdr(stats_df["p_wilcoxon"])
    return pd.DataFrame(rows), stats_df


def bh_fdr(pvals: Iterable[float]) -> np.ndarray:
    p = np.asarray(list(pvals), dtype=float)
    out = np.full_like(p, np.nan)
    valid = np.isfinite(p)
    if valid.sum() == 0:
        return out
    pv = p[valid]
    order = np.argsort(pv)
    ranked = pv[order]
    m = len(ranked)
    adj = ranked * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    corrected = np.empty_like(adj)
    corrected[order] = adj
    out[valid] = corrected
    return out


def make_figure_04(paired_df: pd.DataFrame, paired_stats_df: pd.DataFrame, out_dir: Path) -> None:
    effects = COMPACT_EFFECTS
    fig, axes = plt.subplots(1, len(effects), figsize=(12, 4.8), sharey=False)
    if len(effects) == 1:
        axes = [axes]

    for ax, (modality, roi, label) in zip(axes, effects):
        sub = paired_df[(paired_df["modality"] == modality) & (paired_df["roi"] == roi)]
        st = paired_stats_df[(paired_stats_df["modality"] == modality) & (paired_stats_df["roi"] == roi)]
        p = st.iloc[0]["p_ttest"] if len(st) else np.nan

        for _, r in sub.iterrows():
            ax.plot([0, 1], [r["W4"], r["W5"]], marker="o", linewidth=1, alpha=0.55)

        if len(sub) > 0:
            ax.scatter([0], [sub["W4"].mean()], marker="D", s=58, zorder=4)
            ax.scatter([1], [sub["W5"].mean()], marker="D", s=58, zorder=4)

        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["W4", "W5"])
        ax.set_title(f"{label}\nW4-W5 {p_text(p)}", fontsize=10)

    axes[0].set_ylabel("Subject-level difference")
    fig.suptitle("Subject-level W4 to W5 change for Face - Non-face", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(out_dir / "figure_04_w4_w5_paired_subjects_compact_v2.png", dpi=300)
    fig.savefig(out_dir / "figure_04_w4_w5_paired_subjects_compact_v2.pdf")
    plt.close(fig)
    print(f"[OK] Wrote: {out_dir / 'figure_04_w4_w5_paired_subjects_compact_v2.png'}")


def make_figure_05(paired_df: pd.DataFrame, paired_stats_df: pd.DataFrame, out_dir: Path) -> None:
    values = []
    labels = []
    annotations = []
    for modality, roi, label in ALL_EFFECTS:
        vals = paired_df[(paired_df["modality"] == modality) & (paired_df["roi"] == roi)]["W4_minus_W5"].dropna().to_numpy()
        if len(vals) == 0:
            continue
        values.append(vals)
        labels.append(label)
        st = paired_stats_df[(paired_stats_df["modality"] == modality) & (paired_stats_df["roi"] == roi)]
        p = st.iloc[0]["p_ttest"] if len(st) else np.nan
        annotations.append(p_text(p))

    if not values:
        return

    fig, ax = plt.subplots(figsize=(10, 5.4))
    positions = np.arange(1, len(values) + 1)
    ax.boxplot(values, positions=positions, showmeans=True)
    for pos, vals in zip(positions, values):
        jitter = np.linspace(-0.08, 0.08, len(vals)) if len(vals) > 1 else np.array([0.0])
        ax.scatter(np.full(len(vals), pos) + jitter, vals, s=26, alpha=0.75, zorder=3)

    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("W4 - W5 subject-level difference")
    ax.set_title("Face - Non-face: paired W4-minus-W5 difference")

    all_vals = np.concatenate(values)
    y_min, y_max = np.nanmin(all_vals), np.nanmax(all_vals)
    y_range = y_max - y_min if y_max > y_min else 1
    ax.set_ylim(y_min - 0.12 * y_range, y_max + 0.18 * y_range)
    for pos, text in zip(positions, annotations):
        ax.text(pos, y_max + 0.05 * y_range, text, ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_dir / "figure_05_w4_minus_w5_boxplot_v2.png", dpi=300)
    fig.savefig(out_dir / "figure_05_w4_minus_w5_boxplot_v2.pdf")
    plt.close(fig)
    print(f"[OK] Wrote: {out_dir / 'figure_05_w4_minus_w5_boxplot_v2.png'}")


def write_readme(out_dir: Path) -> None:
    text = """# Final ERP Figures v2

Generated by:

```bash
python scripts/03f_make_publication_erp_figures.py --config configs/config.yaml
```

## Main figures

- `figure_01_difference_waves_v2`
  - 2x2 Face - Non-face difference-wave panel with W4 statistics in the panel titles.

- `figure_02_w4_subject_boxplot_compact_v2`
  - Compact subject-level W4 boxplot for the main scalp and ear ROIs.

- `figure_02b_w4_subject_boxplot_all_v2`
  - Full W4 boxplot including central ROI and ear-full ROI.

- `figure_03_w4_w5_summary_v2`
  - W4 versus W5 summary with paired W4-W5 p-value annotations.

- `figure_04_w4_w5_paired_subjects_compact_v2`
  - Subject-level paired W4-to-W5 trajectories for the compact set of key ROIs.

- `figure_05_w4_minus_w5_boxplot_v2`
  - Direct boxplot of subject-level W4-minus-W5 differences.

## Recommended figure set for the report

Use Figures 1, 2 compact, 3, and 5.

Figure 4 is useful for supplementary material because it shows the paired subject
trajectories directly, but it is visually denser.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")
    print(f"[OK] Wrote: {out_dir / 'README.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create patched publication-ready ERP figures.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--diff-dir", default="reports/erp_diff_sens")
    parser.add_argument("--stats-dir", default="reports/stats_sens")
    parser.add_argument("--out-dir", default="reports/final_figures_v2")
    args = parser.parse_args()

    config = load_yaml(Path(args.config))
    root = get_project_root(config)
    windows = get_windows(config)

    diff_dir = Path(args.diff_dir)
    stats_dir = Path(args.stats_dir)
    out_dir = Path(args.out_dir)
    if not diff_dir.is_absolute():
        diff_dir = root / diff_dir
    if not stats_dir.is_absolute():
        stats_dir = root / stats_dir
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    ensure_dir(out_dir)

    subject_diffs_path = stats_dir / "subject_level_window_differences.csv"
    subject_stats_path = stats_dir / "subject_level_difference_stats.csv"
    w4w5_path = stats_dir / "w4_w5_interpretation_summary.csv"

    if not subject_diffs_path.exists():
        raise FileNotFoundError(subject_diffs_path)
    if not subject_stats_path.exists():
        raise FileNotFoundError(subject_stats_path)
    if not w4w5_path.exists():
        raise FileNotFoundError(w4w5_path)

    subject_diffs = pd.read_csv(subject_diffs_path)
    subject_diffs["subject_id"] = subject_diffs["subject_id"].astype(str)
    subject_stats = pd.read_csv(subject_stats_path)
    w4w5 = pd.read_csv(w4w5_path)

    print(f"[INFO] diff_dir: {diff_dir}")
    print(f"[INFO] stats_dir: {stats_dir}")
    print(f"[INFO] out_dir: {out_dir}")

    paired_df, paired_stats_df = paired_stats(subject_diffs, ALL_EFFECTS)
    paired_df.to_csv(out_dir / "publication_w4_w5_paired_subject_values.csv", index=False)
    paired_stats_df.to_csv(out_dir / "publication_w4_w5_paired_stats.csv", index=False)

    make_figure_01(diff_dir, subject_stats, out_dir, windows)

    make_boxplot(
        subject_diffs,
        subject_stats,
        COMPACT_EFFECTS,
        out_dir / "figure_02_w4_subject_boxplot_compact_v2",
        "Subject-level Face - Non-face differences in W4 (compact ROIs)",
    )

    make_boxplot(
        subject_diffs,
        subject_stats,
        ALL_EFFECTS,
        out_dir / "figure_02b_w4_subject_boxplot_all_v2",
        "Subject-level Face - Non-face differences in W4 (all key ROIs)",
    )

    make_figure_03(w4w5, paired_stats_df, out_dir)
    make_figure_04(paired_df, paired_stats_df, out_dir)
    make_figure_05(paired_df, paired_stats_df, out_dir)

    # Compact statistical summary for writing.
    summary_rows = []
    for modality, roi, label in ALL_EFFECTS:
        w4 = subject_stats[
            (subject_stats["modality"] == modality)
            & (subject_stats["roi"] == roi)
            & (subject_stats["contrast"] == "face_vs_nonface")
            & (subject_stats["window"].astype(str) == "W4")
        ]
        w5 = subject_stats[
            (subject_stats["modality"] == modality)
            & (subject_stats["roi"] == roi)
            & (subject_stats["contrast"] == "face_vs_nonface")
            & (subject_stats["window"].astype(str) == "W5")
        ]
        drop = paired_stats_df[(paired_stats_df["modality"] == modality) & (paired_stats_df["roi"] == roi)]
        row = {"label": label, "modality": modality, "roi": roi}
        if len(w4):
            for c in ["n_subjects", "mean_difference", "sem_difference", "effect_size_dz", "p_ttest", "p_fdr_ttest", "p_wilcoxon"]:
                row[f"W4_{c}"] = w4.iloc[0].get(c, np.nan)
        if len(w5):
            for c in ["mean_difference", "sem_difference", "effect_size_dz", "p_ttest", "p_fdr_ttest", "p_wilcoxon"]:
                row[f"W5_{c}"] = w5.iloc[0].get(c, np.nan)
        if len(drop):
            for c in ["mean_w4_minus_w5", "sem_w4_minus_w5", "p_ttest", "p_fdr_ttest", "p_wilcoxon", "effect_size_dz"]:
                row[f"W4minusW5_{c}"] = drop.iloc[0].get(c, np.nan)
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_dir / "publication_figure_stats_summary.csv", index=False)
    print(f"[OK] Wrote: {out_dir / 'publication_figure_stats_summary.csv'}")

    write_readme(out_dir)

    print("\n=== Done. Recommended files for report ===")
    for name in [
        "figure_01_difference_waves_v2.png",
        "figure_02_w4_subject_boxplot_compact_v2.png",
        "figure_03_w4_w5_summary_v2.png",
        "figure_05_w4_minus_w5_boxplot_v2.png",
        "publication_figure_stats_summary.csv",
    ]:
        print(f"  - {out_dir / name}")


if __name__ == "__main__":
    main()
