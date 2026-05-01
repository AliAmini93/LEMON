# LEMON ERP Analysis

Neuroscience-first ERP analysis of the LEMON/MELON Emotional Affect paradigm, with a focus on comparing scalp EEG and ear-EEG responses to Face versus Non-face stimuli.

This repository contains the analysis code, configuration files, quality-control decisions, ERP/statistical analysis scripts, and report-generation workflow used for the LEMON/MELON ERP project.

## Project Goal

The goal of this project is to first validate whether meaningful neural responses exist in the dataset before moving toward machine learning or deep learning.

The current analysis focuses on:

- Scalp EEG versus ear-EEG
- Face versus Non-face ERP responses
- Emotional versus Neutral ERP responses as an exploratory contrast
- Late ERP effects, especially W4 = 320–600 ms
- W4-to-W5 sensitivity analysis
- Scalp topography of the main Face–Non-face effect

The most defensible current finding is that scalp EEG shows a robust late Face–Non-face ERP effect, and ear-EEG partially preserves this late effect, especially in strict-ear and right-ear configurations.

## Scientific Framing

This project should not be framed as participant-level emotion recognition.

A safer and more accurate framing is:

> Neuroscience-first analysis of face-related stimulus processing in the LEMON/MELON Emotional Affect paradigm, comparing scalp EEG and ear-EEG.

The Emotional–Neutral contrast is currently treated as exploratory.

## Repository Structure

```text
LEMON/
├── configs/
│   ├── config.yaml
│   └── qc_decisions.yaml
│
├── scripts/
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
│   └── 04_statistics.py
│
├── reports/
│   ├── qc/
│   ├── tables/
│   ├── stats/
│   ├── stats_sens/
│   ├── figures/
│   ├── figures_sens/
│   ├── final_figures/
│   ├── final_figures_v2/
│   ├── erp_diff/
│   ├── erp_diff_sens/
│   ├── topography/
│   └── topography_clean/
│
├── output/
│   ├── manifests/
│   └── processed/
│
├── README.md
└── .gitignore
