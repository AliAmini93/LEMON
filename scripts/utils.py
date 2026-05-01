from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yaml


def load_config(config_path: str | Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_root(cfg: dict) -> Path:
    return Path(cfg["data_root"])


def output_root(cfg: dict) -> Path:
    return Path(cfg["output_root"])


def subject_root(cfg: dict, sid: str) -> Path:
    return data_root(cfg) / f"sub-{sid}" / "ses-lab"


def get_paths(cfg: dict, sid: str) -> Dict[str, Path]:
    base = subject_root(cfg, sid)
    beh = base / "beh" / f"sub-{sid}_ses-lab_task-emotionalAffectParadigm_events.tsv"
    eeg = base / "eeg"
    et = base / "eyetracking"
    return {
        "beh": beh,
        "ear": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-earEEG_eeg.set",
        "scalp": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-scalpEEG_eeg.set",
        "ear_events": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-earEEG_events.tsv",
        "scalp_events": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-scalpEEG_events.tsv",
        "gsr": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-GSR_physio.tsv.gz",
        "hr": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-HRPlethSpO2_physio.tsv.gz",
        "gyro": eeg / f"sub-{sid}_ses-lab_task-labParadigm_acq-gyroAcc_physio.tsv.gz",
        "et_raw": et / f"sub-{sid}_ses-lab_task-EmotionalAffectParadigm_acq-eyetracking_rec-eye0_eyetracking.tsv.gz",
        "et_fix": et / f"sub-{sid}_ses-lab_task-EmotionalAffectParadigm_acq-fixations_rec-eye0_events.tsv",
        "et_sac": et / f"sub-{sid}_ses-lab_task-EmotionalAffectParadigm_acq-saccades_rec-eye0_events.tsv",
        "et_blink": et / f"sub-{sid}_ses-lab_task-EmotionalAffectParadigm_acq-blinks_rec-eye0_events.tsv",
        "et_ev": et / f"sub-{sid}_ses-lab_task-EmotionalAffectParadigm_acq-events_rec-eye0_events.tsv",
    }


def check_subject_modalities(cfg: dict, sid: str) -> dict:
    paths = get_paths(cfg, sid)
    row = {"subject_id": sid}
    for key, path in paths.items():
        row[key] = path.exists()
    row["include_main"] = bool(row["beh"] and row["ear"] and row["scalp"])
    row["include_ear_only"] = bool((not row["include_main"]) and row["beh"] and row["ear"])
    row["n_modalities_present"] = sum(int(v) for k, v in row.items() if k not in {"subject_id", "include_main", "include_ear_only", "n_modalities_present", "notes"})
    row["notes"] = infer_subject_notes(row)
    return row


def infer_subject_notes(row: dict) -> str:
    missing = [k for k, v in row.items() if isinstance(v, bool) and not v and k not in {"include_main", "include_ear_only"}]
    if not missing:
        return "complete"
    return "missing:" + ",".join(missing)


def save_json(obj: dict, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def read_behavioral_events(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    # Normalize columns if present
    if "type" in df.columns:
        df["type"] = df["type"].astype(str).str.lower().str.strip()
    if "expression" in df.columns:
        df["expression"] = df["expression"].astype(str).str.lower().str.strip()
    return df


def build_metadata(df: pd.DataFrame) -> pd.DataFrame:
    meta = df.copy()
    # Derived columns
    if "type" in meta.columns:
        meta["is_face"] = meta["type"].eq("face")
        meta["is_non_face"] = meta["type"].eq("non_face")
    if "expression" in meta.columns:
        emotional = {"happy", "angry", "afraid"}
        meta["is_emotional"] = meta["expression"].isin(emotional)
        meta["is_neutral"] = meta["expression"].eq("neutral")
    return meta


def labels_summary(df: pd.DataFrame) -> dict:
    out = {}
    if "type" in df.columns:
        out["type_counts"] = df["type"].value_counts(dropna=False).to_dict()
    if "expression" in df.columns:
        out["expression_counts"] = df["expression"].value_counts(dropna=False).to_dict()
    return out


def available_channels(ch_names: List[str], desired: Iterable[str]) -> List[str]:
    desired_set = list(desired)
    return [ch for ch in desired_set if ch in ch_names]


def safe_drop_channels(ch_names: List[str], drop_list: Iterable[str]) -> List[str]:
    drops = set(drop_list)
    return [ch for ch in ch_names if ch not in drops]


def format_subject(sid: str) -> str:
    return sid if sid.startswith("sub-") else f"sub-{sid}"
