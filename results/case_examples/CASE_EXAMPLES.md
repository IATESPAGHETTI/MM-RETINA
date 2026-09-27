# MM-RETINA Classification Case Examples

All examples below are pulled from already-saved, real held-out cross-validation predictions — none are re-run or hand-picked training examples. No explainability method was run, so no visual region is claimed to have caused any prediction.

## GAMMA (frozen EXP-05/06 benchmark — EfficientNet-B0 fundus + ResNet18 OCT)

### Example G-01 — Normal correctly detected

- True: **Normal**
- Predicted: **Normal**
- Confidence: 89.6%
- Fold: 4 (held-out validation fold, `results/cv_fusion_effnetb0_v1/fusion/fold4/predictions.csv`)
- Full probabilities: normal=0.896, early=0.065, progressive=0.039
- Fundus: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0001\0001.jpg`
- OCT: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0001\0001`
- Panel: `results\case_examples\images\G-01_0001.png`

### Example G-02 — Early correctly detected

- True: **Early**
- Predicted: **Early**
- Confidence: 78.5%
- Fold: 1 (held-out validation fold, `results/cv_fusion_effnetb0_v1/fusion/fold1/predictions.csv`)
- Full probabilities: normal=0.055, early=0.785, progressive=0.160
- Fundus: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0097\0097.jpg`
- OCT: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0097\0097`
- Panel: `results\case_examples\images\G-02_0097.png`

### Example G-03 — Progressive correctly detected

- True: **Progressive**
- Predicted: **Progressive**
- Confidence: 79.0%
- Fold: 3 (held-out validation fold, `results/cv_fusion_effnetb0_v1/fusion/fold3/predictions.csv`)
- Full probabilities: normal=0.059, early=0.151, progressive=0.790
- Fundus: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0081\0081.jpg`
- OCT: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0081\0081`
- Panel: `results\case_examples\images\G-03_0081.png`

### Example G-04 — Informative misclassification (Early confused with Normal, near-tied confidence)

- True: **Early**
- Predicted: **Normal**
- Confidence: 48.0%
- Fold: 0 (held-out validation fold, `results/cv_fusion_effnetb0_v1/fusion/fold0/predictions.csv`)
- Full probabilities: normal=0.480, early=0.477, progressive=0.044
- Fundus: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0017\0017.jpg`
- OCT: `C:\Users\ASUS\Downloads\prj4\dataset\GAMMA\grading\Glaucoma_grading\training\multi-modality_images\0017\0017`
- Panel: `results\case_examples\images\G-04_0017.png`

## HVF (eye-level, patient-grouped CV; Random Forest model)

### Example H-C01-01 — Mild correctly detected

- **C01 — severity-proxy features included (md_db/psd_db/vfi_pct)**
- Real patient ID: `6023839`  ·  Eye: R  ·  Source file: `hvf_and)rnfl_gcc\HVF\Mild\102.dcm`
- True severity: **Mild**
- Predicted severity: **Mild**
- Model probability (predicted class): 99.9%
- Fold: 3 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: Yes

### Example H-C01-02 — Moderate correctly detected

- **C01 — severity-proxy features included (md_db/psd_db/vfi_pct)**
- Real patient ID: `2506246`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Moderate\12.dcm`
- True severity: **Moderate**
- Predicted severity: **Moderate**
- Model probability (predicted class): 86.1%
- Fold: 0 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: Yes

### Example H-C01-03 — Severe correctly detected

- **C01 — severity-proxy features included (md_db/psd_db/vfi_pct)**
- Real patient ID: `1035757`  ·  Eye: R  ·  Source file: `hvf_and)rnfl_gcc\HVF\Severe\9.dcm`
- True severity: **Severe**
- Predicted severity: **Severe**
- Model probability (predicted class): 96.6%
- Fold: 1 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: Yes

### Example H-C01-04 — Adjacent-severity confusion (Mild predicted as Moderate)

- **C01 — severity-proxy features included (md_db/psd_db/vfi_pct)**
- Real patient ID: `1074658`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Mild\16.dcm`
- True severity: **Mild**
- Predicted severity: **Moderate**
- Model probability (predicted class): 49.0%
- Fold: 2 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: Yes

### Example H-C01-05 — Adjacent-severity confusion (Moderate predicted as Severe)

- **C01 — severity-proxy features included (md_db/psd_db/vfi_pct)**
- Real patient ID: `3059262`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Moderate\19.dcm`
- True severity: **Moderate**
- Predicted severity: **Severe**
- Model probability (predicted class): 48.4%
- Fold: 4 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: Yes

### Example H-C01b-01 — Mild correctly detected

- **C01b — MD/PSD/VFI removed**
- Real patient ID: `3499303`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Mild\72.dcm`
- True severity: **Mild**
- Predicted severity: **Mild**
- Model probability (predicted class): 81.1%
- Fold: 3 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: No

### Example H-C01b-02 — Moderate correctly detected

- **C01b — MD/PSD/VFI removed**
- Real patient ID: `2531438`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Moderate\13.dcm`
- True severity: **Moderate**
- Predicted severity: **Moderate**
- Model probability (predicted class): 45.2%
- Fold: 2 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: No

### Example H-C01b-03 — Severe correctly detected

- **C01b — MD/PSD/VFI removed**
- Real patient ID: `3059051`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Severe\27.dcm`
- True severity: **Severe**
- Predicted severity: **Severe**
- Model probability (predicted class): 64.7%
- Fold: 1 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: No

### Example H-C01b-04 — Adjacent-severity confusion (Mild predicted as Moderate)

- **C01b — MD/PSD/VFI removed**
- Real patient ID: `6018823`  ·  Eye: R  ·  Source file: `hvf_and)rnfl_gcc\HVF\Mild\98.dcm`
- True severity: **Mild**
- Predicted severity: **Moderate**
- Model probability (predicted class): 43.4%
- Fold: 0 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: No

### Example H-C01b-05 — Adjacent-severity confusion (Moderate predicted as Severe)

- **C01b — MD/PSD/VFI removed**
- Real patient ID: `2506246`  ·  Eye: L  ·  Source file: `hvf_and)rnfl_gcc\HVF\Moderate\12.dcm`
- True severity: **Moderate**
- Predicted severity: **Severe**
- Model probability (predicted class): 38.4%
- Fold: 0 (patient-grouped held-out validation fold)
- MD/PSD/VFI used: No

## Data-quality example

### Patient 1028746 — asymmetric eye severity

- Eye R: true=mild, predicted=mild, fold=2 (`hvf_and)rnfl_gcc\HVF\Mild\10.dcm`)
- Eye L: true=severe, predicted=severe, fold=2 (`hvf_and)rnfl_gcc\HVF\Severe\8.dcm`)

Both eyes of this real patient were graded on the same study date (2024-03-05), and GroupKFold placed both eyes in the fold shown above — confirmed no cross-fold leakage of this patient.

**Right eye: Mild. Left eye: Severe. Same study date.**

Why this matters: this is real evidence that glaucoma severity in this cohort is an eye-level property, not a patient-level one — a model or report that collapsed this patient to a single severity label would be wrong for at least one of their two eyes by construction, regardless of how accurate the model is.
