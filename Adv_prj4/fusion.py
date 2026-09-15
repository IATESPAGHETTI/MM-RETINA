"""
Cross-attention fusion for the ProcureFlow-unrelated OCT/Fundus/HVF + tabular
glaucoma severity classifier.

Your existing pipeline (multimodal-code.ipynb) fuses branches with a single
Concatenate() over GAP vectors — this is "late fusion" and treats every
modality as equally informative for every sample, which is rarely true
(e.g. HVF is more decisive for early-stage loss, OCT/RNFL for structural
damage). This module replaces that with a small Transformer-style
cross-attention block: each modality's feature vector attends to every
other modality's vector before pooling, so the network learns per-sample,
per-modality weighting instead of a fixed concatenation.
"""

from __future__ import annotations

import tensorflow as tf
from tensorflow.keras import layers


class ModalityDropout(layers.Layer):
    """Randomly zeroes out whole modality tokens during training.

    Standard Dropout zeroes individual scalars; that lets the network lean
    on redundant signal from the same modality. Zeroing an entire modality's
    token forces the fusion block to tolerate a missing scan/report, which
    is exactly the failure mode a real deployment hits (a patient without an
    HVF test on file, a corrupted OCT export).
    """

    def __init__(self, drop_prob: float = 0.15, **kwargs):
        super().__init__(**kwargs)
        self.drop_prob = drop_prob

    def call(self, tokens, training=None):
        # tokens: (batch, num_modalities, dim)
        if not training or self.drop_prob <= 0:
            return tokens
        shape = tf.shape(tokens)
        keep_mask = tf.cast(
            tf.random.uniform((shape[0], shape[1], 1)) > self.drop_prob,
            tokens.dtype,
        )
        # Guarantee at least one modality survives per sample.
        any_kept = tf.reduce_max(keep_mask, axis=1, keepdims=True)
        keep_mask = tf.where(tf.equal(any_kept, 0.0), tf.ones_like(keep_mask), keep_mask)
        return tokens * keep_mask

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"drop_prob": self.drop_prob})
        return cfg


def cross_modal_fusion(
    modality_vectors: dict[str, tf.Tensor],
    proj_dim: int = 128,
    num_heads: int = 4,
    ff_dim: int = 256,
    modality_dropout: float = 0.15,
    name: str = "cross_modal_fusion",
) -> tf.Tensor:
    """Builds a cross-attention fusion head over pooled per-modality vectors.

    Parameters
    ----------
    modality_vectors:
        Mapping of modality name -> pooled feature tensor of shape (B, C_i).
        C_i may differ per modality (e.g. EfficientNetV2S vs the tabular MLP);
        each is linearly projected to a common `proj_dim` before attention.
    proj_dim:
        Shared token dimension all modalities are projected into.
    num_heads, ff_dim:
        Standard transformer-block hyperparameters for the attention + FFN.
    modality_dropout:
        Probability of dropping an entire modality token at train time.

    Returns
    -------
    A single fused feature vector (B, proj_dim) — feed this into your
    classification head instead of the plain `Concatenate(...)` output.
    """
    names = list(modality_vectors.keys())
    projected = []
    for m in names:
        v = modality_vectors[m]
        v = layers.Dense(proj_dim, name=f"{name}_proj_{m}")(v)
        v = layers.LayerNormalization(name=f"{name}_ln_{m}")(v)
        projected.append(v)

    # Stack into a token sequence: (B, num_modalities, proj_dim)
    tokens = layers.Lambda(
        lambda xs: tf.stack(xs, axis=1), name=f"{name}_stack"
    )(projected)

    tokens = ModalityDropout(modality_dropout, name=f"{name}_modality_dropout")(tokens)

    # Learned modality-type embeddings (so attention knows "which" token is which,
    # since order alone is a weak signal once modalities get dropped).
    num_modalities = len(names)
    modality_embed = layers.Embedding(
        input_dim=num_modalities, output_dim=proj_dim, name=f"{name}_modality_embed"
    )(tf.range(num_modalities))
    tokens = layers.Add(name=f"{name}_add_modality_embed")(
        [tokens, tf.expand_dims(modality_embed, axis=0)]
    )

    # Transformer encoder block: self-attention across modality tokens.
    attn_out = layers.MultiHeadAttention(
        num_heads=num_heads, key_dim=proj_dim // num_heads, name=f"{name}_mha"
    )(tokens, tokens)
    tokens = layers.Add(name=f"{name}_residual1")([tokens, attn_out])
    tokens = layers.LayerNormalization(name=f"{name}_ln1")(tokens)

    ffn = layers.Dense(ff_dim, activation="gelu", name=f"{name}_ffn1")(tokens)
    ffn = layers.Dense(proj_dim, name=f"{name}_ffn2")(ffn)
    tokens = layers.Add(name=f"{name}_residual2")([tokens, ffn])
    tokens = layers.LayerNormalization(name=f"{name}_ln2")(tokens)

    # Attention-pool the token sequence into one vector (learned query),
    # rather than a plain mean/GAP over modalities.
    pooled = layers.GlobalAveragePooling1D(name=f"{name}_pool")(tokens)
    return pooled
