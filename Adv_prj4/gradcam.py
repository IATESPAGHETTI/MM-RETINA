"""
Grad-CAM for a multi-input model.

Standard Grad-CAM implementations assume a single image input. This
version targets one named image branch (e.g. "oct_input") of the
multi-modal model while holding the other branches fixed at their
actual sample values, so the heatmap answers: "where did the OCT
backbone specifically look to justify this severity prediction?"
"""

from __future__ import annotations

import numpy as np
import tensorflow as tf


def make_gradcam_heatmap(
    model: tf.keras.Model,
    inputs: dict[str, np.ndarray],
    image_input_name: str,
    conv_layer_name: str,
    class_index: int | None = None,
) -> np.ndarray:
    """Returns a (H, W) heatmap in [0, 1] for `inputs[image_input_name]`.

    inputs:
        Dict of input_name -> single-sample array (add batch dim of 1),
        matching the model's named Input layers.
    conv_layer_name:
        Name of the last conv layer inside the backbone for that modality,
        e.g. the top block of the nested EfficientNetV2S ("effnet_oct").
        For a nested submodel, pass "effnet_oct" and this function will
        reach into it via `get_layer`.
    """
    # `conv_layer_name` names one of the whole-backbone submodels wired in by
    # model.py (e.g. "effnet_oct", "effnet_hvf"), so its own `.output` — the
    # feature map produced when the backbone was called on that branch's
    # input — is exactly the conv activation Grad-CAM needs.
    target_layer = model.get_layer(conv_layer_name)

    grad_model = tf.keras.models.Model(
        [model.inputs], [target_layer.output, model.output]
    )

    tensor_inputs = {k: tf.convert_to_tensor(v) for k, v in inputs.items()}
    with tf.GradientTape() as tape:
        conv_output, predictions = grad_model(tensor_inputs)
        if class_index is None:
            class_index = int(tf.argmax(predictions[0]))
        target_score = predictions[:, class_index]

    grads = tape.gradient(target_score, conv_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_output = conv_output[0]
    heatmap = conv_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy()


def overlay_heatmap(image_rgb: np.ndarray, heatmap: np.ndarray, alpha: float = 0.4):
    """Resizes `heatmap` to `image_rgb`'s size and alpha-blends a jet colormap.

    `image_rgb` is expected in [0, 1] float RGB, matching the notebook's
    `load_image` normalisation. Returns a uint8 RGB image for display/saving.
    """
    import cv2

    h, w = image_rgb.shape[:2]
    heatmap_resized = cv2.resize(heatmap, (w, h))
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    colored = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB) / 255.0

    base = image_rgb if image_rgb.max() <= 1.0 else image_rgb / 255.0
    blended = (1 - alpha) * base + alpha * colored
    return np.uint8(np.clip(blended, 0, 1) * 255)
