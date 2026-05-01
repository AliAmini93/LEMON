from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from utils import check_subject_modalities, ensure_dir, load_config, output_root, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build modality availability manifest for LEMON.")
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    out_root = output_root(cfg)
    manifests_dir = ensure_dir(out_root / "manifests")
    qc_dir = ensure_dir(Path("reports") / "qc")

    rows = [check_subject_modalities(cfg, sid) for sid in cfg["subjects_expected"]]
    df = pd.DataFrame(rows).sort_values("subject_id")

    manifest_path = manifests_dir / "subject_manifest.csv"
    df.to_csv(manifest_path, index=False)

    main_subjects = df.loc[df["include_main"], "subject_id"].tolist()
    ear_only_subjects = df.loc[df["include_ear_only"], "subject_id"].tolist()

    (manifests_dir / "main_subjects.txt").write_text("\n".join(main_subjects), encoding="utf-8")
    (manifests_dir / "ear_only_subjects.txt").write_text("\n".join(ear_only_subjects), encoding="utf-8")

    summary = {
        "n_expected": int(len(cfg["subjects_expected"])),
        "n_main_subjects": int(len(main_subjects)),
        "n_ear_only_subjects": int(len(ear_only_subjects)),
        "main_subjects": main_subjects,
        "ear_only_subjects": ear_only_subjects,
        "excluded_subjects": df.loc[~df["include_main"], "subject_id"].tolist(),
    }
    save_json(summary, manifests_dir / "manifest_summary.json")
    save_json(summary, qc_dir / "manifest_summary.json")

    modality_cols = [
        "beh", "ear", "scalp", "gsr", "hr", "gyro", "et_raw", "et_fix", "et_sac", "et_blink", "et_ev"
    ]
    modality_summary = pd.DataFrame({
        "modality": modality_cols,
        "n_present": [int(df[c].sum()) for c in modality_cols],
        "n_missing": [int((~df[c]).sum()) for c in modality_cols],
    })
    modality_summary.to_csv(qc_dir / "modality_availability_summary.csv", index=False)

    print(f"[OK] Wrote manifest: {manifest_path}")
    print(f"[OK] Main subjects ({len(main_subjects)}): {', '.join(main_subjects)}")
    print(f"[OK] Ear-only subjects ({len(ear_only_subjects)}): {', '.join(ear_only_subjects) or 'None'}")


if __name__ == "__main__":
    main()
