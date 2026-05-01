#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03d_subject_level_difference_stats.py

Subject-level ERP difference statistics for the LEMON/MELON Emotional Affect analysis.

This script converts condition-level ERP window amplitudes into subject-level
difference scores and then performs group-level tests against zero.

Main use:
    python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml

Inputs expected by default:
    reports/tables/window_amplitudes.csv
    reports/tables/condition_counts.csv                         optional but recommended
    reports/erp_diff_sens/difference_window_summary_w5.csv       optional, for W4/W5 descriptive interpretation

Main outputs:
    reports/stats/subject_level_window_differences.csv
    reports/stats/subject_level_difference_stats.csv
    reports/stats/subject_level_difference_stats_key_results.csv
    reports/stats/w4_w5_interpretation_summary.csv               if W4/W5 summary exists
    reports/figures/subject_level_face_nonface_w4.png            if matplotlib is available
    reports/figures/w4_w5_interpretation_summary.png             if W4/W5 summary exists

Important:
    - The subject-level inferential statistics are computed from
      reports/tables/window_amplitudes.csv.
    - If that table only contains main epochs, then W1-W4 are tested.
    - W5 is summarized from reports/erp_diff_sens/difference_window_summary_w5.csv
      as descriptive W4/W5 interpretation unless W5 is also present in
      window_amplitudes.csv.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yaml
except Exception:
    yaml = None

try:
    from scipy import stats
except Exception as exc:
    raise RuntimeError("scipy is required for statistical tests. Please install scipy.") from exc


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


def bh_fdr(pvals: Iterable[float]) -> np.ndarray:
    """
    Benjamini-Hochberg FDR correction.
    NaN p-values remain NaN.
    """
    p = np.asarray(list(pvals), dtype=float)
    out = np.full_like(p, np.nan, dtype=float)

    valid = np.isfinite(p)
    if valid.sum() == 0:
        return out

    pv = p[valid]
    order = np.argsort(pv)
    ranked = pv[order]
    m = len(ranked)

    adj = ranked * m / (np.arange(1, m + 1))
    # Enforce monotonicity from largest to smallest
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)

    corrected = np.empty_like(adj)
    corrected[order] = adj
    out[valid] = corrected
    return out


def safe_ttest_1samp(x: np.ndarray) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
    if np.nanstd(x, ddof=1) == 0:
        return np.nan, np.nan
    res = stats.ttest_1samp(x, popmean=0.0, nan_policy="omit")
    return float(res.statistic), float(res.pvalue)


def safe_wilcoxon(x: np.ndarray) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 1:
        return np.nan, np.nan
    # Wilcoxon fails when all differences are exactly zero
    if np.allclose(x, 0):
        return np.nan, np.nan
    try:
        res = stats.wilcoxon(x, zero_method="wilcox", alternative="two-sided")
        return float(res.statistic), float(res.pvalue)
    except Exception:
        return np.nan, np.nan


def safe_sign_test(x: np.ndarray) -> Tuple[int, int, float]:
    """
    Two-sided binomial sign test excluding zeros.

    Returns:
        n_positive, n_negative, p_value
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n_pos = int(np.sum(x > 0))
    n_neg = int(np.sum(x < 0))
    n = n_pos + n_neg
    if n == 0:
        return n_pos, n_neg, np.nan
    k = min(n_pos, n_neg)
    try:
        p = stats.binomtest(k, n=n, p=0.5, alternative="two-sided").pvalue
    except AttributeError:
        p = stats.binom_test(k, n=n, p=0.5, alternative="two-sided")
    return n_pos, n_neg, float(p)


def ci95_t(x: np.ndarray) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 2:
        return np.nan, np.nan
    sem = np.nanstd(x, ddof=1) / math.sqrt(n)
    if not np.isfinite(sem):
        return np.nan, np.nan
    tcrit = stats.t.ppf(0.975, df=n - 1)
    mean = np.nanmean(x)
    return float(mean - tcrit * sem), float(mean + tcrit * sem)


def cohen_dz(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan
    sd = np.nanstd(x, ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return np.nan
    return float(np.nanmean(x) / sd)


def get_window_order(config: dict) -> Dict[str, int]:
    windows = (
        config.get("erp_windows_ms")
        or config.get("erp_windows")
        or config.get("windows")
        or {}
    )
    if isinstance(windows, dict):
        return {str(k): i for i, k in enumerate(windows.keys())}
    return {"W1": 0, "W2": 1, "W3": 2, "W4": 3, "W5": 4}


def sort_windows(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    order = get_window_order(config)
    if "window" in df.columns:
        df = df.copy()
        df["_window_order"] = df["window"].map(order).fillna(999).astype(int)
        sort_cols = [c for c in ["modality", "contrast", "roi", "_window_order", "window"] if c in df.columns]
        df = df.sort_values(sort_cols).drop(columns=["_window_order"])
    return df


# ---------------------------------------------------------------------
# Subject-level differences from window_amplitudes.csv
# ---------------------------------------------------------------------

def compute_subject_differences(
    window_table: Path,
    condition_counts: Optional[Path] = None,
) -> pd.DataFrame:
    if not window_table.exists():
        raise FileNotFoundError(f"Window table not found: {window_table}")

    df = pd.read_csv(window_table)

    required = {
        "subject_id",
        "modality",
        "contrast",
        "condition",
        "roi",
        "window",
        "start_ms",
        "end_ms",
        "mean_amplitude",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {window_table}: {sorted(missing)}")

    df = df.copy()
    df["subject_id"] = df["subject_id"].astype(str)
    df["condition"] = df["condition"].astype(str)

    idx_cols = ["subject_id", "modality", "contrast", "roi", "window", "start_ms", "end_ms"]
    wide = (
        df.pivot_table(
            index=idx_cols,
            columns="condition",
            values="mean_amplitude",
            aggfunc="mean",
        )
        .reset_index()
    )

    rows = []
    for _, r in wide.iterrows():
        contrast = r["contrast"]

        if contrast == "face_vs_nonface":
            cond_a, cond_b = "face", "non_face"
        elif contrast == "emotional_vs_neutral":
            cond_a, cond_b = "emotional", "neutral"
        else:
            # Unknown contrast; skip safely.
            continue

        if cond_a not in wide.columns or cond_b not in wide.columns:
            continue

        a_val = r.get(cond_a, np.nan)
        b_val = r.get(cond_b, np.nan)
        if not (np.isfinite(a_val) and np.isfinite(b_val)):
            continue

        rows.append({
            "subject_id": r["subject_id"],
            "modality": r["modality"],
            "contrast": contrast,
            "condition_a": cond_a,
            "condition_b": cond_b,
            "roi": r["roi"],
            "window": r["window"],
            "start_ms": r["start_ms"],
            "end_ms": r["end_ms"],
            "mean_a": float(a_val),
            "mean_b": float(b_val),
            "difference": float(a_val - b_val),
        })

    out = pd.DataFrame(rows)

    # Add counts if available.
    if condition_counts is not None and condition_counts.exists() and len(out) > 0:
        cc = pd.read_csv(condition_counts)
        needed = {"subject_id", "modality", "contrast", "condition", "n_epochs"}
        if needed.issubset(cc.columns):
            cc = cc.copy()
            cc["subject_id"] = cc["subject_id"].astype(str)
            cc["condition"] = cc["condition"].astype(str)

            cc_wide = (
                cc.pivot_table(
                    index=["subject_id", "modality", "contrast"],
                    columns="condition",
                    values="n_epochs",
                    aggfunc="sum",
                )
                .reset_index()
            )

            out = out.merge(cc_wide, on=["subject_id", "modality", "contrast"], how="left")

            def get_count(row, cond):
                return row.get(cond, np.nan)

            out["n_a"] = [get_count(row, row["condition_a"]) for _, row in out.iterrows()]
            out["n_b"] = [get_count(row, row["condition_b"]) for _, row in out.iterrows()]

            # Avoid carrying condition count columns into the final output.
            drop_cols = [c for c in ["face", "non_face", "emotional", "neutral"] if c in out.columns]
            out = out.drop(columns=drop_cols)

    if "n_a" not in out.columns:
        out["n_a"] = np.nan
    if "n_b" not in out.columns:
        out["n_b"] = np.nan

    return out


def compute_group_stats(subject_diffs: pd.DataFrame) -> pd.DataFrame:
    rows = []

    group_cols = ["modality", "contrast", "roi", "window", "start_ms", "end_ms"]
    for keys, g in subject_diffs.groupby(group_cols, dropna=False):
        modality, contrast, roi, window, start_ms, end_ms = keys
        x = g["difference"].to_numpy(dtype=float)
        x = x[np.isfinite(x)]

        n = len(x)
        mean = float(np.nanmean(x)) if n > 0 else np.nan
        median = float(np.nanmedian(x)) if n > 0 else np.nan
        std = float(np.nanstd(x, ddof=1)) if n > 1 else np.nan
        sem = float(std / math.sqrt(n)) if n > 1 and np.isfinite(std) else np.nan
        t_stat, p_t = safe_ttest_1samp(x)
        w_stat, p_w = safe_wilcoxon(x)
        n_pos, n_neg, p_sign = safe_sign_test(x)
        ci_low, ci_high = ci95_t(x)
        dz = cohen_dz(x)

        rows.append({
            "modality": modality,
            "contrast": contrast,
            "roi": roi,
            "window": window,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "n_subjects": n,
            "mean_difference": mean,
            "median_difference": median,
            "std_difference": std,
            "sem_difference": sem,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
            "n_positive": n_pos,
            "n_negative": n_neg,
            "positive_pct": float(100 * n_pos / n) if n > 0 else np.nan,
            "t_stat": t_stat,
            "p_ttest": p_t,
            "wilcoxon_stat": w_stat,
            "p_wilcoxon": p_w,
            "p_sign": p_sign,
            "effect_size_dz": dz,
        })

    stats_df = pd.DataFrame(rows)
    if len(stats_df) > 0:
        stats_df["p_fdr_ttest"] = bh_fdr(stats_df["p_ttest"].to_numpy())
        stats_df["p_fdr_wilcoxon"] = bh_fdr(stats_df["p_wilcoxon"].to_numpy())
    return stats_df


# ---------------------------------------------------------------------
# W4/W5 descriptive interpretation from difference_window_summary_w5.csv
# ---------------------------------------------------------------------

def make_w4_w5_summary(w5_summary: Path) -> Optional[pd.DataFrame]:
    if not w5_summary.exists():
        return None

    df = pd.read_csv(w5_summary)
    required = {"modality", "contrast", "roi", "window", "mean_difference", "sem_average", "abs_peak", "abs_peak_time_ms"}
    if not required.issubset(df.columns):
        return None

    df = df[(df["contrast"] == "face_vs_nonface") & (df["window"].isin(["W4", "W5"]))].copy()
    if df.empty:
        return None

    # Keep the most relevant ROIs but do not hard-fail if extra ROIs exist.
    key_pairs = {
        ("scalp_sens", "face_roi"),
        ("scalp_sens", "late_roi"),
        ("scalp_sens", "central_roi"),
        ("ear_strict_sens", "ear_strict"),
        ("ear_full_sens", "ear_right"),
        ("ear_full_sens", "ear_full"),
    }
    df_key = df[df[["modality", "roi"]].apply(tuple, axis=1).isin(key_pairs)].copy()
    if df_key.empty:
        df_key = df.copy()

    wide_mean = df_key.pivot_table(index=["modality", "roi"], columns="window", values="mean_difference", aggfunc="first")
    wide_sem = df_key.pivot_table(index=["modality", "roi"], columns="window", values="sem_average", aggfunc="first")
    wide_peak = df_key.pivot_table(index=["modality", "roi"], columns="window", values="abs_peak", aggfunc="first")
    wide_peak_t = df_key.pivot_table(index=["modality", "roi"], columns="window", values="abs_peak_time_ms", aggfunc="first")

    rows = []
    for idx in wide_mean.index:
        modality, roi = idx
        w4 = wide_mean.loc[idx].get("W4", np.nan)
        w5 = wide_mean.loc[idx].get("W5", np.nan)
        w4_sem = wide_sem.loc[idx].get("W4", np.nan) if idx in wide_sem.index else np.nan
        w5_sem = wide_sem.loc[idx].get("W5", np.nan) if idx in wide_sem.index else np.nan
        w4_peak = wide_peak.loc[idx].get("W4", np.nan) if idx in wide_peak.index else np.nan
        w5_peak = wide_peak.loc[idx].get("W5", np.nan) if idx in wide_peak.index else np.nan
        w4_peak_t = wide_peak_t.loc[idx].get("W4", np.nan) if idx in wide_peak_t.index else np.nan
        w5_peak_t = wide_peak_t.loc[idx].get("W5", np.nan) if idx in wide_peak_t.index else np.nan

        drop = w5 - w4 if np.isfinite(w4) and np.isfinite(w5) else np.nan
        drop_pct = (100 * (w4 - w5) / abs(w4)) if np.isfinite(w4) and abs(w4) > 1e-12 and np.isfinite(w5) else np.nan

        if np.isfinite(drop_pct):
            if drop_pct > 50:
                interp = "clear post-W4 decrease"
            elif drop_pct > 20:
                interp = "moderate post-W4 decrease"
            elif drop_pct > 0:
                interp = "small post-W4 decrease"
            else:
                interp = "no decrease or increase"
        else:
            interp = "insufficient data"

        rows.append({
            "modality": modality,
            "roi": roi,
            "contrast": "face_vs_nonface",
            "w4_mean_difference": w4,
            "w4_sem_average": w4_sem,
            "w5_mean_difference": w5,
            "w5_sem_average": w5_sem,
            "w5_minus_w4": drop,
            "post_w4_decrease_pct": drop_pct,
            "w4_abs_peak": w4_peak,
            "w4_abs_peak_time_ms": w4_peak_t,
            "w5_abs_peak": w5_peak,
            "w5_abs_peak_time_ms": w5_peak_t,
            "interpretation": interp,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------

def make_plots(
    subject_diffs: pd.DataFrame,
    stats_df: pd.DataFrame,
    w4w5_df: Optional[pd.DataFrame],
    fig_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("[WARN] matplotlib is not available; skipping figures.")
        return

    ensure_dir(fig_dir)

    # Plot 1: subject-level W4 distributions for key Face--Non-face effects.
    key = subject_diffs[
        (subject_diffs["contrast"] == "face_vs_nonface")
        & (subject_diffs["window"] == "W4")
        & (
            ((subject_diffs["modality"].isin(["scalp_main", "scalp_sens"])) & subject_diffs["roi"].isin(["face_roi", "late_roi", "central_roi"]))
            | ((subject_diffs["modality"].isin(["ear_full_main", "ear_full_sens"])) & subject_diffs["roi"].isin(["ear_right", "ear_full"]))
            | ((subject_diffs["modality"].isin(["ear_strict_main", "ear_strict_sens"])) & subject_diffs["roi"].isin(["ear_strict"]))
        )
    ].copy()

    if len(key) > 0:
        key["label"] = key["modality"] + "\n" + key["roi"]
        labels = list(dict.fromkeys(key["label"].tolist()))

        fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.25), 5))
        data = [key.loc[key["label"] == lab, "difference"].dropna().to_numpy() for lab in labels]
        ax.boxplot(data, labels=labels, showmeans=True)
        for i, vals in enumerate(data, start=1):
            if len(vals) == 0:
                continue
            # Deterministic small jitter
            jitter = np.linspace(-0.08, 0.08, len(vals)) if len(vals) > 1 else np.array([0.0])
            ax.scatter(np.full(len(vals), i) + jitter, vals, s=18, alpha=0.75)
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_ylabel("Subject-level difference (condition A - condition B)")
        ax.set_title("Subject-level Face - Non-face differences in W4")
        ax.tick_params(axis="x", labelrotation=35)
        fig.tight_layout()
        out = fig_dir / "subject_level_face_nonface_w4.png"
        fig.savefig(out, dpi=200)
        plt.close(fig)
        print(f"[OK] Wrote figure: {out}")

    # Plot 2: W4 vs W5 descriptive summary.
    if w4w5_df is not None and len(w4w5_df) > 0:
        plot_df = w4w5_df.copy()
        plot_df["label"] = plot_df["modality"] + "\n" + plot_df["roi"]

        x = np.arange(len(plot_df))
        width = 0.36

        fig, ax = plt.subplots(figsize=(max(8, len(plot_df) * 1.25), 5))
        ax.bar(x - width / 2, plot_df["w4_mean_difference"], width, yerr=plot_df["w4_sem_average"], capsize=3, label="W4: 320-600 ms")
        ax.bar(x + width / 2, plot_df["w5_mean_difference"], width, yerr=plot_df["w5_sem_average"], capsize=3, label="W5: 600-800 ms")
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(plot_df["label"], rotation=35, ha="right")
        ax.set_ylabel("Grand-average difference")
        ax.set_title("Face - Non-face: W4 versus W5 descriptive summary")
        ax.legend()
        fig.tight_layout()
        out = fig_dir / "w4_w5_interpretation_summary.png"
        fig.savefig(out, dpi=200)
        plt.close(fig)
        print(f"[OK] Wrote figure: {out}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute subject-level ERP difference statistics and W4/W5 interpretation summaries."
    )
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--window-table", default="reports/tables/window_amplitudes.csv", help="Input window amplitudes CSV")
    parser.add_argument("--condition-counts", default="reports/tables/condition_counts.csv", help="Input condition counts CSV")
    parser.add_argument("--w5-summary", default="reports/erp_diff_sens/difference_window_summary_w5.csv", help="Input W4/W5 summary CSV")
    parser.add_argument("--out-dir", default="reports/stats", help="Output directory for stats CSVs")
    parser.add_argument("--fig-dir", default="reports/figures", help="Output directory for figures")
    parser.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_yaml(config_path)

    window_table = Path(args.window_table)
    condition_counts = Path(args.condition_counts)
    w5_summary = Path(args.w5_summary)
    out_dir = Path(args.out_dir)
    fig_dir = Path(args.fig_dir)
    ensure_dir(out_dir)
    ensure_dir(fig_dir)

    # 1) Subject-level differences.
    subject_diffs = compute_subject_differences(
        window_table=window_table,
        condition_counts=condition_counts if condition_counts.exists() else None,
    )
    subject_diffs = sort_windows(subject_diffs, config)

    out_subject = out_dir / "subject_level_window_differences.csv"
    subject_diffs.to_csv(out_subject, index=False)
    print(f"[OK] Wrote subject-level differences: {out_subject}")

    # 2) Group stats.
    stats_df = compute_group_stats(subject_diffs)
    stats_df = sort_windows(stats_df, config)

    out_stats = out_dir / "subject_level_difference_stats.csv"
    stats_df.to_csv(out_stats, index=False)
    print(f"[OK] Wrote subject-level stats: {out_stats}")

    # 3) Key results table.
    key_stats = stats_df[
        (stats_df["contrast"] == "face_vs_nonface")
        & (stats_df["window"].isin(["W1", "W4", "W5"]))
        & (
            ((stats_df["modality"].isin(["scalp_main", "scalp_sens"])) & stats_df["roi"].isin(["face_roi", "late_roi", "central_roi"]))
            | ((stats_df["modality"].isin(["ear_full_main", "ear_full_sens"])) & stats_df["roi"].isin(["ear_right", "ear_full"]))
            | ((stats_df["modality"].isin(["ear_strict_main", "ear_strict_sens"])) & stats_df["roi"].isin(["ear_strict"]))
        )
    ].copy()
    key_stats = key_stats.sort_values(["contrast", "modality", "roi", "window"])
    out_key = out_dir / "subject_level_difference_stats_key_results.csv"
    key_stats.to_csv(out_key, index=False)
    print(f"[OK] Wrote key subject-level stats: {out_key}")

    # 4) W4/W5 descriptive interpretation.
    w4w5_df = make_w4_w5_summary(w5_summary)
    if w4w5_df is not None:
        out_w4w5 = out_dir / "w4_w5_interpretation_summary.csv"
        w4w5_df.to_csv(out_w4w5, index=False)
        print(f"[OK] Wrote W4/W5 interpretation summary: {out_w4w5}")
    else:
        print(f"[WARN] W4/W5 summary not available or invalid: {w5_summary}")
        w4w5_df = None

    # 5) Figures.
    if not args.no_plots:
        make_plots(subject_diffs, stats_df, w4w5_df, fig_dir)

    # 6) Console summary.
    print("\n=== Quick summary: strongest subject-level trends by |effect_size_dz| ===")
    if len(stats_df) > 0:
        show = stats_df.copy()
        show["abs_dz"] = show["effect_size_dz"].abs()
        show = show.sort_values("abs_dz", ascending=False).head(12)
        cols = [
            "modality",
            "contrast",
            "roi",
            "window",
            "n_subjects",
            "mean_difference",
            "sem_difference",
            "effect_size_dz",
            "p_ttest",
            "p_fdr_ttest",
            "p_wilcoxon",
            "p_fdr_wilcoxon",
            "positive_pct",
        ]
        cols = [c for c in cols if c in show.columns]
        with pd.option_context("display.max_columns", None, "display.width", 180):
            print(show[cols].to_string(index=False))
    else:
        print("[WARN] No stats rows generated.")

    if w4w5_df is not None:
        print("\n=== W4/W5 descriptive interpretation ===")
        cols = [
            "modality",
            "roi",
            "w4_mean_difference",
            "w5_mean_difference",
            "post_w4_decrease_pct",
            "interpretation",
        ]
        with pd.option_context("display.max_columns", None, "display.width", 160):
            print(w4w5_df[cols].to_string(index=False))

    # 7) Note about W5 inference.
    if "W5" not in set(subject_diffs["window"].astype(str)):
        print(
            "\n[NOTE] W5 was not found in reports/tables/window_amplitudes.csv. "
            "Therefore W5 is summarized descriptively from the sensitivity grand-average table, "
            "but not tested at subject level by this run. If you need subject-level W5 tests, "
            "rerun ERP window extraction on sensitivity epochs or extend 03_erp_analysis.py to include sens modalities."
        )


if __name__ == "__main__":
    main()
