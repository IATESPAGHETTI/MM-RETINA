# Data audit — what the three projects' data can and cannot support

Scope: Kartik's RETINA (diabetes / vessel analysis), the Research project
(Sankara Nethralaya glaucoma OCT + clinical Excel, the PDF paper) and
MM-RETINA (GAMMA multimodal). All numbers below were computed from the files
on disk, not copied from the paper.

## 1. Inventory

| Source | Contents | Labels | Patient ID? |
|---|---|---|---|
| `Glaucoma _Research/` | 100 Control + 203 Glaucoma optic-nerve-head OCT B-scans (844x563 JPG) + `Glaucoma_Excel.xlsx` (203 glaucoma rows, 100 control rows, 37 columns) | Control 100 / Mild 118 / Moderate 47 / Severe 38 | No (only `SI No`) |
| `data/.../Glaucoma AI Project 1/Fundus image/` | 107 colour fundus photos (2588x1958) | Mild 83 / Moderate 13 / Severe 11 | No (burned-in text overlay only) |
| `data/.../Glaucoma Disc photos/` | 107 images | none | No |
| `data/.../HVF/` | 168 DICOM visual-field reports | Mild 109 / Moderate 25 / Severe 34 | Yes (DICOM `patient_id`, 90 patients) |
| `data/.../RNFL and GCC data/Glaucoma AI.xlsx` | 171 rows, RNFL + GCC thickness | Mild 114 / Moderate 25 / Severe 32 | No |
| GAMMA (MM-RETINA) | 300 paired fundus + 256-slice OCT volumes | Normal / Early / Progressive | Yes |
| RETINA/DIPP | LES-AV (22 images), segmentation set, 2 HbA1c Keras models, U-Net (DRIVE) | HbA1c bins / vessel masks | n/a |

## 2. Findings

1. **"Disc photos" is a duplicate of "Fundus image".** All 107 files are
   byte-identical (MD5) to the 107 fundus images, under different file names.
   They are one dataset, not two. Counting them separately would double-count.
2. **The Research Excel is the master table.** 82 of the 171 rows in
   `Glaucoma AI.xlsx` match a Research-Excel row on *all 12* RNFL/GCC
   measurements exactly (a column-shuffled control gives 0 near-matches).
   On those 82 rows eye agrees 100%, sex 100%, severity 96%, and age is +1/+2
   years (the workbook was exported later). So roughly half the "new" RNFL/GCC
   data is the same eyes again, and the other 89 rows have no images.
3. **HVF DICOMs link to the Research eyes, partially.** Matching on MD value +
   eye gives 101/168 files, with 100% severity agreement. Adding age within 2 years
   gives **67 files that map to exactly one Research eye**. HVF therefore adds
   PSD / VFI / reliability indices for ~67 eyes; it is not an independent cohort.
4. **Severity is a function of HVF MD.** The Research Excel severity equals
   `Mild if MD > -6 dB, Moderate if -12 < MD <= -6, Severe if MD <= -12` with
   **100% agreement on all 203 glaucoma eyes**. Therefore any model that takes
   HVF MD as an input "predicts" severity by reading its own definition. The
   paper lists HVF MD among its top features (Tables III/IX); those accuracies
   (91-93%) are circular and are not evidence of diagnostic skill.
5. **Missingness leaks the label.** Pachymetry is missing for 33% of glaucoma
   but 51% of control rows; CFT for 26% vs 49%, with different means.
   Both columns are excluded from the models here.
6. **No patient IDs in the Research data.** OD/OS of one patient are adjacent
   rows with equal age and sex. Patient groups are reconstructed with that rule
   and every evaluation splits by group so the two eyes never straddle
   train/test. The paper describes augmenting 303 scans to 1,818 and then splitting
   70/20/10. Tested with the paper's own architecture (`ml/glaucoma/run_paper.py leaky`):
   a random image-level split of the augmented set gives 81.3% test accuracy with 100% of test
   images having an augmented copy of the same scan in training; a patient-grouped split of the
   same data gives 52.2%. This shows the protocol can inflate accuracy that much; it does not
   establish what the paper actually did (its split is not described). One seed, ~180 test images.
7. **Fundus photos carry burned-in text** in the top-left corner (patient
   identifiers). They are not used for record linkage here, and the product UI
   must not display them unmasked.
8. **Class imbalance:** Moderate (47) and Severe (38) eyes are few; per-class
   recall on them has wide uncertainty. Reported with that caveat.

## 3. What each dataset is used for

| Use | Data | Why |
|---|---|---|
| OCT severity classifier | Research 303 B-scans | Only labelled OCT images |
| Clinical-feature model (honest) | Research Excel without HVF MD, Pachy, CFT | Removes circular and missing-pattern features |
| Rule-based staging from MD | HVF MD | It is a rule, so it is presented as a rule, not as AI |
| Multimodal OCT + clinical late fusion | Research 303 eyes | The only place image + tabular exist for the same eye |
| GAMMA fundus + OCT volume model | existing MM-RETINA checkpoints | Already trained; kept as the multimodal demo |
| External sanity check | Sankara fundus (glaucoma only) | No controls and no patient link, so it cannot train or fully validate |
| Diabetes module | Kartik's models, unchanged | Different disease; integrated as its own module |

Not done on purpose: matching the Sankara fundus photos to Research eyes via
the burned-in text (identifiers), and fusing HVF-DICOM + fundus without a
verified patient link.
