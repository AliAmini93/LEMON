from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import mne
import numpy as np
import pandas as pd
import yaml

from utils import (
    ensure_dir,
    get_paths,
    labels_summary,
    load_config,
    output_root,
    read_behavioral_events,
    save_json,
)

mne.set_log_level("WARNING")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess and epoch LEMON EEG data with optional QC decisions.")
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    parser.add_argument("--qc-decisions", type=str, default="configs/qc_decisions.yaml")
    parser.add_argument("--subjects", nargs="*", default=None, help="Subject IDs, e.g. 200 201 202")
    parser.add_argument("--use-manifest", action="store_true", help="Read main subjects from output/manifests/main_subjects.txt")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--disable-reject",
        action="store_true",
        help="Disable amplitude-based epoch rejection. Useful while channel/subject QC is being stabilized.",
    )
    return parser.parse_args()


def resolve_subjects(cfg: dict, args: argparse.Namespace) -> List[str]:
    if args.subjects:
        return [s.replace("sub-", "") for s in args.subjects]
    if args.use_manifest:
        manifest = output_root(cfg) / "manifests" / "main_subjects.txt"
        return [line.strip().replace("sub-", "") for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    return cfg["main_subjects"]


def load_qc_decisions(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"bad_channels": {}, "exclude_modality": {"scalp": [], "ear": []}}
    with open(p, "r", encoding="utf-8") as f:
        qc = yaml.safe_load(f) or {}
    qc.setdefault("bad_channels", {})
    qc.setdefault("exclude_modality", {})
    qc["exclude_modality"].setdefault("scalp", [])
    qc["exclude_modality"].setdefault("ear", [])
    return qc


def modality_is_excluded(qc_decisions: dict, sid: str, modality: str) -> bool:
    return str(sid) in {str(x) for x in qc_decisions.get("exclude_modality", {}).get(modality, [])}


def get_bad_channels(qc_decisions: dict, sid: str, modality: str) -> List[str]:
    entry = qc_decisions.get("bad_channels", {}).get(str(sid), {}) or {}
    return list(entry.get(modality, []) or [])


def load_raw_set(path: Path) -> mne.io.BaseRaw:
    return mne.io.read_raw_eeglab(path, preload=True, uint16_codec="latin1", verbose="ERROR")


def preprocess_raw(raw: mne.io.BaseRaw, l_freq: float, h_freq: float, notch: float, sfreq_target: float) -> mne.io.BaseRaw:
    raw.filter(l_freq=l_freq, h_freq=h_freq, fir_design="firwin", verbose="ERROR")
    raw.notch_filter(freqs=[notch], verbose="ERROR")
    raw.resample(sfreq_target, npad="auto", verbose="ERROR")
    return raw


def drop_channels_if_present(raw_or_epochs, channels: List[str], label: str) -> List[str]:
    existing = [ch for ch in channels if ch in raw_or_epochs.ch_names]
    if existing:
        raw_or_epochs.drop_channels(existing)
        print(f"[QC] {label}: dropped channels: {', '.join(existing)}")
    return existing


def build_events_from_onsets(onsets_sec: np.ndarray, sfreq: float) -> np.ndarray:
    samples = np.round(onsets_sec.astype(float) * sfreq).astype(int)
    samples = np.clip(samples, 0, None)
    return np.c_[samples, np.zeros_like(samples), np.ones_like(samples)]


def make_epochs(
    raw: mne.io.BaseRaw,
    events: np.ndarray,
    metadata: pd.DataFrame,
    tmin: float,
    tmax: float,
    baseline: Tuple[float, float],
    reject_uv: float | None,
    label: str,
) -> Tuple[mne.Epochs, Dict]:
    event_times_sec = events[:, 0] / raw.info["sfreq"] if len(events) else np.array([])
    qc = {
        "label": label,
        "n_events_input": int(len(events)),
        "raw_tmin_sec": float(raw.times[0]) if len(raw.times) else None,
        "raw_tmax_sec": float(raw.times[-1]) if len(raw.times) else None,
        "event_tmin_sec": float(np.min(event_times_sec)) if len(event_times_sec) else None,
        "event_tmax_sec": float(np.max(event_times_sec)) if len(event_times_sec) else None,
        "reject_uv_requested": None if reject_uv is None else float(reject_uv),
        "fallback_without_reject": False,
    }

    reject = None if reject_uv is None or reject_uv <= 0 else {"eeg": reject_uv * 1e-6}

    def _build(reject_param):
        return mne.Epochs(
            raw,
            events=events,
            event_id={"image": 1},
            tmin=tmin,
            tmax=tmax,
            baseline=baseline,
            metadata=metadata,
            preload=True,
            reject=reject_param,
            detrend=None,
            on_missing="ignore",
            verbose="ERROR",
        )

    epochs = _build(reject)
    qc["n_epochs_after_first_pass"] = int(len(epochs))
    qc["n_epochs_dropped_first_pass"] = int(len(events) - len(epochs))

    if len(epochs) == 0 and reject is not None:
        print(f"[WARN] {label}: all epochs dropped with reject={reject_uv} uV. Rebuilding without rejection.")
        epochs = _build(None)
        qc["fallback_without_reject"] = True
        qc["n_epochs_after_fallback"] = int(len(epochs))
        qc["n_epochs_dropped_fallback"] = int(len(events) - len(epochs))

    if len(epochs) == 0:
        raise RuntimeError(
            f"No epochs could be created for {label}. "
            f"Raw range={qc['raw_tmin_sec']}-{qc['raw_tmax_sec']}s, "
            f"event range={qc['event_tmin_sec']}-{qc['event_tmax_sec']}s. "
            "Check event onsets/time base."
        )

    qc["n_epochs_final"] = int(len(epochs))
    qc["n_epochs_dropped_final"] = int(len(events) - len(epochs))
    return epochs, qc


def prepare_metadata(beh_path: Path) -> pd.DataFrame:
    df = read_behavioral_events(beh_path)
    return df.copy()


def save_metadata(metadata: pd.DataFrame, out_dir: Path) -> None:
    metadata.to_csv(out_dir / "metadata.csv", index=False)


def remove_old_epoch_files(out_dir: Path, modality_prefix: str) -> None:
    for p in out_dir.glob(f"{modality_prefix}*-epo.fif"):
        p.unlink(missing_ok=True)


def run_subject(cfg: dict, qc_decisions: dict, sid: str, overwrite: bool = False, disable_reject: bool = False) -> Dict:
    out_dir = ensure_dir(output_root(cfg) / "processed" / f"sub-{sid}")
    qc_path = out_dir / "qc.json"
    if qc_path.exists() and not overwrite:
        print(f"[SKIP] sub-{sid}: already processed. Use --overwrite to rerun.")
        return json.loads(qc_path.read_text(encoding="utf-8"))

    paths = get_paths(cfg, sid)
    metadata = prepare_metadata(paths["beh"])
    save_metadata(metadata, out_dir)

    exclude_ear = modality_is_excluded(qc_decisions, sid, "ear")
    exclude_scalp = modality_is_excluded(qc_decisions, sid, "scalp")

    qc = {
        "subject_id": sid,
        "n_behavior_rows": int(len(metadata)),
        "labels_summary": labels_summary(metadata),
        "exclude_ear": bool(exclude_ear),
        "exclude_scalp": bool(exclude_scalp),
        "ear_dropped_channels": [],
        "scalp_dropped_channels": [],
    }

    base = (cfg["baseline"]["tmin"], cfg["baseline"]["tmax"])
    reject_uv = None if disable_reject else cfg.get("artifact", {}).get("reject_uv", None)

    if not exclude_ear:
        ear_raw = load_raw_set(paths["ear"])
        qc["ear_original_sfreq"] = float(ear_raw.info["sfreq"])
        qc["ear_original_nchan"] = int(len(ear_raw.ch_names))
        qc["ear_raw_duration_sec"] = float(ear_raw.times[-1])
        bad_ear = get_bad_channels(qc_decisions, sid, "ear")
        dropped = drop_channels_if_present(ear_raw, bad_ear, f"sub-{sid} ear")
        qc["ear_dropped_channels"] = dropped
        preprocess_raw(ear_raw, cfg["filters"]["l_freq"], cfg["filters"]["h_freq"], cfg["filters"]["notch"], cfg["sfreq_target"])
        ear_onsets = metadata["onset_earEEG"].astype(float).to_numpy()
        ear_events = build_events_from_onsets(ear_onsets, ear_raw.info["sfreq"])
        epochs_ear_main, qc_ear_main = make_epochs(
            ear_raw, ear_events, metadata, cfg["epoch_main"]["tmin"], cfg["epoch_main"]["tmax"], base, reject_uv, f"sub-{sid} ear main"
        )
        epochs_ear_sens, qc_ear_sens = make_epochs(
            ear_raw, ear_events, metadata, cfg["epoch_sensitivity"]["tmin"], cfg["epoch_sensitivity"]["tmax"], base, reject_uv, f"sub-{sid} ear sensitivity"
        )
        strict_drop = [ch for ch in cfg["ear"]["strict_drop_channels"] if ch in epochs_ear_main.ch_names]
        epochs_ear_strict_main = epochs_ear_main.copy().drop_channels(strict_drop) if strict_drop else epochs_ear_main.copy()
        epochs_ear_strict_sens = epochs_ear_sens.copy().drop_channels(strict_drop) if strict_drop else epochs_ear_sens.copy()
        remove_old_epoch_files(out_dir, "ear_")
        epochs_ear_main.save(out_dir / "ear_full_main-epo.fif", overwrite=True, verbose="ERROR")
        epochs_ear_sens.save(out_dir / "ear_full_sens-epo.fif", overwrite=True, verbose="ERROR")
        epochs_ear_strict_main.save(out_dir / "ear_strict_main-epo.fif", overwrite=True, verbose="ERROR")
        epochs_ear_strict_sens.save(out_dir / "ear_strict_sens-epo.fif", overwrite=True, verbose="ERROR")
        qc.update({
            "ear_full_final_nchan": int(len(epochs_ear_main.ch_names)),
            "ear_strict_final_nchan": int(len(epochs_ear_strict_main.ch_names)),
            "n_epochs_main_ear": int(len(epochs_ear_main)),
            "n_epochs_sens_ear": int(len(epochs_ear_sens)),
            "epoch_qc_ear_main": qc_ear_main,
            "epoch_qc_ear_sensitivity": qc_ear_sens,
            "ear_channels": epochs_ear_main.ch_names,
        })
    else:
        remove_old_epoch_files(out_dir, "ear_")
        print(f"[QC] sub-{sid}: skipped ear modality due to qc_decisions.yaml")
        qc.update({
            "ear_full_final_nchan": 0,
            "ear_strict_final_nchan": 0,
            "n_epochs_main_ear": 0,
            "n_epochs_sens_ear": 0,
            "ear_channels": [],
        })

    if not exclude_scalp:
        scalp_raw = load_raw_set(paths["scalp"])
        scalp_raw.drop_channels([ch for ch in cfg["scalp"]["drop_channels"] if ch in scalp_raw.ch_names])
        qc["scalp_original_sfreq"] = float(scalp_raw.info["sfreq"])
        qc["scalp_original_nchan_after_eog_drop"] = int(len(scalp_raw.ch_names))
        qc["scalp_raw_duration_sec"] = float(scalp_raw.times[-1])
        bad_scalp = get_bad_channels(qc_decisions, sid, "scalp")
        dropped = drop_channels_if_present(scalp_raw, bad_scalp, f"sub-{sid} scalp")
        qc["scalp_dropped_channels"] = dropped
        preprocess_raw(scalp_raw, cfg["filters"]["l_freq"], cfg["filters"]["h_freq"], cfg["filters"]["notch"], cfg["sfreq_target"])
        scalp_onsets = metadata["estimated_onset_scalpEEG"].astype(float).to_numpy()
        scalp_events = build_events_from_onsets(scalp_onsets, scalp_raw.info["sfreq"])
        epochs_scalp_main, qc_scalp_main = make_epochs(
            scalp_raw, scalp_events, metadata, cfg["epoch_main"]["tmin"], cfg["epoch_main"]["tmax"], base, reject_uv, f"sub-{sid} scalp main"
        )
        epochs_scalp_sens, qc_scalp_sens = make_epochs(
            scalp_raw, scalp_events, metadata, cfg["epoch_sensitivity"]["tmin"], cfg["epoch_sensitivity"]["tmax"], base, reject_uv, f"sub-{sid} scalp sensitivity"
        )
        remove_old_epoch_files(out_dir, "scalp_")
        epochs_scalp_main.save(out_dir / "scalp_main-epo.fif", overwrite=True, verbose="ERROR")
        epochs_scalp_sens.save(out_dir / "scalp_sens-epo.fif", overwrite=True, verbose="ERROR")
        qc.update({
            "scalp_final_nchan": int(len(epochs_scalp_main.ch_names)),
            "n_epochs_main_scalp": int(len(epochs_scalp_main)),
            "n_epochs_sens_scalp": int(len(epochs_scalp_sens)),
            "epoch_qc_scalp_main": qc_scalp_main,
            "epoch_qc_scalp_sensitivity": qc_scalp_sens,
            "scalp_channels": epochs_scalp_main.ch_names,
        })
    else:
        remove_old_epoch_files(out_dir, "scalp_")
        print(f"[QC] sub-{sid}: skipped scalp modality due to qc_decisions.yaml")
        qc.update({
            "scalp_final_nchan": 0,
            "n_epochs_main_scalp": 0,
            "n_epochs_sens_scalp": 0,
            "scalp_channels": [],
        })

    qc["sfreq_final"] = float(cfg["sfreq_target"])
    save_json(qc, qc_path)
    print(f"[OK] sub-{sid}: saved epochs to {out_dir}")
    return qc


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    qc_decisions = load_qc_decisions(args.qc_decisions)
    subjects = resolve_subjects(cfg, args)

    out_qc_dir = ensure_dir(Path("reports") / "qc")
    rows = []
    for sid in subjects:
        try:
            rows.append(run_subject(cfg, qc_decisions, sid, overwrite=args.overwrite, disable_reject=args.disable_reject))
        except Exception as exc:
            err = {"subject_id": sid, "error": str(exc)}
            rows.append(err)
            print(f"[ERROR] sub-{sid}: {exc}")

    pd.DataFrame(rows).to_csv(out_qc_dir / "preprocess_qc_summary.csv", index=False)
    print(f"[OK] Wrote QC summary: {out_qc_dir / 'preprocess_qc_summary.csv'}")


if __name__ == "__main__":
    main()
