# EXPERIMENTS.md

Log of every actual training/evaluation run. Never delete entries, even
failed ones — a failed run is still real information.

---

## smoke-test-1

- **Date:** 2026-09-17
- **Git commit:** bbda339 (before this session's training-pipeline commit)
- **Split:** dataset/splits/gamma_split_v1.json (seed=42)
- **Architecture:** GammaMultimodalModel, modality=fusion
- **Encoders:** resnet18 / resnet18 (fundus / OCT), ImageNet-pretrained
- **Image resolution:** 128x128
- **OCT slice count/sampling:** 4, evenly spaced from 256
- **Batch size:** 2
- **Optimizer:** AdamW, lr=1e-4
- **Loss:** CrossEntropyLoss (unweighted, smoke test only)
- **Augmentation:** train-mode fundus+OCT augmentation active
- **Epochs:** 1 batch only (not a training run)
- **Best validation epoch:** n/a
- **Test metrics:** n/a — this is a pipeline sanity check, not a trained model
- **Checkpoint path:** none saved
- **Notes:** Real forward+backward pass on real samples (ids 0013, 0061).
  loss=1.1517, peak CUDA memory 472MB. PASSED. Also verified
  modality=fundus (loss=0.953, 237MB) and modality=oct (loss=1.107, 242MB)
  smoke-test independently. Purpose was to catch shape/dtype/device bugs
  before spending real training time — it did catch one (see fusion_run1
  prerequisite note: gamma_loader relative-path bug, fixed before this run).

---

## fusion_run1

- **Date:** 2026-09-17
- **Git commit:** bbda339 (training/ pipeline added same session, not yet committed at run start)
- **Split:** dataset/splits/gamma_split_v1.json (seed=42) — train=70, val=16, test=14
- **Architecture:** GammaMultimodalModel, modality=fusion (fundus + OCT cross-attention)
- **Encoders:** resnet18 / resnet18 (fundus / OCT), ImageNet-pretrained
- **Image resolution:** 160x160
- **OCT slice count/sampling:** 8, evenly spaced from 256
- **Batch size:** 4
- **Optimizer:** AdamW, lr=1e-4, weight_decay=1e-4
- **LR schedule:** CosineAnnealingLR, T_max=25
- **Loss:** Focal loss (gamma=2.0), weighted by inverse class frequency from the real train split
- **Augmentation:** fundus flip/rotation/color-jitter; OCT brightness/contrast only
- **Modality dropout:** 0.15
- **Mixed precision:** enabled
- **Epochs (max):** 25, early stopping patience=8 on val loss
- **Command:**
  ```
  python train_multimodal.py --modality fusion --run-name fusion_run1 \
      --img-size 160 --oct-slices 8 --batch-size 4 --epochs 25 --lr 1e-4 \
      --focal-loss --amp --patience 8
  ```
- **Status:** LAUNCHED, running in background at the time this entry was
  written. **Do not treat this entry as containing results** — it's
  recorded before completion per the "record before finishing" workflow
  requirement. The actual best validation epoch, checkpoint path, and test
  metrics will be appended in a follow-up dated entry once the run
  finishes and `evaluate.py` has actually been executed against it.
- **Best validation epoch:** PENDING
- **Test metrics:** PENDING — will only ever be filled in with output
  copy-pasted from an actual `evaluate.py` run, never estimated.
- **Checkpoint path:** training/checkpoints/fusion_run1.pt (once saved)
- **Notes:** First real training run on the actual GAMMA dataset in this
  project. Test split is only 14 samples — expect high variance in any
  single test metric; this run is a first data point, not a conclusion.
