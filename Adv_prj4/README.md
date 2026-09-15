# Adv_prj4 — Cross-Attention Multimodal Upgrade

Upgrades to the existing 4-modality glaucoma severity classifier
(`../multimodal-code.ipynb`): Fundus + HVF + OCT images plus RNFL/GCC
tabular measurements, predicting Mild / Moderate / Severe.

The baseline already does real multimodal fusion (concatenated GAP
vectors from three EfficientNet backbones + an MLP). What's added here:

| File | What it adds | Why |
|---|---|---|
| `fusion.py` | Cross-attention fusion block (replaces `Concatenate`) + `ModalityDropout` | Lets the model learn per-sample modality weighting instead of a fixed concat; robust to a missing modality at inference |
| `losses.py` | Categorical focal loss | Automatic hard-example mining for the under-represented Moderate class, replacing hand-tuned sample weights |
| `model.py` | `build_model()` wiring backbones -> fusion -> head | Same backbones/U-Net/attention-gates as the notebook, new fusion + loss |
| `gradcam.py` | Grad-CAM for a chosen image branch | Visual justification of predictions — required for any clinical-facing ML claim |
| `tta.py` | Test-time augmentation over the 3 image branches | Cheap accuracy/robustness gain at inference, no retraining needed |

## Using it

Replace the "4-MODALITY GLAUCOMA SEVERITY CLASSIFIER" cell in the
notebook with:

```python
import sys
sys.path.append("Adv_prj4")
from model import build_model

model = build_model(use_focal_loss=True, focal_alpha=(1.0, 3.0, 1.0))
model.summary()
```

Everything downstream (the generator, callbacks, `model.fit(...)`,
evaluation cells) is unchanged — `build_model()` returns a compiled
`keras.Model` with the same four named inputs
(`fundus_input`, `hvf_input`, `oct_input`, `tabular_input`).

For Grad-CAM on a validation sample's OCT scan:

```python
from gradcam import make_gradcam_heatmap, overlay_heatmap

heatmap = make_gradcam_heatmap(
    model,
    inputs={k: v[np.newaxis] for k, v in sample_inputs.items()},
    image_input_name="oct_input",
    conv_layer_name="effnet_oct",
)
overlaid = overlay_heatmap(sample_inputs["oct_input"], heatmap)
```

For TTA at evaluation time:

```python
from tta import predict_with_tta
probs = predict_with_tta(model, fundus_batch, hvf_batch, oct_batch, tabular_batch)
```

## What this does NOT change

- Data loading, leakage-safe train/val/test split, and the augmentation
  pipeline (`generate_multimodal_dataset.py` logic) are untouched.
- The RF/XGBoost stacking in the notebook's Phase 2 still works —
  `feature_extractor = Model(inputs=model.inputs, outputs=model.get_layer(...).output)`
  just needs to point at the new fusion output layer name instead of
  `"merged_features"` (the pooled cross-attention output, right before
  the classification head's first `Dense(256)`).
