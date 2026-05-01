from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from scipy import stats

from utils import ensure_dir, load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ERP statistics on extracted window amplitudes.")
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--input", type=str, default="reports/tables/window_amplitudes.csv")
    return parser.parse_args()


def cohens_d_paired(x: np.ndarray, y: np.ndarray) -> float:
    diff = x - y
    sd = diff.std(ddof=1)
    if sd == 0:
        return np.nan
    return float(diff.mean() / sd)


def fdr_bh(pvals: List[float]) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty_like(adj)
    out[order] = adj
    return out


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Required ERP window table not found: {input_path}\n\n"
            "This file is created by step 03. Please run the previous steps first:\n"
            "  python scripts/02_preprocess_epoch.py --config configs/config.yaml --subjects 200 201 202\n"
            "  python scripts/03_erp_analysis.py --config configs/config.yaml --subjects 200 201 202\n\n"
            "Then rerun statistics:\n"
            "  python scripts/04_statistics.py --config configs/config.yaml"
        )
    df = pd.read_csv(input_path)

    stats_dir = ensure_dir(Path("reports") / "stats")
    results = []

    # Condition comparisons within modality/ROI/window
    group_cols = ["modality", "contrast", "roi", "window"]
    for keys, sub in df.groupby(group_cols):
        modality, contrast, roi, window = keys
        conds = sub["condition"].unique().tolist()
        if len(conds) != 2:
            continue
        subjects = sorted(set(sub["subject_id"]))
        pivot = sub.pivot_table(index="subject_id", columns="condition", values="mean_amplitude", aggfunc="mean")
        if pivot.shape[1] != 2:
            continue
        a, b = pivot.columns.tolist()
        x = pivot[a].to_numpy(dtype=float)
        y = pivot[b].to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]
        if len(x) < 3:
            continue
        if cfg["stats"]["test"].lower() == "ttest":
            stat, p = stats.ttest_rel(x, y, nan_policy="omit")
            test_name = "paired_ttest"
        else:
            stat, p = stats.wilcoxon(x, y, zero_method="wilcox", correction=False)
            test_name = "wilcoxon"
        results.append({
            "analysis": "condition_within_modality",
            "modality": modality,
            "contrast": contrast,
            "roi": roi,
            "window": window,
            "condition_a": a,
            "condition_b": b,
            "n": len(x),
            "mean_a": float(np.mean(x)),
            "mean_b": float(np.mean(y)),
            "mean_diff": float(np.mean(x - y)),
            "test": test_name,
            "statistic": float(stat),
            "p_value": float(p),
            "effect_size_dz": cohens_d_paired(x, y),
        })

    # Ear vs scalp effect-size comparisons
    # First compute per-subject effect scores from contrasts.
    pivot = df.pivot_table(
        index=["subject_id", "modality", "contrast", "roi", "window"],
        columns="condition",
        values="mean_amplitude",
        aggfunc="mean",
    ).reset_index()
    for contrast in pivot["contrast"].unique():
        subc = pivot[pivot["contrast"] == contrast].copy()
        cond_cols = [c for c in subc.columns if c not in {"subject_id", "modality", "contrast", "roi", "window"}]
        if len(cond_cols) != 2:
            continue
        a, b = cond_cols
        subc["effect_score"] = subc[a] - subc[b]
        scalp = subc[subc["modality"] == "scalp_main"]
        for ear_mod in ["ear_full_main", "ear_strict_main"]:
            ear = subc[subc["modality"] == ear_mod]
            merged = pd.merge(
                scalp[["subject_id", "roi", "window", "effect_score"]].rename(columns={"effect_score": "scalp_effect"}),
                ear[["subject_id", "roi", "window", "effect_score"]].rename(columns={"effect_score": "ear_effect"}),
                on=["subject_id", "roi", "window"],
                how="inner",
            )
            for (roi, window), grp in merged.groupby(["roi", "window"]):
                x = grp["scalp_effect"].to_numpy(dtype=float)
                y = grp["ear_effect"].to_numpy(dtype=float)
                mask = np.isfinite(x) & np.isfinite(y)
                x = x[mask]
                y = y[mask]
                if len(x) < 3:
                    continue
                if cfg["stats"]["test"].lower() == "ttest":
                    stat, p = stats.ttest_rel(x, y, nan_policy="omit")
                    test_name = "paired_ttest"
                else:
                    stat, p = stats.wilcoxon(x, y, zero_method="wilcox", correction=False)
                    test_name = "wilcoxon"
                results.append({
                    "analysis": "modality_effect_comparison",
                    "modality": f"scalp_main_vs_{ear_mod}",
                    "contrast": contrast,
                    "roi": roi,
                    "window": window,
                    "condition_a": "scalp_effect",
                    "condition_b": "ear_effect",
                    "n": len(x),
                    "mean_a": float(np.mean(x)),
                    "mean_b": float(np.mean(y)),
                    "mean_diff": float(np.mean(x - y)),
                    "test": test_name,
                    "statistic": float(stat),
                    "p_value": float(p),
                    "effect_size_dz": cohens_d_paired(x, y),
                })

    res = pd.DataFrame(results)
    if len(res) == 0:
        raise RuntimeError("No statistical results could be computed. Check inputs and contrasts.")

    res["p_fdr"] = fdr_bh(res["p_value"].tolist())
    out_path = stats_dir / "erp_stats_results.csv"
    res.to_csv(out_path, index=False)
    print(f"[OK] Wrote statistics table: {out_path}")


if __name__ == "__main__":
    main()
