# Vision slides — "Where this goes next" (3 slides)

_Draft 2026-11-21. These are **vision** slides. Only slide 2 has a number behind it, and that number is preliminary (see caveat). Say "research prototype, not a medical device" on every one._

---

## Slide 1 — One platform, several eye diseases

**Headline:** MM-RETINA started as glaucoma grading and grew into a retinal screening workspace.

- Glaucoma module: fundus photo + OCT scan → Normal / Early / Progressive (MM-RETINA), plus an OCT/clinical-feature study from the Sankara cohort.
- Diabetes module (from the merged RETINA project): vessel analysis, fractal dimension, an *experimental* HbA1c estimate.
- Same app, same API, same honest labelling of what each model can and cannot do.

**Say out loud:** the diabetes models shipped with no validation. On their 22 reference images the HbA1c output was non-informative, so the app labels it experimental. We integrated it; we did not validate it.

---

## Slide 2 — Triage: cheap screening first, scan only when unsure

**Headline:** In a community clinic a fundus photo is cheap; an OCT scan is not. Screen with the photo, and send only uncertain eyes for OCT.

**How it works (rule, not a trained system):**
fundus model confident → answer from the photo alone; not confident → "send for OCT", and the fundus+OCT model decides.

**Evidence (preliminary; `results/nested_cv_v1/triage_analysis.json`, chart `triage_curve.png`):**
- Accuracy on 100 patients, out-of-fold, one training seed so far: fundus-only 0.73, fusion-for-everyone 0.76.
- Sending about a quarter of eyes for OCT (confidence cut-off 0.50) gave 0.76, the same as sending everyone.
- **Caveat to state:** the 95% intervals (about 0.64–0.84) overlap heavily, so this shows triage *does not obviously lose accuracy*, not that it wins. The cut-off was swept, not tuned or validated. The seed-42-only result will be redone with all three seeds.
- **Honest side finding:** on this seed, fundus-only caught more Early cases (0.54) than fusion (0.42). OCT may not help the Early stage here. Do not claim OCT improves early detection.

**Do not say:** "saves X% of OCT scans in practice." This is a simulation on 100 research patients.

---

## Slide 3 — Privacy-preserving training (federated learning)

**Headline:** More hospitals' data would help, and patient images should not leave the hospital.

- Idea: each hospital trains locally and shares only model updates, not images. A central server combines them.
- Why it fits this project: our biggest limit is data (100 labelled patients; 26 Early cases). Other clinics have more, but cannot hand over scans.
- **Status: idea only.** Nothing was built or tested. Needs real partner hospitals, ethics approval, and compatible scanners and labels (our own data already showed how label definitions differ between cohorts).

---

## Likely panel questions (short answers)

- *"Is triage proven?"* No. It is a simulation on 100 patients with wide intervals. It motivates a proper study.
- *"Why not just use OCT for everyone?"* Cost and access. We tested whether the fundus photo alone gets close; on our data it nearly does, with large uncertainty.
- *"Does the diabetes part work?"* It runs; it is not validated. We say so in the app.
- *"Is anything here clinical?"* No. Research prototype, not a medical device.
