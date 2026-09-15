"""
Upgraded 4-modality glaucoma severity model.

This keeps your existing per-modality backbones (EfficientNetV2S for
Fundus/OCT, EfficientNetB0 for HVF, MLP for tabular RNFL/GCC) and the
Attention U-Net decoder on the fundus branch — those are already solid.
What changes is the fusion head: `Concatenate()` is replaced by the
cross-attention block in fusion.py, and the loss is switchable to focal
loss (losses.py). Import `build_model` from here in place of the
inline architecture cell in multimodal-code.ipynb.
"""

from __future__ import annotations

import os

import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras.applications import EfficientNetB0, EfficientNetV2S
from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2

from fusion import cross_modal_fusion
from losses import categorical_focal_loss

INPUT_SHAPE = (224, 224, 3)
CLINICAL_DIM = 12
NUM_CLASSES = 3


def _attention_gate(x, g, inter_channels):
    theta_x = layers.Conv2D(inter_channels, (1, 1), padding="same")(x)
    phi_g = layers.Conv2D(inter_channels, (1, 1), padding="same")(g)
    phi_g = layers.UpSampling2D(
        size=(theta_x.shape[1] // phi_g.shape[1], theta_x.shape[2] // phi_g.shape[2])
    )(phi_g)
    add_xg = layers.Activation("relu")(layers.Add()([theta_x, phi_g]))
    psi = layers.Conv2D(1, (1, 1), padding="same", activation="sigmoid")(add_xg)
    return layers.Multiply()([x, psi])


def _load_backbone(weights_filename: str, kaggle_input_path: str, **effnet_kwargs):
    """Same weight-resolution logic as the notebook: prefer a locally
    pre-trained medical backbone over generic ImageNet weights."""
    weights = "imagenet"
    local_path = None
    if os.path.exists(weights_filename):
        local_path = weights_filename
        weights = None
    elif os.path.exists(kaggle_input_path):
        local_path = kaggle_input_path
        weights = None

    backbone = EfficientNetV2S(weights=weights, include_top=False, **effnet_kwargs)
    if local_path is not None:
        backbone.load_weights(local_path)
    return backbone


def _freeze_all_but_last(backbone, unfreeze_last_n, name):
    backbone._name = name
    backbone.trainable = True
    for layer in backbone.layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
    for layer in backbone.layers[:-unfreeze_last_n]:
        layer.trainable = False
    return backbone


def _fundus_branch(fundus_input):
    effnet_fundus = _load_backbone(
        "fundus_backbone_only.keras",
        "/kaggle/input/fundus-pretrained-weights/fundus_backbone_only.keras",
        input_shape=INPUT_SHAPE,
    )
    effnet_fundus = _freeze_all_but_last(effnet_fundus, 30, "effnet_fundus")
    fundus_features = effnet_fundus(fundus_input)

    x = layers.Conv2D(32, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(fundus_input)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(32, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    skip1 = x
    x = layers.MaxPooling2D(2)(x)

    x = layers.Conv2D(64, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(64, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    skip2 = x
    x = layers.MaxPooling2D(2)(x)

    x = layers.Conv2D(128, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(128, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    skip3 = x
    x = layers.MaxPooling2D(2)(x)

    x = layers.Conv2D(256, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(256, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    bridge = x

    x = layers.UpSampling2D(2)(bridge)
    att3 = _attention_gate(skip3, bridge, 64)
    x = layers.Concatenate()([x, att3])
    x = layers.Conv2D(128, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(128, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)

    x = layers.UpSampling2D(2)(x)
    att2 = _attention_gate(skip2, x, 32)
    x = layers.Concatenate()([x, att2])
    x = layers.Conv2D(64, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(64, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)
    x = layers.BatchNormalization()(x)

    unet_features = layers.Conv2D(32, 3, activation="relu", padding="same", kernel_regularizer=l2(1e-4))(x)

    gap_eff = layers.GlobalAveragePooling2D(name="gap_eff_fundus")(fundus_features)
    gap_unet = layers.GlobalAveragePooling2D(name="gap_unet")(unet_features)
    return layers.Concatenate(name="fundus_vector")([gap_eff, gap_unet])


def _hvf_branch(hvf_input):
    effnet_hvf = EfficientNetB0(weights="imagenet", include_top=False, input_shape=INPUT_SHAPE)
    effnet_hvf = _freeze_all_but_last(effnet_hvf, 20, "effnet_hvf")
    hvf_features = effnet_hvf(hvf_input)
    return layers.GlobalAveragePooling2D(name="hvf_vector")(hvf_features)


def _oct_branch(oct_input):
    effnet_oct = _load_backbone(
        "oct_backbone_only.keras",
        "/kaggle/input/oct-pretrained-weights/oct_backbone_only.keras",
        input_shape=INPUT_SHAPE,
    )
    effnet_oct = _freeze_all_but_last(effnet_oct, 30, "effnet_oct")
    oct_features = effnet_oct(oct_input)
    return layers.GlobalAveragePooling2D(name="oct_vector")(oct_features)


def _tabular_branch(tabular_input):
    y = layers.Dense(64, activation="relu", kernel_regularizer=l2(1e-4))(tabular_input)
    y = layers.BatchNormalization()(y)
    y = layers.Dropout(0.3)(y)
    y = layers.Dense(32, activation="relu", kernel_regularizer=l2(1e-4))(y)
    return layers.BatchNormalization(name="tabular_vector")(y)


def build_model(
    use_focal_loss: bool = True,
    focal_gamma: float = 2.0,
    focal_alpha=(1.0, 3.0, 1.0),
    fusion_proj_dim: int = 128,
    fusion_heads: int = 4,
    modality_dropout: float = 0.15,
    learning_rate: float = 1e-4,
) -> Model:
    fundus_input = layers.Input(shape=INPUT_SHAPE, name="fundus_input")
    hvf_input = layers.Input(shape=INPUT_SHAPE, name="hvf_input")
    oct_input = layers.Input(shape=INPUT_SHAPE, name="oct_input")
    tabular_input = layers.Input(shape=(CLINICAL_DIM,), name="tabular_input")

    fundus_vec = _fundus_branch(fundus_input)
    hvf_vec = _hvf_branch(hvf_input)
    oct_vec = _oct_branch(oct_input)
    tab_vec = _tabular_branch(tabular_input)

    fused = cross_modal_fusion(
        {"fundus": fundus_vec, "hvf": hvf_vec, "oct": oct_vec, "tabular": tab_vec},
        proj_dim=fusion_proj_dim,
        num_heads=fusion_heads,
        modality_dropout=modality_dropout,
    )

    x = layers.Dense(256, activation="relu", kernel_regularizer=l2(1e-3))(fused)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.6)(x)
    x = layers.Dense(128, activation="relu", kernel_regularizer=l2(1e-3))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(64, activation="relu", kernel_regularizer=l2(1e-3))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(NUM_CLASSES, activation="softmax", name="severity")(x)

    model = Model(
        inputs=[fundus_input, hvf_input, oct_input, tabular_input],
        outputs=outputs,
        name="glaucoma_cross_attention_fusion",
    )

    loss = (
        categorical_focal_loss(gamma=focal_gamma, alpha=list(focal_alpha), label_smoothing=0.1)
        if use_focal_loss
        else tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=loss,
        metrics=["accuracy"],
    )
    return model


if __name__ == "__main__":
    m = build_model()
    m.summary()
