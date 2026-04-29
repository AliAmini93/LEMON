# LEMON/MELON ERP Analysis Reproducibility Guide

**Purpose:**  
This document explains, step by step, how to rerun the full ERP analysis pipeline when new LEMON/MELON subjects become available, and how to update the current results.

The current analysis is a **neuroscience-first ERP analysis** of the **LEMON subset of the MELON Emotional Affect paradigm**. The main scientific focus is:

> Whether ear-EEG preserves stimulus-locked neural differences related to face/non-face processing compared with scalp EEG.

The current main contrast is:

> **Face − Non-face**

The current secondary/exploratory contrast is:

> **Emotional − Neutral**

This is **not** framed as participant-level emotion recognition, because the paradigm does not provide self-reported emotion labels.

---

## 1. Current Analysis Status

At the current stage, the analysis has produced:

- Subject availability audit
- Preprocessing and epoch extraction
- QC-based bad-channel and bad-modality decisions
- ERP window analysis
- Difference-wave plots
- Sensitivity analysis up to 800 ms
- W5 window summary for 600–800 ms
- A LaTeX progress report for supervisors

The current strongest finding is:

> Face − Non-face differences are clear in scalp EEG and partially preserved in ear-EEG, especially in the strict-ear and right-ear ROIs. The strongest late effect occurs in W4 = 320–600 ms and decreases during W5 = 600–800 ms.

---

## 2. Working Directory Assumption

All commands below assume that the project root is:

```text
F:\LEMON
```

Run all commands from this folder:

```bash
cd /d F:\LEMON
```

Expected main folders:

```text
F:\LEMON
├── configs/
│   ├── config.yaml
│   ├── config.yaml.bak_before_w5
│   └── qc_decisions.yaml
│
├── scripts/
│   ├── 00_add_w5_window.py
│   ├── 01_manifest.py
│   ├── 02_preprocess_epoch.py
│   ├── 03_erp_analysis.py
│   ├── 03b_plot_difference_waves.py
│   ├── 03b_plot_difference_waves_sens.py
│   ├── 03c_summarize_difference_windows.py
│   └── 04_statistics.py
│
├── output/
│   ├── manifests/
│   └── processed/
│
├── reports/
│   ├── qc/
│   ├── tables/
│   ├── stats/
│   ├── erp_diff/
│   └── erp_diff_sens/
│
├── sub-200/
├── sub-201/
└── ...
```

---

## 3. Before Adding New Subjects

Before copying new subject folders or rerunning the full pipeline, create a backup of the current outputs.

### 3.1. Backup current reports and outputs

In PowerShell:

```powershell
$date = Get-Date -Format "yyyyMMdd_HHmm"
New-Item -ItemType Directory -Force -Path "backups\backup_$date"

Copy-Item -Recurse -Force "reports" "backups\backup_$date\reports"
Copy-Item -Recurse -Force "output"  "backups\backup_$date\output"
Copy-Item -Recurse -Force "configs" "backups\backup_$date\configs"

Write-Output "Backup created: backups\backup_$date"
```

This is important because the next runs may overwrite:

```text
output/processed/
reports/tables/
reports/stats/
reports/erp_diff/
reports/erp_diff_sens/
```

---

## 4. Add New Subjects

When new subjects arrive, copy their folders directly into the root directory:

```text
F:\LEMON\sub-XXX
```

Example:

```text
F:\LEMON\sub-217
F:\LEMON\sub-218
F:\LEMON\sub-219
```

Each subject should ideally contain:

```text
sub-XXX/
└── ses-lab/
    ├── beh/
    ├── eeg/
    └── eyetracking/
```

---

## 5. Verify New Subject File Availability

Before running preprocessing, verify whether the new subjects contain the required files.

### 5.1. Full 11-modality availability check

Edit the subject list in the script below and run it in PowerShell from `F:\LEMON`.

```powershell
$subjects = @('200','201','202','203','204','205','206','207','208','209','211','212','213','214','215','216','217','218','219','220','221','222')

Write-Output "=== FULL MODALITY AVAILABILITY MATRIX ==="
Write-Output ""

foreach ($s in $subjects) {
    $base = "F:\LEMON\sub-$s\ses-lab"

    # Behavioral
    $beh_emo = Test-Path "$base\beh\sub-${s}_ses-lab_task-emotionalAffectParadigm_events.tsv"

    # EEG
    $ear_set = Test-Path "$base\eeg\sub-${s}_ses-lab_task-labParadigm_acq-earEEG_eeg.set"
    $scalp_set = Test-Path "$base\eeg\sub-${s}_ses-lab_task-labParadigm_acq-scalpEEG_eeg.set"

    # Physio
    $gsr = Test-Path "$base\eeg\sub-${s}_ses-lab_task-labParadigm_acq-GSR_physio.tsv.gz"
    $hr = Test-Path "$base\eeg\sub-${s}_ses-lab_task-labParadigm_acq-HRPlethSpO2_physio.tsv.gz"
    $gyro = Test-Path "$base\eeg\sub-${s}_ses-lab_task-labParadigm_acq-gyroAcc_physio.tsv.gz"

    # Eyetracking - Emotional Affect paradigm-specific
    $et_raw = Test-Path "$base\eyetracking\sub-${s}_ses-lab_task-EmotionalAffectParadigm_acq-eyetracking_rec-eye0_eyetracking.tsv.gz"
    $et_fix = Test-Path "$base\eyetracking\sub-${s}_ses-lab_task-EmotionalAffectParadigm_acq-fixations_rec-eye0_events.tsv"
    $et_sac = Test-Path "$base\eyetracking\sub-${s}_ses-lab_task-EmotionalAffectParadigm_acq-saccades_rec-eye0_events.tsv"
    $et_blink = Test-Path "$base\eyetracking\sub-${s}_ses-lab_task-EmotionalAffectParadigm_acq-blinks_rec-eye0_events.tsv"
    $et_ev = Test-Path "$base\eyetracking\sub-${s}_ses-lab_task-EmotionalAffectParadigm_acq-events_rec-eye0_events.tsv"

    Write-Output "sub-$s | beh=$beh_emo | ear=$ear_set | scalp=$scalp_set | GSR=$gsr | HR=$hr | gyro=$gyro | ET_raw=$et_raw | ET_fix=$et_fix | ET_sac=$et_sac | ET_blink=$et_blink | ET_ev=$et_ev"
}
```

### 5.2. Interpretation

For the **main ear-vs-scalp ERP analysis**, a subject should have at least:

```text
beh = True
ear = True
scalp = True
```

If one of these is missing:

- no `beh` → no labels, not usable for current ERP contrasts
- no `ear` → not usable for ear analysis
- no `scalp` → not usable for scalp analysis
- no `beh + no scalp` but has ear → may be useful later only if labels can be reconstructed, but not for the current main pipeline

---

## 6. Update `config.yaml` if Needed

Open:

```text
configs/config.yaml
```

Check whether there is a field such as:

```yaml
subjects_expected:
  - 200
  - 201
```

or:

```yaml
main_subjects:
  - 200
  - 201
```

If new subjects were added, include their IDs.

Example:

```yaml
subjects_expected:
  - 200
  - 201
  - 202
  - 203
  - 205
  - 206
  - 208
  - 209
  - 211
  - 212
  - 213
  - 214
  - 215
  - 217
  - 218
  - 219
  - 220
  - 221
  - 222
```

If `01_manifest.py` auto-detects subjects from the folder structure, this step may not be necessary. Still, always check the generated manifest in the next step.

---

## 7. Ensure W5 Exists in `config.yaml`

The current analysis uses:

```yaml
erp_windows_ms:
  W1: [80, 130]
  W2: [130, 220]
  W3: [220, 320]
  W4: [320, 600]
  W5: [600, 800]
```

If W5 is missing, run:

```bash
python scripts/00_add_w5_window.py --config configs/config.yaml
```

Expected output:

```text
[OK] Backup created or already exists
[OK] Updated config: configs\config.yaml
[OK] erp_windows_ms:
  W1: [80, 130]
  W2: [130, 220]
  W3: [220, 320]
  W4: [320, 600]
  W5: [600, 800]
```

---

## 8. Generate the Subject Manifest

Run:

```bash
python scripts/01_manifest.py --config configs/config.yaml
```

Expected output:

```text
[OK] Wrote manifest: output\manifests\subject_manifest.csv
[OK] Main subjects (...): ...
[OK] Ear-only subjects (...): ...
```

Then open:

```text
output/manifests/subject_manifest.csv
```

Check:

- Which subjects are classified as usable/main
- Which subjects are excluded
- Whether the new subjects appear correctly

If new subjects do not appear, check:

1. Folder naming: `sub-XXX`
2. Session folder: `ses-lab`
3. File names
4. `config.yaml` subject list

---


## 9. First Preprocessing Run for New/Updated Dataset

Run preprocessing with the current QC decisions:

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
```

Expected output:

```text
[OK] sub-XXX: saved epochs to output\processed\sub-XXX
[OK] Wrote QC summary: reports\qc\preprocess_qc_summary.csv
```

### 9.1. Why `--disable-reject`?

Earlier, strict automatic rejection removed all epochs for some subjects. For this ERP-first exploratory workflow, we currently:

1. preprocess with `--disable-reject`;
2. inspect signal quality manually and semi-automatically;
3. apply bad-channel and bad-modality decisions via `qc_decisions.yaml`.

---

## 10. Inspect Preprocessing QC Summary

Open:

```text
reports/qc/preprocess_qc_summary.csv
```

Important columns to check:

```text
subject_id
n_behavior_rows
n_epochs_main_ear
n_epochs_main_scalp
n_epochs_sens_ear
n_epochs_sens_scalp
ear_full_final_nchan
ear_strict_final_nchan
scalp_final_nchan
```

Expected values for a good subject:

```text
n_behavior_rows = 400
n_epochs_main_ear = 400
n_epochs_main_scalp = 400
n_epochs_sens_ear = 400
n_epochs_sens_scalp = 400
```

If a subject has fewer or zero epochs, inspect:

- behavioral file
- event timing columns
- EEG file duration
- missing modality
- preprocessing errors

---

## 11. Run or Update QC Diagnostics

The current project used two key QC diagnostics:

```text
reports/qc/epoch_ptp_threshold_scan.csv
reports/qc/channel_ptp_scan.csv
```

If the scripts that generated these files are available in your local `scripts/` folder, rerun them after adding new subjects. If not, use the principles below manually or via a diagnostic script.

### 11.1. Epoch-level PTP scan

The purpose is to detect subjects/modalities where many epochs have extreme peak-to-peak amplitude.

Previously useful thresholds included:

```text
100 µV
200 µV
300 µV
500 µV
```

Interpretation:

- Many epochs above 100 µV may indicate noisy data, but not always fatal.
- Many epochs above 300–500 µV often indicate serious artifacts.
- If all or nearly all epochs are extreme, inspect channel-level diagnostics.

### 11.2. Channel-level PTP scan

The purpose is to identify:

- all-NaN channels
- channels with extremely high median PTP
- channels with extremely high p95 or p99 PTP

Decision logic:

| Situation | Decision |
|---|---|
| One or few bad channels | Drop bad channel(s) |
| Entire modality globally bad | Exclude modality for that subject |
| All-NaN channel | Drop channel |
| Single extreme ear channel | Drop channel |
| All ear channels extreme | Exclude ear modality |
| Most scalp channels extreme | Exclude scalp modality |

---

## 12. Update `qc_decisions.yaml`

Open:

```text
configs/qc_decisions.yaml
```

Current structure:

```yaml
bad_channels:
  '201':
    scalp:
      - CP5
      - TP7
      - T7
    ear:
      - ER3

exclude_modality:
  scalp:
    - '209'
    - '212'
  ear:
    - '213'
    - '215'
```

### 12.1. Add new bad channels

Example:

```yaml
bad_channels:
  '217':
    scalp:
      - FC5
    ear:
      - ER2
```

### 12.2. Add modality exclusions

Example:

```yaml
exclude_modality:
  scalp:
    - '209'
    - '212'
    - '218'
  ear:
    - '213'
    - '215'
    - '219'
```

### 12.3. Important notes

- Use subject IDs as strings, e.g. `'217'`.
- Do not remove old decisions unless you intentionally want to reinclude those data.
- After changing `qc_decisions.yaml`, rerun preprocessing.

---

## 13. Re-run Preprocessing After QC Updates

After updating `qc_decisions.yaml`, rerun:

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
```

Expected output should include lines such as:

```text
[QC] sub-201 ear: dropped channels: ER3
[QC] sub-201 scalp: dropped channels: CP5, TP7, T7
[QC] sub-213: skipped ear modality due to qc_decisions.yaml
[OK] sub-XXX: saved epochs to output\processed\sub-XXX
```

Check that no unexpected subject is skipped.

---

## 14. Run ERP Window Analysis

Run:

```bash
python scripts/03_erp_analysis.py --config configs/config.yaml
```

Expected output:

```text
[OK] Wrote ERP window table: reports\tables\window_amplitudes.csv
[OK] Wrote condition counts: reports\tables\condition_counts.csv
[OK] Wrote ROI channel usage: reports\tables\roi_channel_usage.csv
[OK] Wrote channel NaN report: reports\tables\channel_nan_report.csv
[OK] Wrote skipped modality report: reports\tables\skipped_modality_epochs.csv
[OK] No NaNs in mean_amplitude.
```

### 14.1. If NaNs appear

Check:

```text
reports/tables/channel_nan_report.csv
reports/tables/roi_channel_usage.csv
```

Likely reasons:

- a bad channel was not added to `qc_decisions.yaml`
- all channels in an ROI were removed
- one channel is all-NaN
- a modality should be excluded

Then update `qc_decisions.yaml` and rerun preprocessing and ERP analysis.

---

## 15. Run Window-Level Statistics

Run:

```bash
python scripts/04_statistics.py --config configs/config.yaml
```

Expected output:

```text
[OK] Wrote statistics table: reports\stats\erp_stats_results.csv
```

Main output:

```text
reports/stats/erp_stats_results.csv
```

Important columns:

```text
modality
contrast
roi
window
n
mean_diff
effect_size_dz
p_value
p_fdr
```

Interpretation:

- Use p-values cautiously because the sample size is currently small.
- Treat non-FDR-corrected effects as exploratory trends.
- Main interpretation should still rely on effect direction, window consistency, and difference-wave plots.

---

## 16. Generate Main Difference-Wave Plots

Run:

```bash
python scripts/03b_plot_difference_waves.py --config configs/config.yaml
```

Expected output:

```text
[OK] scalp_main_face_vs_nonface_face_roi: n=...
[OK] scalp_main_face_vs_nonface_central_roi: n=...
[OK] scalp_main_face_vs_nonface_late_roi: n=...
[OK] scalp_main_emotional_vs_neutral_face_roi: n=...
[OK] ear_full_main_face_vs_nonface_ear_full: n=...
[OK] ear_strict_main_face_vs_nonface_ear_strict: n=...
[OK] ear_full_main_face_vs_nonface_ear_right: n=...
[OK] ear_full_main_emotional_vs_neutral_ear_right: n=...
```

Outputs:

```text
reports/erp_diff/
```

Important files:

```text
reports/erp_diff/scalp_main_face_vs_nonface_face_roi.png
reports/erp_diff/scalp_main_face_vs_nonface_late_roi.png
reports/erp_diff/ear_strict_main_face_vs_nonface_ear_strict.png
reports/erp_diff/ear_full_main_face_vs_nonface_ear_right.png
reports/erp_diff/scalp_main_emotional_vs_neutral_face_roi.png
reports/erp_diff/ear_full_main_emotional_vs_neutral_ear_right.png
```

---

## 17. Summarize Main Difference-Wave Windows

Run:

```bash
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv
```

Important note:

- If `config.yaml` includes W5, the main 600 ms epoch may not contain valid W5 values.
- W5 should be interpreted using the sensitivity outputs from `reports/erp_diff_sens`.

Main output:

```text
reports/erp_diff/difference_window_summary.csv
```

---

## 18. Generate Sensitivity Difference-Wave Plots

Sensitivity plots use epochs extending to 800 ms.

Run:

```bash
python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml
```

Expected output:

```text
[OK] scalp_sens_face_vs_nonface_face_roi: n=...
[OK] scalp_sens_face_vs_nonface_central_roi: n=...
[OK] scalp_sens_face_vs_nonface_late_roi: n=...
[OK] scalp_sens_emotional_vs_neutral_face_roi: n=...
[OK] ear_full_sens_face_vs_nonface_ear_full: n=...
[OK] ear_strict_sens_face_vs_nonface_ear_strict: n=...
[OK] ear_full_sens_face_vs_nonface_ear_right: n=...
[OK] ear_full_sens_emotional_vs_neutral_ear_right: n=...
```

Outputs:

```text
reports/erp_diff_sens/
```

Important files:

```text
reports/erp_diff_sens/scalp_sens_face_vs_nonface_face_roi.png
reports/erp_diff_sens/scalp_sens_face_vs_nonface_late_roi.png
reports/erp_diff_sens/ear_strict_sens_face_vs_nonface_ear_strict.png
reports/erp_diff_sens/ear_full_sens_face_vs_nonface_ear_right.png
reports/erp_diff_sens/scalp_sens_emotional_vs_neutral_face_roi.png
reports/erp_diff_sens/ear_full_sens_emotional_vs_neutral_ear_right.png
```

---

## 19. Summarize Sensitivity Windows Including W5

Run:

```bash
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
```

Expected output:

```text
[OK] Read 8 grand-average files from: reports\erp_diff_sens
[OK] Wrote window summary: reports\erp_diff_sens\difference_window_summary_w5.csv
```

Main output:

```text
reports/erp_diff_sens/difference_window_summary_w5.csv
```

This table should include:

```text
W1: 80–130 ms
W2: 130–220 ms
W3: 220–320 ms
W4: 320–600 ms
W5: 600–800 ms
```

---


## 20. Check Whether W4 Still Dominates After Adding New Subjects

Open:

```text
reports/erp_diff_sens/difference_window_summary_w5.csv
```

Focus on:

```text
contrast = face_vs_nonface
window = W4 and W5
```

Key rows to check:

```text
scalp_sens / face_roi / W4 and W5
scalp_sens / late_roi / W4 and W5
ear_strict_sens / ear_strict / W4 and W5
ear_full_sens / ear_right / W4 and W5
```

Previously, the key result was:

| ROI | W4 mean | W5 mean | Interpretation |
|---|---:|---:|---|
| scalp face_roi | 2.196 | 0.643 | clear decrease |
| scalp late_roi | 2.079 | 0.635 | clear decrease |
| ear_strict | 1.804 | 0.393 | strong decrease |
| ear_right | 1.659 | 0.223 | strong decrease |

After new subjects are added, verify whether this pattern remains.

---

## 21. Scientific Interpretation Checklist

After rerunning the full pipeline, check the following.

### 21.1. Face − Non-face

Ask:

- Is Face − Non-face still stronger than Emotional − Neutral?
- Is W4 still the strongest late window?
- Does W5 still show a decrease after 600 ms?
- Does ear_strict still show a positive W4 effect?
- Does ear_right still show a strong W4 effect?

If yes, the current main narrative remains stable:

> Ear-EEG preserves part of the late face-related ERP information, especially in strict-ear and right-ear ROIs.

### 21.2. Emotional − Neutral

Ask:

- Is Emotional − Neutral still weak/noisy?
- Does it remain less stable than Face − Non-face?
- Are any effects consistent across subjects?

If it remains weak, keep it exploratory.

### 21.3. Scalp vs Ear

Ask:

- Is scalp still stronger than ear?
- Is ear still above zero in W4?
- Does strict-ear remain meaningful after removing Fpz?

This is important for the core ear-EEG claim.

---

## 22. Update the LaTeX Report

After rerunning analyses, update the Overleaf report with:

### 22.1. Updated figures

Copy updated plots from:

```text
reports/erp_diff_sens/
```

to your LaTeX project:

```text
figures/
```

Most important figures:

```text
scalp_sens_face_vs_nonface_face_roi.png
scalp_sens_face_vs_nonface_late_roi.png
ear_strict_sens_face_vs_nonface_ear_strict.png
ear_full_sens_face_vs_nonface_ear_right.png
scalp_sens_emotional_vs_neutral_face_roi.png
ear_full_sens_emotional_vs_neutral_ear_right.png
```

### 22.2. Updated tables

Copy updated CSV files from:

```text
reports/erp_diff_sens/difference_window_summary_w5.csv
reports/stats/erp_stats_results.csv
reports/qc/preprocess_qc_summary.csv
reports/tables/roi_channel_usage.csv
reports/tables/skipped_modality_epochs.csv
```

to:

```text
tables/
```

### 22.3. Update text

Update:

- number of usable subjects
- number of excluded modalities
- W4/W5 means
- whether the current conclusions changed after adding new subjects

---

## 23. Recommended Full Rerun Command Sequence

After new subjects are copied and `config.yaml` is updated, the full rerun sequence is:

```bash
cd /d F:\LEMON

python scripts/01_manifest.py --config configs/config.yaml

python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject

python scripts/03_erp_analysis.py --config configs/config.yaml

python scripts/04_statistics.py --config configs/config.yaml

python scripts/03b_plot_difference_waves.py --config configs/config.yaml

python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv

python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml

python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
```

---

## 24. Expected Final Outputs After Rerun

After the full rerun, these files/folders should be updated:

```text
output/manifests/subject_manifest.csv
output/processed/sub-XXX/

reports/qc/preprocess_qc_summary.csv

reports/tables/window_amplitudes.csv
reports/tables/condition_counts.csv
reports/tables/roi_channel_usage.csv
reports/tables/channel_nan_report.csv
reports/tables/skipped_modality_epochs.csv

reports/stats/erp_stats_results.csv

reports/erp_diff/
reports/erp_diff/difference_window_summary.csv

reports/erp_diff_sens/
reports/erp_diff_sens/difference_window_summary_w5.csv
```

---

## 25. Troubleshooting

### 25.1. Problem: `Epochs-object is empty`

Likely cause:

- artifact rejection too strict
- incorrect event onsets
- EEG file too short
- no valid events

Solution:

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
```

Then inspect QC manually.

---

### 25.2. Problem: `No NaNs in mean_amplitude` is not shown

Likely cause:

- bad channel not removed
- all-NaN channel in ROI
- subject/modality should be excluded

Check:

```text
reports/tables/channel_nan_report.csv
reports/tables/roi_channel_usage.csv
reports/tables/skipped_modality_epochs.csv
```

Update:

```text
configs/qc_decisions.yaml
```

Then rerun:

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
python scripts/03_erp_analysis.py --config configs/config.yaml
```

---

### 25.3. Problem: New subjects do not appear in manifest

Check:

- folder name is `sub-XXX`
- files are under `ses-lab`
- `config.yaml` includes the new subject IDs if required
- behavioral file exists:

```text
sub-XXX_ses-lab_task-emotionalAffectParadigm_events.tsv
```

Rerun:

```bash
python scripts/01_manifest.py --config configs/config.yaml
```

---

### 25.4. Problem: W5 is missing

Run:

```bash
python scripts/00_add_w5_window.py --config configs/config.yaml
```

Then rerun sensitivity summary:

```bash
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
```

---

## 26. Current Scientific Claims to Preserve

When updating results, preserve the correct scientific framing.

### Do not claim:

> Ear-EEG detects emotions.

Do not claim:

> This is participant-level emotion recognition.

Do not claim:

> The paradigm provides self-reported valence/arousal labels.

### Correct claim:

> The LEMON/MELON Emotional Affect paradigm supports stimulus-locked analysis of face-related EEG responses. Face − Non-face effects are stronger and more stable than Emotional − Neutral effects. Ear-EEG appears to preserve part of the late face-related neural information, especially in strict-ear and right-ear ROIs.

---

## 27. Next Planned Analysis Step

The next planned script is:

```text
03d_subject_level_difference_stats.py
```

Goal:

For each:

```text
subject × modality × ROI × contrast × window
```

compute:

```text
mean(condition A) - mean(condition B)
```

Then perform:

- one-sample t-test against zero
- Wilcoxon signed-rank test
- effect size estimation
- FDR correction

This will allow final inferential claims at the subject level.

---

## 28. Minimal Checklist for Future Updates

When new subjects arrive:

- [ ] Copy `sub-XXX` folders to `F:\LEMON`
- [ ] Run modality availability check
- [ ] Update `config.yaml` if needed
- [ ] Ensure W5 exists in `config.yaml`
- [ ] Run `01_manifest.py`
- [ ] Check `subject_manifest.csv`
- [ ] Run preprocessing with current QC decisions
- [ ] Inspect `preprocess_qc_summary.csv`
- [ ] Run/update QC diagnostics
- [ ] Update `qc_decisions.yaml`
- [ ] Re-run preprocessing
- [ ] Run ERP analysis
- [ ] Run statistics
- [ ] Generate main difference waves
- [ ] Generate sensitivity difference waves
- [ ] Generate W5 summary
- [ ] Check whether W4 remains the strongest window
- [ ] Update LaTeX report figures and tables
- [ ] Document any change in conclusions

---

## 29. Short Version: One-Block Command Rerun

Use this only after:

1. new subjects are copied,
2. `config.yaml` is updated,
3. `qc_decisions.yaml` is updated or confirmed.

```bash
cd /d F:\LEMON

python scripts/01_manifest.py --config configs/config.yaml

python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject

python scripts/03_erp_analysis.py --config configs/config.yaml

python scripts/04_statistics.py --config configs/config.yaml

python scripts/03b_plot_difference_waves.py --config configs/config.yaml

python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv

python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml

python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
```

---

## 30. Final Note

This workflow is designed for the current ERP-first analysis. It is not yet optimized for machine learning or deep learning. For ML/DL, channel consistency and subject-specific channel removal must be handled separately before training any model.
