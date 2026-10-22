# Round 2: what actually improves the glaucoma models?

All runs: Research cohort (303 eyes, 162 patients), patient-grouped 5-fold CV, seeds 42/43/44,
fixed epoch budgets, nothing selected on a test fold. Scripts: `ml/glaucoma/explore.py`,
`triage.py`, `ml/gamma_external.py`. Raw results: `ml/results/explore/`.

## Result: no change in model design beats the noise

| Idea | Balanced accuracy (4-class) | vs baseline |
|---|---|---|
| **Clinical baseline** (random forest, structural features) | 67.7% ± 1.4 | |
| Clinical ensemble (logreg + RF + HGB averaged) | 68.0% ± 1.0 | +0.3, noise |
| Hierarchical (detect, then stage) | 67.7% ± 1.4 | 0.0. Better at spotting controls (93% vs 84% recall), worse at Mild (55% vs 68%) |
| Early fusion: frozen-OCT PCA features added to clinical features (best config) | 67.2% | −0.5, noise (logistic head: worse, 61–67%) |
| **OCT baseline** (ResNet18) | 44.9% ± 2.3 | |
| + disc crop | 46.1% ± 2.6 | +1.2, noise |
| + ordinal loss | 44.6% ± 2.3 | −0.3 |
| + auxiliary RNFL/GCC regression head | 43.7% ± 1.7 | −1.2 |
| crop + ordinal + auxiliary | 44.6% ± 1.6 (AUC 0.80 vs 0.77) | AUC +0.03 is the only visible gain |
| Paper architecture (U-Net + InceptionV3, 512 px, tuned) | 47.2% (1 seed) | +2.3, within noise |

Conclusion: the ceiling is the data (one B-scan per eye, 303 eyes, 47 Moderate, 38 Severe), not the model.

## What does help: knowing when not to answer

Clinical random forest, ranked by its own confidence (patient-grouped out-of-fold predictions):

| Cases answered | Accuracy | Balanced accuracy |
|---|---|---|
| 100% | 70.0% | 67.7% |
| 80% (defer the least confident fifth) | 76.3% | 70.6% |
| 60% | 85.7% | 73.6% |

Deferred eyes would go to a visual-field test. Sensitivity for glaucoma at 90% specificity is 88.5%.
This is the only change that moves the headline number, and it is honest because it states the coverage.

**Built into the app** (`ml/glaucoma/make_defer.py`, `backend/services/defer_service.py`): cut-offs are the 20th percentile of out-of-fold confidence, pooled over 3 seeds (clinical 0.532, fused 0.488, OCT 0.396). Pooled accuracy when answered: clinical 76.3%, fused 77.6%, OCT-only 52.0% (so OCT-only is always flagged as not dependable). Deferred eyes were right 44.5% / 41.2% / 36.8% of the time.

## External check: GAMMA fundus model on Sankara fundus photos (107, glaucoma only)

Labels mapped exactly (GAMMA and Sankara grade from the same MD cut-offs): Mild = early, Moderate/Severe = progressive.
Text outside the retinal field was masked before inference.

- 3-class accuracy 70.1%, but **always answering "early" scores 77.6%** (83/107 are Mild), so the model is no better than the class prior here.
- It predicted "early" for 91 of 107 eyes; only 4 of 24 progressive eyes were recognised. AUC progressive-vs-early 0.64.
- Limits: single-split demo checkpoint, only two classes present, 107 eyes. It says the model does not carry over cleanly to a different camera and hospital; it does not say the GAMMA cross-validation numbers are wrong.
