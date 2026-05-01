# Comprehensive Report on the LEMON/MELON Analysis Workflow So Far

## 0. Executive Summary

At the beginning, the main question was whether the **MELON dataset**, especially its **Emotional Affect paradigm**, could be useful for a PhD project focused on **emotion recognition using EEG/EMG/VR**. After reviewing the documentation, we realized that although MELON contains a paradigm called “Emotional Affect,” its nature is **not classical emotion recognition**. Participants do not provide self-report labels such as valence, arousal, dominance, or SAM ratings. Instead, they view facial images with different emotional expressions within a **face-memory task**.

Therefore, the framing of the project shifted from:

> Emotion Recognition

to:

> EEG-based decoding of emotional facial stimuli / face-related stimulus decoding

After discussing the topic with the supervisor, it became clear that working on this dataset could still be useful, especially as a short conference paper and potentially later as an extended journal version. Later, it became clear that the data available to us was not the full MELON dataset with around 100 participants, but a subset called **LEMON**, initially containing 16 participants, with 6 more expected later. However, from the 16 currently available subjects, only 13 were usable for the main analysis involving ear-EEG, scalp EEG, and behavioral labels.

After the dataset audit, we decided to temporarily set aside machine learning and deep learning, and instead perform a **neuroscience-first analysis**. The purpose was to examine ERPs, difference waves, and whether condition-related neural differences are visible in scalp EEG and ear-EEG before moving toward classification.

The most important finding so far is:

> The **Face − Non-face** contrast shows clear and relatively strong effects in scalp EEG, and part of this effect is also visible in ear-EEG, especially in the strict-ear and right-ear ROIs. In contrast, the **Emotional − Neutral** effect is weaker, noisier, and less temporally stable.

After the initial difference-wave analysis, the workflow was extended with **subject-level statistics** and **publication-ready final figures**. The current strongest planned ROI-level results are:

| Effect | Window | Result |
|---|---:|---|
| Scalp late ROI, Face − Non-face | W4: 320–600 ms | p < .001, dz = 1.39, n = 11 |
| Scalp face ROI, Face − Non-face | W4: 320–600 ms | p = .128, dz = 0.50, n = 11 |
| Ear strict montage, Face − Non-face | W4: 320–600 ms | p = .020, dz = 0.83, n = 11 |
| Ear right ROI, Face − Non-face | W4: 320–600 ms | p = .017, dz = 0.86, n = 11 |
| Ear strict, W4 − W5 decrease | W4 vs W5 | p = .028 |
| Ear right, W4 − W5 decrease | W4 vs W5 | p = .010 |

Therefore, the current scientific direction of the paper should be:

> Ear-EEG preserves coarse face/non-face stimulus-related ERP information, especially in late time windows, while emotion-specific effects are weaker and exploratory.

A key statistical caveat is that these should be described as **planned ROI-level tests** rather than as broad corrected effects across all possible exploratory comparisons.

---

## 1. Starting Point: Understanding the MELON Dataset

### 1.1. Initial Information from the Documentation

The full MELON project documentation was reviewed. The key points were:

- The MELON dataset was collected by the Center for Ear-EEG at Aarhus University.
- Apple supported the project.
- The main aim of the dataset was to investigate real-world and wearable applications of ear-EEG.
- The dataset includes both laboratory and outside-laboratory recordings.
- Multiple modalities are included:
  - ear-EEG
  - scalp EEG
  - GSR
  - PPG / HR / SpO2
  - IMU / gyroscope / accelerometer
  - eye tracking / pupillometry
  - behavioral data
- The full MELON dataset includes around 100 participants.
- The dataset is organized in a BIDS-like structure.

### 1.2. MELON Paradigms

Several laboratory paradigms were described:

- ASSR
- Relaxation
- Jaw movement
- Book reading
- Visual search
- Imposed sound
- Emotional Affect
- Cognitive Response / P300
- Mental Load

For the PhD project, the **Emotional Affect** paradigm was the most relevant part, because it is the only paradigm involving facial stimuli with emotional expressions.

---

## 2. Initial Conceptual Analysis: Is MELON Suitable for Emotion Recognition?

The initial question was:

> Is MELON close enough to datasets such as DEAP, MAHNOB-HCI, or I-DARE in terms of labels, task structure, and experimental design, so that it can be used together with them for training an emotion recognition model?

After reviewing the documentation, the answer became clear.

### 2.1. MELON Is Not Suitable for Participant Emotion Recognition

The reasons are:

- Participants do not provide self-report emotion labels.
- The labels do not represent the internal emotional state of the participant.
- The labels describe the stimulus category, such as:
  - face / non_face
  - happy / angry / afraid / neutral
- Each stimulus is shown for approximately 0.5 seconds.
- The task is not to report how the participant feels.
- The task is a face-memory task: at the end of each block, the participant is asked whether a target face appeared in the block.

Therefore, we cannot say:

> The model recognizes the participant’s emotion.

Instead, we should say:

> The model decodes the category of viewed emotional facial stimuli from EEG.

### 2.2. Correct Framing

A key decision was made early on: the paper should not use the term:

> Emotion Recognition

Instead, the correct terms are:

- Decoding emotional facial stimuli
- Affective stimulus decoding
- Face/non-face stimulus decoding
- Neural response to emotional facial stimuli

This decision is important because it prevents overclaiming and protects the work from likely reviewer criticism.

---

## 3. Relationship to the PhD Project

The PhD project is broadly focused on:

> Human emotion recognition using a hybrid BCI and MCI system

with emphasis on:

- EEG
- EMG
- Deep Learning
- VR serious games
- Emotion recognition / prediction
- Externally expressive emotions
- Mixed emotions

MELON is not fully aligned with the PhD objectives because:

- It does not include EMG.
- It does not include VR.
- It does not include self-reported emotion labels.
- It does not include a serious game context.

However, it can still be useful in several ways:

1. Practicing preprocessing and ERP analysis on real EEG data.
2. Investigating wearable EEG and ear-EEG.
3. Developing a side conference paper.
4. Strengthening the narrative around wearable affective sensing.
5. Comparing ear-EEG and scalp EEG recorded simultaneously.

---

## 4. Initial Conference Paper Idea

Given the limited time available, the initial paper idea was:

> Ear-EEG versus Scalp-EEG for Decoding Emotional Facial Stimuli in the MELON Dataset

A more accurate title later became:

> Ear-EEG versus Scalp-EEG for Face-Related Stimulus Decoding in the LEMON/MELON Emotional Affect Paradigm

### 4.1. Initial Research Question

The main research question was:

> What neural information about emotional facial stimuli is preserved in ear-EEG compared with scalp EEG?

### 4.2. Proposed Tasks

Three tasks were defined.

#### Task A: Face vs Non-face

- Label source: `type`
- Classes:
  - `face`
  - `non_face`
- This task became the safety-net task.
- It is more robust and more directly supported by the paradigm.

#### Task B: Emotional vs Neutral

- Only face trials are used.
- Emotional = `happy` + `angry` + `afraid`
- Neutral = `neutral`
- This task is closer to emotion, but it is imbalanced.

#### Task C: 4-Class Expression Classification

Classes:

- `happy`
- `angry`
- `afraid`
- `neutral`

This task is more ambitious and may later be useful for ML/DL analysis.

---

## 5. Methods Discussion: From EEGNet/SVM to ERP + xDAWN + DL

Initially, EEGNet and SVM were considered. However, after further discussion and input from another expert, we realized that using EEGNet alone would make the paper shallow.

### 5.1. Concern About EEGNet

The concern was:

- EEGNet has already been used extensively.
- It does not provide strong methodological novelty.
- If we only report that EEGNet performs better on scalp EEG than ear-EEG, the paper would be too superficial.

### 5.2. Shift in Novelty

We decided that the novelty of the paper should not be a new model, but a **scientific finding**:

> What type of neural information is preserved in ear-EEG, and what type of information is lost?

### 5.3. Final Methodological Framework

The final methodological framework became multi-layered.

#### Layer A: ERP Window Analysis

For interpretability:

- W1: 80–130 ms
- W2: 130–220 ms
- W3: 220–320 ms
- W4: 320–600 ms
- Later, W5: 600–800 ms was added

The goal was:

> To understand which time windows show face/non-face or emotion/neutral effects.

#### Layer B: xDAWN + Riemannian

For classical ERP decoding:

- xDAWN
- Covariance estimation
- Tangent space projection
- Logistic regression

This replaced a simple SVM because it is more appropriate for ERP decoding.

#### Layer C: Deep Learning

For later stages:

- EEGNet
- EEG-Conformer

However, ML/DL was temporarily postponed so that the neuroscience analysis could first be established properly.

---

## 6. Meeting with the Supervisor

A meeting was held with Prof. Robertas Damaševičius.

### 6.1. First Meeting Topic

The first question was whether working on MELON/LEMON during the secondment would be useful.

The supervisor said:

- Working with this dataset would be useful.
- It would be good to use the dataset as much as possible during the stay in Denmark.
- A conference paper could be an immediate output.
- Later, the conference paper could potentially be extended into a journal version without needing additional access to the data, by expanding the text and including already generated results.
- Authorship constraints were not a major concern for him.

### 6.2. Second Meeting Topic

The second question was about the next main journal paper direction for the PhD:

1. EEG + VR datasets, but without EMG
2. EEG + EMG datasets, but without VR

The supervisor said that the decision depends strongly on dataset availability. Since EEG+VR datasets are often private or limited, the EEG+EMG direction is currently more practical. Therefore, he broadly agreed with focusing on datasets such as DEAP, DENS, and I-DARE.

---

## 7. Clarifying the Actual Dataset: LEMON, Not Full MELON

Later, it became clear that the available data was not the full MELON dataset, but a subset called **LEMON**.

### 7.1. Subjects

Initially, 16 subjects were available:

```text
sub-200, 201, 202, 203, 204, 205, 206, 207,
208, 209, 211, 212, 213, 214, 215, 216
```

Important notes:

- `sub-210` was missing.
- Six additional subjects were expected.
- Therefore, the maximum potential number was 22.
- However, only 13 of the 16 currently available subjects were usable for the full main analysis.

### 7.2. Incomplete Subjects

Three subjects had major problems.

#### sub-204

- Only scalp EEG was available.
- No behavioral file.
- No ear-EEG.
- No physio or eye tracking.

#### sub-207

- Similar to sub-204.
- Only scalp EEG was available.
- A folder named `ses-laab` was found, probably indicating a typo or transfer issue.

#### sub-216

- Ear-EEG was available.
- Physio was available.
- Eye tracking was available.
- But no behavioral emotional events file.
- No scalp EEG.
- No eye-tracking events file.

Therefore, it was excluded from the main ear + scalp + behavioral analysis.

### 7.3. Number of Usable Subjects

Currently:

```text
13 usable subjects
```

If the 6 future subjects are complete:

```text
up to 19 usable subjects
```

---

## 8. Available Modalities in LEMON

For the Emotional Affect paradigm, 11 modality/file types were checked:

- Behavioral events
- Ear EEG
- Scalp EEG
- GSR
- HR / Pleth / SpO2
- Gyroscope / accelerometer
- Raw eye tracking
- Fixations
- Saccades
- Blinks
- Eye-tracking events

### 8.1. Modality Matrix Result

- 13 subjects were complete: 11/11
- sub-204: only 1/11
- sub-207: only 1/11
- sub-216: 8/11, but missing behavioral and scalp data

---

## 9. Signal Structure and Channels

### 9.1. Ear EEG

Initially, we assumed ear-EEG had 9 channels. The audit showed that:

```text
Ear EEG = 11 channels
```

Channels:

```text
Fpz
M1
M2
EL1
EL3
EL4
EL5
ER1
ER2
ER3
ER4
```

Important notes:

- EL2 is missing.
- Fpz is a frontal/shared channel.
- M1/M2 are mastoid channels.
- EL/ER are ear electrodes.

For fairness, two ear montages were defined.

#### ear_full

All 11 channels are included.

#### ear_strict

Fpz is excluded. The channels are:

```text
M1, M2, EL1, EL3, EL4, EL5, ER1, ER2, ER3, ER4
```

### 9.2. Scalp EEG

Scalp EEG included 32 channels:

- 30 EEG
- 2 EOG

The EOG channels were excluded.

Therefore, for analysis:

```text
scalp EEG = 30 EEG channels
```

---

## 10. Event Timing and Synchronization

The behavioral file included three onset columns:

```text
onset
onset_earEEG
estimated_onset_scalpEEG
```

The final decision was:

### For Ear-EEG

Use:

```text
onset_earEEG
```

### For Scalp EEG

Use:

```text
estimated_onset_scalpEEG
```

This was necessary because scalp EEG did not contain optical triggers and only had audio triggers.

Later, it was found that:

```text
estimated_onset_scalpEEG = onset_earEEG + constant offset
```

This means relative timing is accurate and defensible.

---

## 11. Class Distribution

For each subject:

```text
400 epochs
```

because:

```text
20 trials × 20 images
```

### 11.1. Task A: Face vs Non-face

```text
face = 320
non_face = 80
```

This is an 80/20 imbalance.

### 11.2. Task B: Emotional vs Neutral

For face trials:

```text
happy = 80
angry = 80
afraid = 80
neutral = 80
```

Therefore:

```text
emotional = 240
neutral = 80
```

This is a 75/25 imbalance.

### 11.3. Task C: 4-Class Expression

This task is approximately balanced:

```text
happy = 80
angry = 80
afraid = 80
neutral = 80
```

---

## 12. Important Shift: Neuroscience-First Analysis

At one stage, we decided to examine the neural signals before applying ML/DL.

The key question became:

> Do we actually see meaningful neural signals in the data?

This was important because if ERP effects are not visible, any ML/DL model may simply learn noise or artifacts.

Therefore, the current workflow became:

1. Preprocessing
2. ERP analysis
3. Difference waves
4. Window-level summaries
5. Subject-level statistics
6. ML/DL later

---

## 13. Initial Pipeline Design

Several scripts were designed.

### 13.1. `01_manifest.py`

Purpose:

- Check subjects.
- Identify complete subjects.
- Create the manifest.

Output:

```text
output/manifests/subject_manifest.csv
```

Result:

```text
Main subjects (13):
200, 201, 202, 203, 205, 206, 208, 209, 211, 212, 213, 214, 215
```

### 13.2. `02_preprocess_epoch.py`

Purpose:

- Read `.set` files.
- Filter the data.
- Downsample.
- Epoch the data.
- Apply baseline correction.
- Save epochs.

At first, the default artifact rejection caused all epochs to be dropped, producing the error:

```text
Epochs-object is empty
```

For debugging, we used:

```bash
--disable-reject
```

Then preprocessing succeeded.

### 13.3. `03_erp_analysis.py`

Purpose:

- Load epochs.
- Compute ERP window mean amplitudes.
- Generate tables.

Outputs:

```text
reports/tables/window_amplitudes.csv
reports/tables/condition_counts.csv
reports/tables/roi_channel_usage.csv
reports/tables/channel_nan_report.csv
reports/tables/skipped_modality_epochs.csv
```

### 13.4. `04_statistics.py`

Purpose:

- Run initial statistics on window amplitudes.
- Generate:

```text
reports/stats/erp_stats_results.csv
```

---

## 14. NaN Problem and Bad Channels

After the initial run, several NaNs were found in `window_amplitudes.csv`.

Further inspection showed that, for example, in sub-201, TP7 was entirely NaN:

```text
TP7 80400/80400 NaNs
```

This caused problems when computing ROI averages that included TP7.

A channel-wise inspection was then performed, revealing that some channels were all-NaN or very noisy in specific subjects.

---

## 15. Detailed QC: Epoch PTP Scan and Channel PTP Scan

Two quality-control scans were performed.

### 15.1. Epoch PTP Threshold Scan

File:

```text
reports/qc/epoch_ptp_threshold_scan.csv
```

This showed that some subjects had severe artifacts.

Examples:

- sub-205 scalp was very poor.
- sub-206 scalp was very poor.
- sub-209 scalp was very poor.
- sub-212 scalp was very poor.
- sub-213 ear was very poor.
- sub-215 ear was very poor.

### 15.2. Channel PTP Scan

File:

```text
reports/qc/channel_ptp_scan.csv
```

This identified channels that were:

- all-NaN
- high median amplitude
- high p95
- high p99

Examples:

#### sub-201 scalp

```text
CP5, TP7, T7 = all_nan
```

#### sub-201 ear

```text
ER3 = high_p95/high_p99
```

#### sub-213 ear

Almost all ear channels were extremely bad.

#### sub-215 ear

Almost all ear channels were extremely bad.

---

## 16. Creating `qc_decisions.yaml`

Based on QC results, decisions were stored in:

```text
configs/qc_decisions.yaml
```

### 16.1. Excluded Modalities

```yaml
exclude_modality:
  scalp: ['209', '212']
  ear: ['213', '215']
```

This means:

- sub-209 and sub-212 were excluded for scalp analysis.
- sub-213 and sub-215 were excluded for ear analysis.

### 16.2. Bad Channels

Some bad channels were dropped for specific subjects, for example:

```yaml
sub-201:
  scalp: [CP5, TP7, T7]
  ear: [ER3]
```

Then `02_preprocess_epoch.py` was rerun using these QC decisions.

Result:

- Preprocessing succeeded.
- Bad modalities were skipped.
- Bad channels were dropped.

---

## 17. Important Note About ML/DL and Dropped Channels

At this stage, we discussed an important issue:

If ML/DL is performed later, subject-specific channel removal can become problematic because models usually require fixed input dimensions.

Therefore, the decision was:

> For now, ML/DL should be postponed, and the analysis should focus on ERP.

For ERP analysis, subject-specific channel removal is acceptable if ROI means are computed from available channels. However, for ML/DL, this issue must be handled separately later using one of the following strategies:

- Common channel set
- Interpolation
- Masking
- Modality-specific exclusion
- Subject exclusion

---

## 18. ERP Analysis After QC

After applying QC decisions, `03_erp_analysis.py` was rerun successfully.

The output confirmed:

```text
[OK] No NaNs in mean_amplitude.
```

This means the NaN problem was solved.

Also:

- Condition counts were valid.
- Skipped modality reports were generated.
- The effective number of subjects was around 11 per modality/ROI.

### 18.1. Initial Statistical Results

In `erp_stats_results.csv`, some uncorrected effects were observed, especially for:

- Face vs Non-face
- Scalp face_roi
- Scalp late_roi
- Ear_right

However, after FDR correction, strong significance was limited. This is expected given the small sample size of N=11.

Therefore, we decided not to rely only on p-values and moved toward difference-wave analysis.

---

## 19. ERP Overlay Plots

Condition-wise ERP overlay plots were generated.

Initial observations:

- Face vs Non-face was visible in scalp EEG.
- Differences were also visible in ear-EEG.
- Emotional vs Neutral was weaker.
- However, overlay plots were not enough to clearly identify the effects.

Therefore, the next step was:

> Create difference waves.

---

## 20. Difference Waves: `03b_plot_difference_waves.py`

A new script was created:

```text
03b_plot_difference_waves.py
```

Purpose:

Generate difference waves for:

```text
Face - Non-face
Emotional - Neutral
```

for the following modality/ROI combinations.

### Scalp

```text
scalp_main / face_vs_nonface / face_roi
scalp_main / face_vs_nonface / central_roi
scalp_main / face_vs_nonface / late_roi
scalp_main / emotional_vs_neutral / face_roi
```

### Ear

```text
ear_full_main / face_vs_nonface / ear_full
ear_strict_main / face_vs_nonface / ear_strict
ear_full_main / face_vs_nonface / ear_right
ear_full_main / emotional_vs_neutral / ear_right
```

Outputs were saved in:

```text
reports/erp_diff/
```

---

## 21. Interpretation of Initial Difference Waves

### 21.1. Scalp Face − Non-face

In scalp face_roi:

- W1 showed a strong positive effect.
- W2/W3 showed mixed and negative-going effects.
- W4 showed a strong late positivity.

In scalp late_roi:

- W4 was very strong.
- The effect increased toward 600 ms.

### 21.2. Ear Face − Non-face

In ear_full, ear_strict, and ear_right:

- A positive and sustained Face − Non-face effect was visible.
- ear_strict was important because Fpz was removed.
- ear_right appeared to be the strongest ear ROI.

Conclusion:

> Ear-EEG preserves some coarse face/non-face information.

### 21.3. Emotional − Neutral

In both scalp and ear:

- Effects were smaller.
- SEM was large.
- Direction was not stable.
- Strong conclusions could not be made.

Conclusion:

> Emotional − Neutral should currently be treated as exploratory.

---

## 22. Numerical Summary of Difference Waves: `03c_summarize_difference_windows.py`

A new script was created:

```text
03c_summarize_difference_windows.py
```

Purpose:

From files:

```text
reports/erp_diff/*_grand_average.csv
```

compute, for each window:

- mean_difference
- sem_average
- peak_positive
- peak_positive_time_ms
- peak_negative
- peak_negative_time_ms
- abs_peak
- abs_peak_time_ms
- window_area

Output:

```text
reports/erp_diff/difference_window_summary.csv
```

### 22.1. Important Result

The strongest effects were:

- Scalp face_roi W4
- Scalp face_roi W1
- Scalp late_roi W4
- Ear_strict W4
- Ear_right W4

Therefore, W4 was identified as the strongest window.

---

## 23. Concern About the 600 ms Cutoff

Because some of the strongest peaks were close to 600 ms, we asked:

> Does the effect really end around 600 ms, or did it only look that way because the original epoch ended at 600 ms?

To answer this, sensitivity epochs were examined.

---

## 24. Sensitivity Analysis up to 800 ms

A new script was created:

```text
03b_plot_difference_waves_sens.py
```

This used:

```text
scalp_sens
ear_full_sens
ear_strict_sens
```

instead of:

```text
scalp_main
ear_full_main
ear_strict_main
```

Outputs were saved in:

```text
reports/erp_diff_sens/
```

### 24.1. Result of Sensitivity Plots

In scalp EEG:

- The Face − Non-face effect increased until around 500–600 ms.
- After 600 ms, it decreased.
- Around 700–800 ms, it moved toward zero or even became negative in some ROIs.

In ear-EEG:

- ear_strict and ear_right also showed strong effects up to around 500–600 ms.
- After 600 ms, the effect decreased.

This confirmed:

> W4 = 320–600 ms is an appropriate window, and the effect decreases after 600 ms.

---

## 25. Adding W5: 600–800 ms

To quantify the post-W4 decrease, a new window was added:

```text
W5: 600–800 ms
```

A patch script was created:

```text
00_add_w5_window.py
```

This added the following to `config.yaml`:

```yaml
erp_windows_ms:
  W1: [80, 130]
  W2: [130, 220]
  W3: [220, 320]
  W4: [320, 600]
  W5: [600, 800]
```

Then the summary was rerun on sensitivity outputs, producing:

```text
reports/erp_diff_sens/difference_window_summary_w5.csv
```

---

## 26. W5 Result

### 26.1. Comparison Between W4 and W5

For Face − Non-face:

| ROI | W4 mean | W5 mean | Interpretation |
|---|---:|---:|---|
| scalp face_roi | 2.196 | 0.643 | Clear decrease |
| scalp late_roi | 2.079 | 0.635 | Clear decrease |
| scalp central_roi | 1.068 | 0.490 | Moderate decrease |
| ear_strict | 1.804 | 0.393 | Strong decrease |
| ear_right | 1.659 | 0.223 | Strong decrease |
| ear_full | 0.635 | 0.474 | Milder decrease |

Conclusion:

> The main Face − Non-face effect is concentrated in W4 and clearly decreases after 600 ms.

### 26.2. Note About W5 Peaks

In some cases, the W5 peak occurred exactly at 600 ms, meaning the very beginning of W5.

This means:

> W5 does not represent a separate strong effect; rather, it captures the tail end of W4, followed by a decline.

Therefore, in writing, we should say:

> The effect peaked around the end of W4 and declined during W5.

---

## 27. Subject-Level Difference Statistics

After the grand-average difference-wave summaries, a crucial methodological step was added:

```text
03d_subject_level_difference_stats.py
```

The reason for this step was that grand-average summaries are descriptive. For inferential claims, we needed to calculate condition differences at the **subject level**.

### 27.1. Purpose

For each:

```text
subject × modality × ROI × contrast × window
```

the script computes:

```text
mean(condition A) − mean(condition B)
```

Then it performs:

- one-sample t-test against zero
- Wilcoxon signed-rank test
- effect size estimation
- FDR correction
- W4 vs W5 descriptive and paired interpretation

### 27.2. Main Subject-Level Output Files

The main run produced:

```text
reports/stats/subject_level_window_differences.csv
reports/stats/subject_level_difference_stats.csv
reports/stats/subject_level_difference_stats_key_results.csv
reports/stats/w4_w5_interpretation_summary.csv
reports/figures/subject_level_face_nonface_w4.png
reports/figures/w4_w5_interpretation_summary.png
```

The sensitivity run produced:

```text
reports/stats_sens/subject_level_window_differences.csv
reports/stats_sens/subject_level_difference_stats.csv
reports/stats_sens/subject_level_difference_stats_key_results.csv
reports/stats_sens/w4_w5_interpretation_summary.csv
reports/figures_sens/subject_level_face_nonface_w4.png
reports/figures_sens/w4_w5_interpretation_summary.png
```

### 27.3. Why the Sensitivity Version Was Necessary

Initially, W5 was summarized descriptively from the grand-average sensitivity difference waves. However, for the final analysis, W5 also needed to be included at subject level.

Therefore, a new script was added:

```text
03_erp_analysis_sens.py
```

This script extracted subject-level window amplitudes for:

```text
scalp_sens
ear_full_sens
ear_strict_sens
```

including:

```text
W5 = 600–800 ms
```

It generated:

```text
reports/tables/window_amplitudes_sens.csv
reports/tables/condition_counts_sens.csv
reports/tables/roi_channel_usage_sens.csv
reports/tables/channel_nan_report_sens.csv
reports/tables/skipped_modality_epochs_sens.csv
```

The subject-level statistics were then rerun using:

```bash
python scripts/03d_subject_level_difference_stats.py --config configs/config.yaml --window-table reports/tables/window_amplitudes_sens.csv --condition-counts reports/tables/condition_counts_sens.csv --w5-summary reports/erp_diff_sens/difference_window_summary_w5.csv --out-dir reports/stats_sens --fig-dir reports/figures_sens
```

### 27.4. Key Subject-Level Findings

The strongest subject-level trends were:

| Modality | Contrast | ROI | Window | Mean difference | Effect size dz | p-value | Positive subjects |
|---|---|---|---|---:|---:|---:|---:|
| scalp_sens | Face − Non-face | late_roi | W4 | 2.079 | 1.39 | < .001 | 100% |
| scalp_sens | Face − Non-face | face_roi | W1 | 2.080 | 1.10 | .005 | 90.9% |
| scalp_sens | Face − Non-face | central_roi | W3 | 1.390 | 0.97 | .009 | 81.8% |
| ear_full_sens | Face − Non-face | ear_right | W1 | 0.820 | 0.94 | .011 | 81.8% |
| ear_strict_sens | Face − Non-face | ear_right | W1 | 0.820 | 0.94 | .011 | 81.8% |
| scalp_sens | Face − Non-face | central_roi | W4 | 1.068 | 0.90 | .014 | 81.8% |
| ear_full_sens | Face − Non-face | ear_right | W4 | 1.659 | 0.86 | .017 | 81.8% |
| ear_strict_sens | Face − Non-face | ear_right | W4 | 1.659 | 0.86 | .017 | 81.8% |
| ear_strict_sens | Face − Non-face | ear_strict | W4 | 1.804 | 0.83 | .020 | 72.7% |

The main interpretation is:

> The scalp late ROI shows the clearest and most consistent W4 Face − Non-face effect. Ear-EEG also shows positive W4 effects, especially in right-ear and strict-ear configurations, although the effects are smaller and more variable than scalp EEG.

### 27.5. W4-to-W5 Subject-Level Change

The W4-to-W5 comparison showed that the late Face − Non-face effect decreases after 600 ms.

The clearest paired decreases were:

| ROI | W4 vs W5 result |
|---|---:|
| Ear strict | p = .028 |
| Ear right | p = .010 |

This supports the interpretation that:

> The late ear-EEG Face − Non-face effect is concentrated mainly within W4 = 320–600 ms and declines during W5 = 600–800 ms.

---

## 28. Final ERP Figures

After subject-level statistics were completed, final figures were generated in two stages.

### 28.1. First Final Figure Script

The first final figure script was:

```text
03e_make_final_erp_figures.py
```

It produced:

```text
reports/final_figures/figure_01_face_nonface_difference_waves.png
reports/final_figures/figure_02_subject_level_w4_boxplot.png
reports/final_figures/figure_03_w4_w5_summary.png
reports/final_figures/figure_04_w4_w5_paired_subjects.png
reports/final_figures/final_figure_source_values.csv
reports/final_figures/final_w4_w5_paired_stats.csv
reports/final_figures/README.md
```

These figures were useful but needed patching for clearer reporting.

### 28.2. Publication-Ready Figure Script

A patched and cleaner final script was then created:

```text
03f_make_publication_erp_figures.py
```

This script produced publication/report-ready figures in:

```text
reports/final_figures_v2/
```

Outputs:

```text
figure_01_difference_waves_v2.png
figure_02_w4_subject_boxplot_compact_v2.png
figure_02b_w4_subject_boxplot_all_v2.png
figure_03_w4_w5_summary_v2.png
figure_04_w4_w5_paired_subjects_compact_v2.png
figure_05_w4_minus_w5_boxplot_v2.png
publication_figure_stats_summary.csv
publication_w4_w5_paired_stats.csv
publication_w4_w5_paired_subject_values.csv
README.md
```

### 28.3. Recommended Figures for the Main Report

The most important figures for the main report are:

```text
figure_01_difference_waves_v2.png
figure_02_w4_subject_boxplot_compact_v2.png
figure_03_w4_w5_summary_v2.png
figure_05_w4_minus_w5_boxplot_v2.png
```

The following figures are better suited for supplementary material:

```text
figure_02b_w4_subject_boxplot_all_v2.png
figure_04_w4_w5_paired_subjects_compact_v2.png
```

### 28.4. Interpretation of Final Figures

#### Figure 1: Difference Waves

This figure shows the Face − Non-face ERP difference waves for:

- Scalp late ROI
- Scalp face ROI
- Ear strict montage
- Ear right ROI

The key message is:

> The late Face − Non-face effect is strongest in scalp late ROI and is also visible in ear-EEG, especially in strict-ear and right-ear ROIs.

#### Figure 2: Subject-Level W4 Boxplot

This figure shows subject-level W4 differences for compact key ROIs.

It makes clear that:

- Scalp late ROI has the strongest and most consistent W4 effect.
- Ear strict and ear right show positive W4 differences.
- Scalp face ROI is visually large but more variable.

#### Figure 3: W4 versus W5 Summary

This figure compares W4 and W5 means.

It shows that:

> W4 is stronger than W5 in the key scalp and ear ROIs.

#### Figure 5: W4-minus-W5 Boxplot

This figure directly summarizes the paired W4 − W5 decrease.

It is useful because it shows:

- W4-to-W5 decrease is clearest in ear strict and ear right.
- This supports the idea that the ear-EEG effect is temporally concentrated in W4.

---

## 29. Current Scientific Interpretation

At this point, the neuroscience-first analysis supports the following interpretation.

### 27.1. Main Finding

**Face − Non-face** is the strongest contrast.

In scalp EEG:

- A strong W1 effect is visible.
- A strong W4 effect is visible.
- Late positivity appears in the 320–600 ms range.

In ear-EEG:

- Face − Non-face effects are visible in ear_strict and ear_right.
- The strongest ear effect is also in W4.
- This suggests that ear-EEG preserves part of the face-related information.

### 27.2. Secondary Finding

**Emotional − Neutral** is weaker, noisier, and exploratory.

Therefore, the dataset is not ideal for strong emotion-specific ERP claims, but it is suitable for face-related stimulus decoding.

### 27.3. Defensible Claim

A defensible claim is:

> The LEMON Emotional Affect paradigm shows robust Face − Non-face ERP differences in scalp EEG and partially preserved late face-related differences in ear-EEG, particularly in strict-ear and right-ear ROIs. Emotion-specific differences were weaker and less stable.

### 27.4. Claims That Are Not Currently Defensible

At this stage, we should not say:

> Ear-EEG detects emotions.

or:

> Ear-EEG preserves the canonical N170.

because:

- The canonical N170 is not clearly visible.
- Emotion-specific effects are weak.
- The task is memory-confounded.

---

## 30. Important Files and Outputs

### 28.1. Config

```text
configs/config.yaml
configs/config.yaml.bak_before_w5
configs/qc_decisions.yaml
```

### 28.2. Manifest

```text
output/manifests/subject_manifest.csv
```

### 28.3. Processed Epochs

```text
output/processed/sub-XXX/
```

Including:

- scalp_main
- scalp_sens
- ear_full_main
- ear_full_sens
- ear_strict_main
- ear_strict_sens
- metadata

### 28.4. QC

```text
reports/qc/preprocess_qc_summary.csv
reports/qc/epoch_ptp_threshold_scan.csv
reports/qc/channel_ptp_scan.csv
```

### 28.5. ERP Tables

```text
reports/tables/window_amplitudes.csv
reports/tables/condition_counts.csv
reports/tables/roi_channel_usage.csv
reports/tables/channel_nan_report.csv
reports/tables/skipped_modality_epochs.csv
```

### 30.6. Statistics

```text
reports/stats/erp_stats_results.csv
reports/stats/subject_level_window_differences.csv
reports/stats/subject_level_difference_stats.csv
reports/stats/subject_level_difference_stats_key_results.csv
reports/stats/w4_w5_interpretation_summary.csv
```

### 30.7. Sensitivity Statistics

```text
reports/stats_sens/subject_level_window_differences.csv
reports/stats_sens/subject_level_difference_stats.csv
reports/stats_sens/subject_level_difference_stats_key_results.csv
reports/stats_sens/w4_w5_interpretation_summary.csv
```

### 30.8. Main Difference Waves

```text
reports/erp_diff/
```

### 30.9. Sensitivity Difference Waves

```text
reports/erp_diff_sens/
```

### 30.10. W5 Summary

```text
reports/erp_diff_sens/difference_window_summary_w5.csv
```

### 30.11. Final Figures

```text
reports/final_figures/
reports/final_figures_v2/
```

Recommended main report figures:

```text
reports/final_figures_v2/figure_01_difference_waves_v2.png
reports/final_figures_v2/figure_02_w4_subject_boxplot_compact_v2.png
reports/final_figures_v2/figure_03_w4_w5_summary_v2.png
reports/final_figures_v2/figure_05_w4_minus_w5_boxplot_v2.png
```

---

## 31. Key Decisions Made During the Process

### Decision 1

Do not present MELON/LEMON as an emotion recognition dataset.

### Decision 2

Shift the focus from emotion recognition to face-related stimulus decoding.

### Decision 3

Temporarily postpone ML/DL and start with neuroscience-first analysis.

### Decision 4

Subject-specific channel removal is acceptable for ERP analysis.

### Decision 5

For future ML/DL, the fixed-channel issue must be handled separately.

### Decision 6

Face − Non-face became the main contrast.

### Decision 7

Emotional − Neutral became a secondary/exploratory contrast.

### Decision 8

W4 = 320–600 ms became the strongest and most interpretable late window.

### Decision 9

W5 = 600–800 ms was added to show that the effect decreases after 600 ms.

### Decision 10

Subject-level statistics were added because grand-average difference waves are descriptive and cannot support inferential claims alone.

### Decision 11

Sensitivity ERP window extraction was added so that W5 could be tested at subject level rather than only summarized descriptively.

### Decision 12

The final report should use the patched publication-ready figures from:

```text
reports/final_figures_v2/
```

rather than the earlier draft figures in:

```text
reports/final_figures/
```

---

## 32. Current Project Status

We now have a defensible analysis path:

1. The dataset has been audited.
2. Usable subjects have been identified.
3. Incomplete modalities have been identified.
4. Bad channels have been detected and removed.
5. QC decisions have been applied.
6. ERP analysis runs without NaNs.
7. Difference waves have been generated.
8. Sensitivity analysis up to 800 ms has been performed.
9. W5 has been added.
10. W4 has been confirmed as the strongest window.
11. Subject-level difference statistics have been computed.
12. W4-to-W5 subject-level comparisons have been performed.
13. Final ERP figures have been generated.
14. Publication/report-ready patched figures have been generated.
15. The scientific narrative is now clear and report-ready.

---

## 33. Logical Next Step

The previously planned next step was:

```text
03d_subject_level_difference_stats.py
```

This step has now been completed.

The logical next step is now **report/manuscript consolidation**:

1. Update the LaTeX/Overleaf report using the final figures from:

```text
reports/final_figures_v2/
```

2. Use the final subject-level tables from:

```text
reports/stats_sens/
```

3. Write the Results section around the following hierarchy:

```text
A. QC and usable data
B. Face − Non-face difference waves
C. Subject-level W4 effects
D. W4 versus W5 temporal concentration
E. Emotional − Neutral as exploratory
F. Interpretation: partial preservation of late face-related information in ear-EEG
```

4. Keep the ML/DL pipeline postponed until the ERP findings are written clearly.

### 33.1. Optional Future Analyses

The following analyses may be useful but are not required before writing the current ERP report:

#### Topography

Useful for scalp EEG only. It could show where the Face − Non-face effect is strongest across the scalp.

However, it is not essential for the current ear-vs-scalp ERP narrative.

#### Time-frequency analysis

Useful if we want to examine theta/alpha/beta changes.

However, it would expand the scope considerably and is not necessary before the current ERP report.

#### ML/DL

This should come after the ERP report. Before ML/DL, channel consistency must be solved carefully because subject-specific bad-channel removal is acceptable for ERP analysis but problematic for fixed-input machine learning.

---

## 34. Final Summary So Far

We started with a broad question:

> Is MELON useful for emotion recognition?

Through documentation review, dataset audit, supervisor discussion, QC, ERP analysis, and difference-wave analysis, we arrived at a more precise and defensible project:

> Investigating whether ear-EEG in the LEMON subset preserves ERP differences related to face/non-face stimulus processing compared with scalp EEG.

The main finding so far is:

> Face − Non-face differences are strong in scalp EEG and are also visible in ear-EEG, especially in the strict-ear and right-ear ROIs, as a sustained late positivity in W4. In contrast, Emotional − Neutral effects are weaker and less stable.

The subject-level analysis strengthens this conclusion:

> The scalp late ROI shows the most robust W4 Face − Non-face effect, while ear strict and ear right ROIs show positive W4 effects with medium-to-large effect sizes. W4-to-W5 comparisons indicate that the late ear-EEG effect decreases after 600 ms.

Therefore, the paper should make a cautious but valuable claim:

> Ear-EEG may preserve coarse face-related neural information, especially late Face − Non-face ERP differences, but it does not yet provide strong evidence for robust emotion-specific information in this paradigm.

The current analysis is now ready to be written into a supervisor progress report and then shaped into the Results section of a conference-paper-style manuscript.


---

**Last updated:** 2026-04-29 12:35  
**Update note:** Added subject-level statistics, sensitivity W5 subject-level extraction, W4/W5 comparisons, and publication-ready final figures.
