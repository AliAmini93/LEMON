# LEMON ERP Analysis

Neuroscience-first ERP analysis of the **LEMON subset of the MELON Emotional Affect paradigm**, focusing on whether ear-EEG preserves stimulus-locked face-related neural differences compared with scalp EEG.

> **Important framing:** this project is **not** participant-level emotion recognition.  
> The paradigm does not provide self-reported valence/arousal/SAM labels. The labels describe the **stimulus category** shown to the participant, not the participant's internal affective state.

## Project Summary

The analysis studies EEG responses during the Emotional Affect paradigm, where participants view emotional facial-expression images and non-face control images inside a face-memory task. The main question is:

> Does ear-EEG preserve ERP information related to face/non-face stimulus processing compared with scalp EEG?

The current analysis is ERP-first and interpretability-first. Machine learning and deep learning are intentionally postponed until the ERP signal structure is better established.

## Scientific Framing

### Correct framing

Use terms such as:

- Face-related stimulus processing
- Face/non-face ERP differentiation
- Affective visual stimulus processing
- Stimulus-locked ERP analysis
- Ear-EEG versus scalp EEG comparison

### Avoid these claims

Do **not** claim that this project performs:

- Emotion recognition
- Participant-level affective state classification
- Valence/arousal decoding
- Internal emotional-state detection
- Robust emotion-specific decoding from ear-EEG

The main labels are stimulus labels, not self-report emotion labels.

## Current Main Findings

The strongest current evidence is for the **Face − Non-face** contrast.

| Finding | Status |
|---|---|
| Scalp W4 Face − Non-face late ROI effect | Strongest and most defensible result |
| Clean scalp W4 topography | Supports posterior-to-centroparietal positivity |
| Ear W4 Face − Non-face effect in strict/right ROIs | Partially preserved, moderate-to-strong |
| Ear W4-to-W5 decrease | Supports temporal concentration of the ear effect |
| Emotional − Neutral | Exploratory and weaker |
| Canonical N170 preservation | Not strongly supported |

Key planned ROI-level results from the current snapshot:

| Effect | Window | n | Result |
|---|---:|---:|---|
| Scalp late ROI, Face − Non-face | W4: 320–600 ms | 11 | mean = 2.08, p = .00098, dz = 1.39 |
| Scalp face ROI, Face − Non-face | W4: 320–600 ms | 11 | mean = 2.20, p = .128, dz = 0.50 |
| Ear strict montage, Face − Non-face | W4: 320–600 ms | 11 | mean = 1.80, p = .020, dz = 0.83 |
| Ear right ROI, Face − Non-face | W4: 320–600 ms | 11 | mean = 1.66, p = .017, dz = 0.86 |
| Ear strict, W4 − W5 decrease | W4 vs W5 | 11 | p = .028, dz = 0.77 |
| Ear right, W4 − W5 decrease | W4 vs W5 | 11 | p = .010, dz = 0.95 |

These values should be interpreted as **planned ROI-level ERP tests**, not broad whole-scalp corrected inference across every exploratory combination.

## Dataset and Subject Status

The available data snapshot contains 16 expected subjects:

```text
sub-200, sub-201, sub-202, sub-203, sub-204, sub-205, sub-206, sub-207,
sub-208, sub-209, sub-211, sub-212, sub-213, sub-214, sub-215, sub-216
```

The current main analysis uses 13 subjects with behavioral labels and both EEG modalities available before QC:

```text
200, 201, 202, 203, 205, 206, 208, 209, 211, 212, 213, 214, 215
```

Excluded from the main analysis:

| Subject | Reason |
|---|---|
| `sub-204` | Missing behavioral and ear-EEG data; only scalp-related files available |
| `sub-207` | Missing behavioral and ear-EEG data; only scalp-related files available |
| `sub-216` | Missing behavioral and scalp data; not usable for main ear-vs-scalp ERP analysis |

After QC, the planned-test subject counts are:

| Analysis set | n |
|---|---:|
| Behavioral-label subjects | 13 |
| Scalp planned-test subjects | 11 |
| Ear planned-test subjects | 11 |
| Subjects with both scalp and ear after QC | 9 |

## Experimental Contrast Definitions

### Main contrast

```text
Face − Non-face
```

This is the primary and most defensible contrast.

### Secondary / exploratory contrast

```text
Emotional − Neutral
```

where:

```text
Emotional = happy + angry + afraid
Neutral = neutral
```

This contrast is weaker and should remain exploratory in the current write-up.

## ERP Windows

The current ERP windows are defined in `configs/config.yaml`:

| Window | Time range |
|---|---:|
| W1 | 80–130 ms |
| W2 | 130–220 ms |
| W3 | 220–320 ms |
| W4 | 320–600 ms |
| W5 | 600–800 ms |

The main effect is concentrated in:

```text
W4 = 320–600 ms
```

W5 was added as a sensitivity window to test whether the late W4 effect continues after 600 ms. The current evidence suggests that the effect decreases during W5, especially in ear-EEG strict/right configurations.

## Channel Definitions

### Ear-EEG channels

The ear recording contains 11 channels:

```text
Fpz, M1, M2, EL1, EL3, EL4, EL5, ER1, ER2, ER3, ER4
```

Notes:

- `EL2` is not present in the current channel set.
- `Fpz` is a frontal/shared channel and is excluded from the strict-ear montage.

### Ear montages / ROIs

| Name | Channels |
|---|---|
| `ear_full` | Fpz, M1, M2, EL1, EL3, EL4, EL5, ER1, ER2, ER3, ER4 |
| `ear_strict` | M1, M2, EL1, EL3, EL4, EL5, ER1, ER2, ER3, ER4 |
| `ear_left` | EL1, EL3, EL4, EL5 |
| `ear_right` | ER1, ER2, ER3, ER4 |
| `ear_mastoid` | M1, M2 |

### Scalp ROIs

Defined in `configs/config.yaml`:

| ROI | Channels |
|---|---|
| `face_roi` | P7, P8, TP7, TP8, O1, O2 |
| `late_roi` | Pz, CP1, CP2, Cz |
| `central_roi` | Fz, Cz, Pz |

EOG channels are dropped from scalp EEG.

## Repository Structure

Expected project structure:

```text
.
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
│   ├── 03_erp_analysis_sens.py
│   ├── 03b_plot_difference_waves.py
│   ├── 03b_plot_difference_waves_sens.py
│   ├── 03c_summarize_difference_windows.py
│   ├── 03d_subject_level_difference_stats.py
│   ├── 03e_make_final_erp_figures.py
│   ├── 03f_make_publication_erp_figures.py
│   ├── 03g_plot_w4_topography.py
│   ├── 03h_plot_clean_topography.py
│   ├── 04_statistics.py
│   └── utils.py
│
├── output/
│   ├── manifests/
│   └── processed/          # large processed epoch files are not tracked
│
├── reports/
│   ├── erp/
│   ├── erp_diff/
│   ├── erp_diff_sens/
│   ├── figures/
│   ├── figures_sens/
│   ├── final_figures/
│   ├── final_figures_v2/
│   ├── qc/
│   ├── stats/
│   ├── stats_sens/
│   ├── tables/
│   ├── topography/
│   └── topography_clean/
│
└── README.md
```

Raw subject folders such as `sub-200/`, `sub-201/`, etc. are expected locally for a full rerun, but should not be committed to GitHub.

## Data Availability and Git Policy

This repository should track:

- configuration files
- analysis scripts
- lightweight manifests
- QC summaries
- final tables
- final figures
- report-ready outputs
- documentation

This repository should **not** track:

- raw EEG files
- raw BIDS subject folders
- large processed epoch objects
- `.set`, `.fdt`, `.fif`, or similar large data files
- local backup folders
- Python cache files

Recommended `.gitignore` entries:

```gitignore
# Raw / private / large data
sub-*/
data/
output/processed/**/*.fif
output/processed/**/*.set
output/processed/**/*.fdt
*.set
*.fdt
*.fif
*.edf
*.bdf

# Local processed outputs that are too large
output/processed/

# Local backups
backups/

# Python
__pycache__/
*.pyc
.venv/
venv/
.env

# OS/editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

If small `metadata.csv` and `qc.json` files inside `output/processed/sub-*` should be tracked, remove the broad `output/processed/` rule and use a more selective ignore policy.

## Requirements

The scripts use Python and common scientific packages.

Recommended environment:

```text
Python >= 3.10
mne
numpy
pandas
scipy
matplotlib
pyyaml
```

Install example:

```bash
pip install mne numpy pandas scipy matplotlib pyyaml
```

If using Conda:

```bash
conda create -n lemon-erp python=3.11
conda activate lemon-erp
pip install mne numpy pandas scipy matplotlib pyyaml
```

## Configuration

Main configuration file:

```text
configs/config.yaml
```

Important fields:

```yaml
data_root: F:/LEMON
output_root: ./output
sfreq_target: 250.0
filters:
  l_freq: 0.5
  h_freq: 40.0
  notch: 50.0
epoch_main:
  tmin: -0.2
  tmax: 0.6
epoch_sensitivity:
  tmin: -0.2
  tmax: 0.8
baseline:
  tmin: -0.2
  tmax: 0.0
```

If running the project on another machine, update:

```yaml
data_root: <your-local-project-or-data-path>
```

QC decisions are stored separately in:

```text
configs/qc_decisions.yaml
```

The valid preprocessing rerun should use both config files:

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
```

## Full Reproducibility Pipeline

Run all commands from the project root.

On Windows PowerShell / Command Prompt:

```bat
cd /d F:\LEMON
```

On Unix-like systems:

```bash
cd /path/to/LEMON
```

### 1. Generate subject manifest

```bash
python scripts/01_manifest.py --config configs/config.yaml
```

Main output:

```text
output/manifests/subject_manifest.csv
```

### 2. Preprocess and epoch EEG

```bash
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
```

Main outputs:

```text
output/processed/sub-*/
reports/qc/preprocess_qc_summary.csv
```

The `--disable-reject` flag is used because strict automatic rejection previously removed all epochs for some subjects. The current workflow relies on explicit QC decisions in `configs/qc_decisions.yaml`.

### 3. Run main ERP window analysis

```bash
python scripts/03_erp_analysis.py --config configs/config.yaml
```

Outputs:

```text
reports/tables/window_amplitudes.csv
reports/tables/condition_counts.csv
reports/tables/roi_channel_usage.csv
reports/tables/channel_nan_report.csv
reports/tables/skipped_modality_epochs.csv
```

### 4. Run main statistics

```bash
python scripts/04_statistics.py --config configs/config.yaml
```

Output:

```text
reports/stats/erp_stats_results.csv
```

### 5. Generate main difference waves

```bash
python scripts/03b_plot_difference_waves.py --config configs/config.yaml
```

Outputs:

```text
reports/erp_diff/
```

### 6. Summarize main difference-wave windows

```bash
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv
```

### 7. Generate sensitivity difference waves up to 800 ms

```bash
python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml
```

Outputs:

```text
reports/erp_diff_sens/
```

### 8. Summarize sensitivity windows including W5

```bash
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
```

### 9. Run sensitivity ERP window extraction

```bash
python scripts/03_erp_analysis_sens.py --config configs/config.yaml
```

Outputs:

```text
reports/tables/window_amplitudes_sens.csv
reports/tables/condition_counts_sens.csv
reports/tables/roi_channel_usage_sens.csv
reports/tables/channel_nan_report_sens.csv
reports/tables/skipped_modality_epochs_sens.csv
```

### 10. Run subject-level difference statistics

Main run:

```bash
python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml
```

Sensitivity W5 run:

```bash
python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml --window-table reports/tables/window_amplitudes_sens.csv --condition-counts reports/tables/condition_counts_sens.csv --w5-summary reports/erp_diff_sens/difference_window_summary_w5.csv --out-dir reports/stats_sens --fig-dir reports/figures_sens
```

Outputs:

```text
reports/stats/
reports/stats_sens/
reports/figures/
reports/figures_sens/
```

### 11. Generate publication/report-ready final figures

```bash
python scripts/03f_make_publication_erp_figures.py --config configs/config.yaml
```

Outputs:

```text
reports/final_figures_v2/
```

Recommended main figures:

```text
reports/final_figures_v2/figure_01_difference_waves_v2.png
reports/final_figures_v2/figure_02_w4_subject_boxplot_compact_v2.png
reports/final_figures_v2/figure_03_w4_w5_summary_v2.png
reports/final_figures_v2/figure_05_w4_minus_w5_boxplot_v2.png
```

Supplementary figures:

```text
reports/final_figures_v2/figure_02b_w4_subject_boxplot_all_v2.png
reports/final_figures_v2/figure_04_w4_w5_paired_subjects_compact_v2.png
```

### 12. Generate W4 scalp topography

```bash
python scripts/03g_plot_w4_topography.py --config configs/config.yaml
```

Outputs:

```text
reports/topography/
```

### 13. Generate clean topography variants

```bash
python scripts/03h_plot_clean_topography.py --config configs/config.yaml
```

Outputs:

```text
reports/topography_clean/
```

Recommended main-report topography:

```text
reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_no_fp.png
```

Recommended supplementary/transparency topography:

```text
reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_clean_panel.png
```

The Overleaf report package also includes a fixed panel version:

```text
figures/scalp_sens_face_vs_nonface_W4_topomap_clean_panel_fixed.png
```

## One-Block Rerun Command

Use this only after raw data are available locally and `configs/config.yaml` points to the correct `data_root`.

```bash
python scripts/01_manifest.py --config configs/config.yaml
python scripts/02_preprocess_epoch.py --config configs/config.yaml --qc-decisions configs/qc_decisions.yaml --use-manifest --overwrite --disable-reject
python scripts/03_erp_analysis.py --config configs/config.yaml
python scripts/04_statistics.py --config configs/config.yaml
python scripts/03b_plot_difference_waves.py --config configs/config.yaml
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff --output reports/erp_diff/difference_window_summary.csv
python scripts/03b_plot_difference_waves_sens.py --config configs/config.yaml
python scripts/03c_summarize_difference_windows.py --config configs/config.yaml --input-dir reports/erp_diff_sens --output reports/erp_diff_sens/difference_window_summary_w5.csv
python scripts/03_erp_analysis_sens.py --config configs/config.yaml
python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml
python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml --window-table reports/tables/window_amplitudes_sens.csv --condition-counts reports/tables/condition_counts_sens.csv --w5-summary reports/erp_diff_sens/difference_window_summary_w5.csv --out-dir reports/stats_sens --fig-dir reports/figures_sens
python scripts/03f_make_publication_erp_figures.py --config configs/config.yaml
python scripts/03g_plot_w4_topography.py --config configs/config.yaml
python scripts/03h_plot_clean_topography.py --config configs/config.yaml
```

## Main Output Files

### Manifests

```text
output/manifests/subject_manifest.csv
output/manifests/manifest_summary.json
output/manifests/main_subjects.txt
```

### QC

```text
reports/qc/preprocess_qc_summary.csv
reports/qc/epoch_ptp_threshold_scan.csv
reports/qc/channel_ptp_scan.csv
```

### ERP tables

```text
reports/tables/window_amplitudes.csv
reports/tables/window_amplitudes_sens.csv
reports/tables/condition_counts.csv
reports/tables/condition_counts_sens.csv
reports/tables/roi_channel_usage.csv
reports/tables/roi_channel_usage_sens.csv
reports/tables/skipped_modality_epochs.csv
reports/tables/skipped_modality_epochs_sens.csv
```

### Statistics

```text
reports/stats/erp_stats_results.csv
reports/stats/subject_level_difference_stats.csv
reports/stats_sens/subject_level_difference_stats.csv
reports/stats_sens/subject_level_difference_stats_key_results.csv
reports/stats_sens/w4_w5_interpretation_summary.csv
```

### Final figures

```text
reports/final_figures_v2/figure_01_difference_waves_v2.png
reports/final_figures_v2/figure_02_w4_subject_boxplot_compact_v2.png
reports/final_figures_v2/figure_03_w4_w5_summary_v2.png
reports/final_figures_v2/figure_05_w4_minus_w5_boxplot_v2.png
reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_no_fp.png
```

## Overleaf / Report Package

The supervisor-facing report is maintained separately as an Overleaf-ready LaTeX package. The latest reviewed package contains:

```text
main.tex
figures/
tables/
README.md
```

The report is titled:

```text
Neuroscience-First ERP Analysis Report
```

Recommended compiler:

```text
pdfLaTeX
```

The report should be read as a neuroscience-first ERP analysis of stimulus-locked Face − Non-face effects, not as participant-level emotion recognition.

## Notes on Topography

The all-channel W4 scalp topography showed strong opposite-polarity frontal-pole values over:

```text
Fp1, Fp2, Fpz
```

Because these channels may reflect residual ocular/frontal activity and dominate the color scale, the main report uses a no-Fp visualization:

```text
reports/topography_clean/scalp_sens_face_vs_nonface_W4_topomap_no_fp.png
```

The robust-scale and clean-panel variants are retained for transparency.

## Limitations

Current limitations:

- Small sample size after QC.
- The current analysis uses planned ROI-level ERP tests, not whole-scalp corrected inference.
- Emotional − Neutral effects are exploratory.
- The paradigm is a face-memory task, so ERP effects may reflect face perception, affective salience, attention, and memory encoding together.
- The results should not be interpreted as participant-level emotion recognition.
- Canonical N170 preservation is not strongly supported.
- Subject-specific bad-channel removal is acceptable for ERP analysis but not directly suitable for fixed-shape ML/DL models.

## Future Work

Possible next directions:

1. Add newly available subjects and rerun the full pipeline.
2. Consolidate the current ERP report into a conference-style manuscript.
3. Start a separate classical decoding branch using xDAWN + Riemannian geometry.
4. Only after ERP and classical decoding are stable, consider deep learning models such as EEGNet or EEG-Conformer.
5. If ML/DL is pursued, create a separate ML-ready preprocessing branch with fixed channel policy, subject-wise validation, and leakage-safe splits.

## Recommended Citation / Acknowledgment

If this repository is used in a report or manuscript, acknowledge that the analysis is based on the LEMON subset of the MELON Emotional Affect paradigm and focuses on stimulus-locked ERP responses rather than emotion recognition.

## Maintainer

Ali Amini

