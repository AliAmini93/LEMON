from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd

from utils import ensure_dir, load_config, output_root

mne.set_log_level("WARNING")


CONTRASTS = {
    "face_vs_nonface": {
        "a": lambda md: md["type"].eq("face"),
        "b": lambda md: md["type"].eq("non_face"),
        "a_name": "face",
        "b_name": "non_face",
    },
    "emotional_vs_neutral": {
        "a": lambda md: md["expression"].isin(["happy", "angry", "afraid"]),
        "b": lambda md: md["expression"].eq("neutral"),
        "a_name": "emotional",
        "b_name": "neutral",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grand-average ERP and window amplitude extraction with QC-aware skipping.")
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--subjects", nargs="*", default=None)
    return parser.parse_args()


def resolve_subjects(cfg: dict, args: argparse.Namespace) -> List[str]:
    if args.subjects:
        return [s.replace("sub-", "") for s in args.subjects]
    return cfg["main_subjects"]


def epoch_path(cfg: dict, sid: str, modality_key: str) -> Path:
    return output_root(cfg) / "processed" / f"sub-{sid}" / f"{modality_key}-epo.fif"


def load_epochs(cfg: dict, sid: str, modality_key: str) -> mne.Epochs | None:
    p = epoch_path(cfg, sid, modality_key)
    if not p.exists():
        return None
    return mne.read_epochs(p, preload=True, verbose="ERROR")


def get_rois(cfg: dict, epochs: mne.Epochs, modality_key: str) -> Dict[str, List[str]]:
    if modality_key.startswith("scalp"):
        rois = {
            "face_roi": cfg["scalp"]["face_roi"],
            "late_roi": cfg["scalp"]["late_roi"],
            "central_roi": cfg["scalp"]["central_roi"],
        }
    elif modality_key.startswith("ear_full"):
        rois = {
            "ear_left": cfg["ear"]["left_roi"],
            "ear_right": cfg["ear"]["right_roi"],
            "ear_mastoid": cfg["ear"]["mastoid_roi"],
            "ear_full": cfg["ear"]["full_channels"],
        }
    else:
        strict_full = [ch for ch in cfg["ear"]["full_channels"] if ch not in cfg["ear"]["strict_drop_channels"]]
        rois = {
            "ear_left": cfg["ear"]["left_roi"],
            "ear_right": cfg["ear"]["right_roi"],
            "ear_mastoid": cfg["ear"]["mastoid_roi"],
            "ear_strict": strict_full,
        }
    out = {}
    for name, desired in rois.items():
        present = [ch for ch in desired if ch in epochs.ch_names]
        if present:
            out[name] = present
    return out


def channels_with_finite_data(epochs: mne.Epochs, picks: List[str]) -> tuple[List[str], List[str]]:
    if not picks:
        return [], []
    ep = epochs.copy().pick(picks)
    data = ep.get_data()
    usable = []
    dropped = []
    for ci, ch in enumerate(ep.ch_names):
        ch_data = data[:, ci, :]
        if np.isfinite(ch_data).any():
            usable.append(ch)
        else:
            dropped.append(ch)
    return usable, dropped


def average_condition(epochs: mne.Epochs, mask: pd.Series, picks: List[str]) -> np.ndarray:
    picks, _ = channels_with_finite_data(epochs, picks)
    if not picks:
        return np.full(len(epochs.times), np.nan)
    sub_epochs = epochs[mask.to_numpy()]
    if len(sub_epochs) == 0:
        return np.full(len(epochs.times), np.nan)
    data = sub_epochs.copy().pick(picks).get_data()
    return np.nanmean(data, axis=(0, 1))


def window_mean(times: np.ndarray, waveform: np.ndarray, start_ms: int, end_ms: int) -> float:
    start_s = start_ms / 1000.0
    end_s = end_ms / 1000.0
    mask = (times >= start_s) & (times < end_s)
    if not np.any(mask) or not np.isfinite(waveform[mask]).any():
        return np.nan
    return float(np.nanmean(waveform[mask]))


def plot_group_waveforms(times: np.ndarray, wf_a: np.ndarray, wf_b: np.ndarray, label_a: str, label_b: str, title: str, out_path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.plot(times * 1000, wf_a, label=label_a, linewidth=2)
    plt.plot(times * 1000, wf_b, label=label_b, linewidth=2)
    plt.axvline(0, color="black", linestyle="--", linewidth=1)
    plt.axhline(0, color="gray", linestyle=":", linewidth=1)
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    subjects = resolve_subjects(cfg, args)

    erp_dir = ensure_dir(Path("reports") / "erp")
    tables_dir = ensure_dir(Path("reports") / "tables")

    modality_keys = ["scalp_main", "ear_full_main", "ear_strict_main"]
    records = []
    condition_count_rows = []
    roi_usage_rows = []
    channel_nan_rows = []
    skipped_rows = []

    for modality_key in modality_keys:
        all_subject_waveforms = {}
        times_ref = None
        for contrast_name, contrast in CONTRASTS.items():
            all_subject_waveforms[contrast_name] = {contrast["a_name"]: {}, contrast["b_name"]: {}}

        for sid in subjects:
            epochs = load_epochs(cfg, sid, modality_key)
            if epochs is None:
                skipped_rows.append({"subject_id": sid, "modality": modality_key, "reason": "missing_epoch_file"})
                continue
            times_ref = epochs.times
            md = epochs.metadata.reset_index(drop=True)
            rois = get_rois(cfg, epochs, modality_key)

            # Channel NaN report for all channels in this modality.
            data_all = epochs.get_data()
            for ci, ch in enumerate(epochs.ch_names):
                ch_data = data_all[:, ci, :]
                channel_nan_rows.append({
                    "subject_id": sid,
                    "modality": modality_key,
                    "channel": ch,
                    "nan_pct": float(100 * np.isnan(ch_data).mean()),
                    "all_nan": bool(not np.isfinite(ch_data).any()),
                })

            for roi_name, roi_picks in rois.items():
                usable, dropped_all_nan = channels_with_finite_data(epochs, roi_picks)
                roi_usage_rows.append({
                    "subject_id": sid,
                    "modality": modality_key,
                    "roi": roi_name,
                    "requested_channels": ";".join(roi_picks),
                    "used_channels": ";".join(usable),
                    "dropped_all_nan_channels": ";".join(dropped_all_nan),
                    "n_used_channels": len(usable),
                })

            for contrast_name, contrast in CONTRASTS.items():
                mask_a = contrast["a"](md)
                mask_b = contrast["b"](md)
                condition_count_rows.append({"subject_id": sid, "modality": modality_key, "contrast": contrast_name, "condition": contrast["a_name"], "n_epochs": int(mask_a.sum())})
                condition_count_rows.append({"subject_id": sid, "modality": modality_key, "contrast": contrast_name, "condition": contrast["b_name"], "n_epochs": int(mask_b.sum())})
                for roi_name, roi_picks in rois.items():
                    usable_picks, _ = channels_with_finite_data(epochs, roi_picks)
                    if not usable_picks:
                        continue
                    wf_a = average_condition(epochs, mask_a, usable_picks)
                    wf_b = average_condition(epochs, mask_b, usable_picks)
                    all_subject_waveforms[contrast_name][contrast["a_name"]].setdefault(roi_name, []).append(wf_a)
                    all_subject_waveforms[contrast_name][contrast["b_name"]].setdefault(roi_name, []).append(wf_b)
                    for cond_name, waveform in [(contrast["a_name"], wf_a), (contrast["b_name"], wf_b)]:
                        for win_name, (start_ms, end_ms) in cfg["erp_windows_ms"].items():
                            records.append({
                                "subject_id": sid,
                                "modality": modality_key,
                                "contrast": contrast_name,
                                "condition": cond_name,
                                "roi": roi_name,
                                "window": win_name,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                                "mean_amplitude": window_mean(times_ref, waveform, start_ms, end_ms),
                            })

        # Plot group means per ROI and contrast.
        if times_ref is not None:
            for contrast_name, contrast in CONTRASTS.items():
                for roi_name in all_subject_waveforms[contrast_name][contrast["a_name"]].keys():
                    arr_a = np.stack(all_subject_waveforms[contrast_name][contrast["a_name"]][roi_name])
                    arr_b = np.stack(all_subject_waveforms[contrast_name][contrast["b_name"]][roi_name])
                    wf_a = np.nanmean(arr_a, axis=0)
                    wf_b = np.nanmean(arr_b, axis=0)
                    title = f"{modality_key} | {contrast_name} | {roi_name}"
                    plot_group_waveforms(
                        times_ref,
                        wf_a,
                        wf_b,
                        contrast["a_name"],
                        contrast["b_name"],
                        title,
                        erp_dir / f"{modality_key}_{contrast_name}_{roi_name}.png",
                    )

    df = pd.DataFrame(records)
    out_csv = tables_dir / "window_amplitudes.csv"
    df.to_csv(out_csv, index=False)
    print(f"[OK] Wrote ERP window table: {out_csv}")

    pd.DataFrame(condition_count_rows).to_csv(tables_dir / "condition_counts.csv", index=False)
    print(f"[OK] Wrote condition counts: {tables_dir / 'condition_counts.csv'}")

    pd.DataFrame(roi_usage_rows).to_csv(tables_dir / "roi_channel_usage.csv", index=False)
    print(f"[OK] Wrote ROI channel usage: {tables_dir / 'roi_channel_usage.csv'}")

    pd.DataFrame(channel_nan_rows).to_csv(tables_dir / "channel_nan_report.csv", index=False)
    print(f"[OK] Wrote channel NaN report: {tables_dir / 'channel_nan_report.csv'}")

    pd.DataFrame(skipped_rows).to_csv(tables_dir / "skipped_modality_epochs.csv", index=False)
    print(f"[OK] Wrote skipped modality report: {tables_dir / 'skipped_modality_epochs.csv'}")

    if df["mean_amplitude"].isna().any():
        n_nan = int(df["mean_amplitude"].isna().sum())
        print(f"[WARN] mean_amplitude still contains {n_nan} NaNs. Check ROI usage and skipped reports.")
    else:
        print("[OK] No NaNs in mean_amplitude.")


if __name__ == "__main__":
    main()
