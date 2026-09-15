"""Focal loss for the 3-class (Mild/Moderate/Severe) severity head.

The baseline notebook fights class imbalance with hand-tuned sample
weights ({0: 1.0, 1: 3.0, 2: 1.0} for Keras, {1: 5.0} for RF/XGBoost).
That works but is brittle — it has to be re-tuned by hand whenever the
class balance shifts. Focal loss achieves the same goal automatically by
down-weighting easy, already-confident predictions and concentrating
gradient on hard/misclassified samples (Lin et al., 2017, RetinaNet).
"""

from __future__ import annotations

import tensorflow as tf


def categorical_focal_loss(gamma: float = 2.0, alpha=None, label_smoothing: float = 0.1):
    """Returns a Keras-compatible focal loss for one-hot / soft targets.

    gamma:
        Focusing parameter. gamma=0 reduces to plain cross-entropy.
        2.0 is the standard RetinaNet default.
    alpha:
        Optional per-class weight vector, e.g. [1.0, 3.0, 1.0] to keep
        boosting the under-represented Moderate class on top of focal
        re-weighting. None disables it.
    label_smoothing:
        Kept consistent with the baseline's CategoricalCrossentropy(0.1)
        so this is a drop-in replacement, not a confound.
    """
    alpha_tensor = None if alpha is None else tf.constant(alpha, dtype=tf.float32)

    def loss_fn(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        if label_smoothing:
            num_classes = tf.cast(tf.shape(y_true)[-1], tf.float32)
            y_true = y_true * (1.0 - label_smoothing) + label_smoothing / num_classes

        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        cross_entropy = -y_true * tf.math.log(y_pred)
        modulating_factor = tf.pow(1.0 - y_pred, gamma)
        loss = modulating_factor * cross_entropy

        if alpha_tensor is not None:
            loss = loss * alpha_tensor

        return tf.reduce_sum(loss, axis=-1)

    return loss_fn
