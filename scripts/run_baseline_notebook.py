"""
Local runner for the original Kaggle baseline notebook (multimodal_code.ipynb),
adapted only to point at the local dataset copy and to save artifacts locally.
Model architecture, generators, splitting logic, and training hyperparameters
are otherwise unchanged from the notebook so results are a fair baseline
comparison against training/train_multimodal.py.
"""
import os
import re
import random
import time
import numpy as np
import pandas as pd
import cv2
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras.applications import EfficientNetB0, EfficientNetV2S
from tensorflow.keras.layers import (
    Input, Conv2D, MaxPooling2D, UpSampling2D, Concatenate, Add,
    GlobalAveragePooling2D, Dense, Dropout, BatchNormalization,
    Multiply, Activation,
)
from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

BASE = os.path.join(os.path.dirname(__file__), "..", "dataset_baseline", "Augmented_Multimodal")
BASE = os.path.abspath(BASE)
FUNDUS_PATH = os.path.join(BASE, "Fundus")
HVF_PATH = os.path.join(BASE, "HVF")
OCT_PATH = os.path.join(BASE, "OCT")
RNFL_PATH = os.path.join(BASE, "RNFL_GCC", "Glaucoma AI.xlsx")

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "augmented")
os.makedirs(OUT_DIR, exist_ok=True)

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "..", "baseline_weights")
FUNDUS_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "fundus_backbone_only.keras")
OCT_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "oct_backbone_only.keras")

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = int(os.environ.get("BASELINE_EPOCHS", "30"))

CLASSES = {"Mild": 1, "Moderate": 2, "Severe": 3}
CLINICAL_COLS = [
    'Average_RNFL', 'RNFL_Superior', 'RNFL_Inferior', 'RNFL_Nasal', 'RNFL_Temporal',
    'Average_GCC', 'GCC_Superior', 'GCC_Inferior', 'GCC_Supero nasal', 'GCC_Supero temporal',
    'GCC_Infero nasal', 'GCC_Infero temporal'
]

print("Using dataset BASE path:", BASE)
df_rnfl = pd.read_excel(RNFL_PATH)
df_rnfl['Glaucoma_Severity'] = df_rnfl['Glaucoma_Severity'].str.upper()
print("Unique severity labels found:", df_rnfl['Glaucoma_Severity'].unique())

excel_by_class = {}
for class_name in CLASSES.keys():
    excel_by_class[class_name] = df_rnfl[df_rnfl['Glaucoma_Severity'] == class_name.upper()].copy()

records_train, records_val, records_test = [], [], []

for class_name, label in CLASSES.items():
    fundus_folder = os.path.join(FUNDUS_PATH, class_name)
    hvf_folder = os.path.join(HVF_PATH, class_name)
    oct_folder = os.path.join(OCT_PATH, class_name)
    if not os.path.exists(fundus_folder):
        continue

    all_fundus = sorted([f for f in os.listdir(fundus_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    test_files = [f for f in all_fundus if f.startswith('test_')]
    orig_files = [f for f in all_fundus if f.startswith('orig_tr')]
    aug_files = [f for f in all_fundus if f.startswith('aug_')]

    random.seed(42)
    random.shuffle(orig_files)
    n_val = max(1, int(round(len(orig_files) * 0.125)))
    val_files_list = orig_files[:n_val]
    train_orig_files = orig_files[n_val:]

    def make_record(fname, split_tag, fundus_folder=fundus_folder, hvf_folder=hvf_folder,
                     oct_folder=oct_folder, label=label, class_name=class_name):
        hvf_path_f = os.path.join(hvf_folder, fname)
        oct_path_f = os.path.join(oct_folder, fname)
        if not os.path.exists(hvf_path_f):
            hvfs = sorted([f for f in os.listdir(hvf_folder) if f.startswith(fname[:8])])
            hvf_path_f = os.path.join(hvf_folder, hvfs[0]) if hvfs else os.path.join(hvf_folder, sorted(os.listdir(hvf_folder))[0])
        if not os.path.exists(oct_path_f):
            octs = sorted([f for f in os.listdir(oct_folder) if f.startswith(fname[:8])])
            oct_path_f = os.path.join(oct_folder, octs[0]) if octs else os.path.join(oct_folder, sorted(os.listdir(oct_folder))[0])
        return {
            'fundus_path': os.path.join(fundus_folder, fname),
            'hvf_path': hvf_path_f,
            'oct_path': oct_path_f,
            'label': label,
            'class_name': class_name,
            'split': split_tag,
            'orig_stem': fname,
        }

    for f in test_files:
        r = make_record(f, 'test')
        raw_idx = int(f[5:9])
        for col in CLINICAL_COLS:
            r[col] = excel_by_class[class_name].iloc[raw_idx % len(excel_by_class[class_name])][col]
        records_test.append(r)

    for f in val_files_list:
        r = make_record(f, 'val')
        pos_idx = int(f[7:11])
        for col in CLINICAL_COLS:
            r[col] = excel_by_class[class_name].iloc[pos_idx % len(excel_by_class[class_name])][col]
        records_val.append(r)

    for f in train_orig_files + aug_files:
        r = make_record(f, 'train')
        if f.startswith('aug_'):
            try:
                pos_idx = int(f.split('_train')[1][:4])
            except Exception:
                pos_idx = 0
        else:
            pos_idx = int(f[7:11])
        for col in CLINICAL_COLS:
            r[col] = excel_by_class[class_name].iloc[pos_idx % len(excel_by_class[class_name])][col]
        records_train.append(r)

train_df = pd.DataFrame(records_train).reset_index(drop=True)
val_df = pd.DataFrame(records_val).reset_index(drop=True)
test_df = pd.DataFrame(records_test).reset_index(drop=True)

print(f"Training set:   {len(train_df)} samples  | class dist: {train_df['class_name'].value_counts().to_dict()}")
print(f"Validation set: {len(val_df)} samples  | class dist: {val_df['class_name'].value_counts().to_dict()}")
print(f"Test set:       {len(test_df)} samples  | class dist: {test_df['class_name'].value_counts().to_dict()}")
print("\nLeakage check:")
print(f"  Test files starting with 'test_':   {(test_df['fundus_path'].str.contains('/test_') | test_df['fundus_path'].str.contains(chr(92)+'test_')).all()}")
print(f"  Any aug_ files in test set:         {(test_df['fundus_path'].str.contains('aug_')).any()}")

X_train_img = train_df[['fundus_path', 'hvf_path', 'oct_path']].values
X_val_img = val_df[['fundus_path', 'hvf_path', 'oct_path']].values
X_test_img = test_df[['fundus_path', 'hvf_path', 'oct_path']].values

X_train_tab = train_df[CLINICAL_COLS].values.astype(float)
X_val_tab = val_df[CLINICAL_COLS].values.astype(float)
X_test_tab = test_df[CLINICAL_COLS].values.astype(float)

y_train = train_df['label'].values
y_val = val_df['label'].values
y_test = test_df['label'].values

scaler = StandardScaler()
X_train_tab = scaler.fit_transform(X_train_tab)
X_val_tab = scaler.transform(X_val_tab)
X_test_tab = scaler.transform(X_test_tab)


def load_image(path):
    img = cv2.imread(path)
    img = cv2.resize(img, IMG_SIZE)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img / 255.0
    return img


def multimodal_generator(X_paths, X_tabular, y_labels, batch_size, shuffle=True, class_weights=None):
    n = len(X_paths)
    indices = np.arange(n)
    while True:
        if shuffle:
            np.random.shuffle(indices)
        for start in range(0, n, batch_size):
            batch_idx = indices[start: start + batch_size]
            fundus_batch, hvf_batch, oct_batch, tabular_batch, label_batch, weight_batch = [], [], [], [], [], []
            for i in batch_idx:
                fundus_batch.append(load_image(X_paths[i][0]))
                hvf_batch.append(load_image(X_paths[i][1]))
                oct_batch.append(load_image(X_paths[i][2]))
                tabular_batch.append(X_tabular[i])
                lbl = y_labels[i] - 1
                label_batch.append(lbl)
                if class_weights is not None:
                    weight_batch.append(class_weights.get(lbl, 1.0))

            f_in = np.array(fundus_batch)
            h_in = np.array(hvf_batch)
            o_in = np.array(oct_batch)
            t_in = np.array(tabular_batch)
            targets = tf.keras.utils.to_categorical(np.array(label_batch), num_classes=3)

            inputs = {"fundus_input": f_in, "hvf_input": h_in, "oct_input": o_in, "tabular_input": t_in}
            if class_weights is not None:
                weights = np.array(weight_batch)
                yield inputs, targets, weights
            else:
                yield inputs, targets


train_gen = multimodal_generator(X_train_img, X_train_tab, y_train, BATCH_SIZE, shuffle=True, class_weights={0: 1.0, 1: 3.0, 2: 1.0})
val_gen = multimodal_generator(X_val_img, X_val_tab, y_val, BATCH_SIZE, shuffle=False)
test_gen = multimodal_generator(X_test_img, X_test_tab, y_test, BATCH_SIZE, shuffle=False)

train_steps = int(np.ceil(len(X_train_img) / BATCH_SIZE))
val_steps = int(np.ceil(len(X_val_img) / BATCH_SIZE))
test_steps = int(np.ceil(len(X_test_img) / BATCH_SIZE))
print(f"Steps per epoch  - train: {train_steps}, val: {val_steps}, test: {test_steps}")


def attention_gate(x, g, inter_channels):
    theta_x = Conv2D(inter_channels, (1, 1), padding="same")(x)
    phi_g = Conv2D(inter_channels, (1, 1), padding="same")(g)
    phi_g = UpSampling2D(size=(theta_x.shape[1] // phi_g.shape[1], theta_x.shape[2] // phi_g.shape[2]))(phi_g)
    add_xg = Activation("relu")(Add()([theta_x, phi_g]))
    psi = Conv2D(1, (1, 1), padding="same", activation="sigmoid")(add_xg)
    return Multiply()([x, psi])


input_shape = (224, 224, 3)

fundus_input = Input(shape=input_shape, name="fundus_input")

fundus_weights = "imagenet"
if os.path.exists(FUNDUS_WEIGHTS_PATH):
    print("Found pre-trained Fundus weights! Using custom medical weights instead of ImageNet.")
    fundus_weights = None

effnet_fundus = EfficientNetV2S(weights=fundus_weights, include_top=False, input_shape=input_shape)
if fundus_weights is None:
    effnet_fundus.load_weights(FUNDUS_WEIGHTS_PATH)
effnet_fundus._name = "effnet_fundus"
effnet_fundus.trainable = True
for layer in effnet_fundus.layers:
    if isinstance(layer, tf.keras.layers.BatchNormalization):
        layer.trainable = False
for layer in effnet_fundus.layers[:-30]:
    layer.trainable = False
fundus_features = effnet_fundus(fundus_input)

x = Conv2D(32, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(fundus_input)
x = BatchNormalization()(x)
x = Conv2D(32, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
skip1 = x
x = MaxPooling2D((2, 2))(x)

x = Conv2D(64, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
x = Conv2D(64, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
skip2 = x
x = MaxPooling2D((2, 2))(x)

x = Conv2D(128, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
x = Conv2D(128, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
skip3 = x
x = MaxPooling2D((2, 2))(x)

x = Conv2D(256, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
x = Conv2D(256, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
bridge = x

x = UpSampling2D((2, 2))(bridge)
att3 = attention_gate(x=skip3, g=bridge, inter_channels=64)
x = Concatenate()([x, att3])
x = Conv2D(128, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
x = Conv2D(128, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)

x = UpSampling2D((2, 2))(x)
att2 = attention_gate(x=skip2, g=x, inter_channels=32)
x = Concatenate()([x, att2])
x = Conv2D(64, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)
x = Conv2D(64, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)
x = BatchNormalization()(x)

unet_features = Conv2D(32, (3, 3), activation="relu", padding="same", kernel_regularizer=l2(0.0001))(x)

gap_eff_fundus = GlobalAveragePooling2D(name="gap_eff_fundus")(fundus_features)
gap_unet = GlobalAveragePooling2D(name="gap_unet")(unet_features)

hvf_input = Input(shape=input_shape, name="hvf_input")
effnet_hvf = EfficientNetB0(weights="imagenet", include_top=False, input_shape=input_shape)
effnet_hvf._name = "effnet_hvf"
effnet_hvf.trainable = True
for layer in effnet_hvf.layers:
    if isinstance(layer, tf.keras.layers.BatchNormalization):
        layer.trainable = False
for layer in effnet_hvf.layers[:-20]:
    layer.trainable = False
hvf_features = effnet_hvf(hvf_input)
gap_eff_hvf = GlobalAveragePooling2D(name="gap_eff_hvf")(hvf_features)

oct_input = Input(shape=input_shape, name="oct_input")

oct_weights = "imagenet"
if os.path.exists(OCT_WEIGHTS_PATH):
    print("Found pre-trained OCT weights! Using custom medical weights instead of ImageNet.")
    oct_weights = None

effnet_oct = EfficientNetV2S(weights=oct_weights, include_top=False, input_shape=input_shape)
if oct_weights is None:
    effnet_oct.load_weights(OCT_WEIGHTS_PATH)
effnet_oct._name = "effnet_oct"
effnet_oct.trainable = True
for layer in effnet_oct.layers:
    if isinstance(layer, tf.keras.layers.BatchNormalization):
        layer.trainable = False
for layer in effnet_oct.layers[:-30]:
    layer.trainable = False
oct_features = effnet_oct(oct_input)
gap_eff_oct = GlobalAveragePooling2D(name="gap_eff_oct")(oct_features)

tabular_input = Input(shape=(12,), name="tabular_input")
y_tab = Dense(64, activation="relu", kernel_regularizer=l2(0.0001))(tabular_input)
y_tab = BatchNormalization()(y_tab)
y_tab = Dropout(0.3)(y_tab)
y_tab = Dense(32, activation="relu", kernel_regularizer=l2(0.0001))(y_tab)
y_tab = BatchNormalization()(y_tab)

merged = Concatenate(name="merged_features")([gap_eff_fundus, gap_unet, gap_eff_hvf, gap_eff_oct, y_tab])

x = Dense(256, activation="relu", kernel_regularizer=l2(0.001))(merged)
x = BatchNormalization()(x)
x = Dropout(0.6)(x)
x = Dense(128, activation="relu", kernel_regularizer=l2(0.001))(x)
x = BatchNormalization()(x)
x = Dropout(0.4)(x)
x = Dense(64, activation="relu", kernel_regularizer=l2(0.001))(x)
x = BatchNormalization()(x)
x = Dropout(0.3)(x)

outputs = Dense(3, activation="softmax")(x)

model = Model(inputs=[fundus_input, hvf_input, oct_input, tabular_input], outputs=outputs)
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
    metrics=["accuracy"],
)
model.summary()

CKPT_PATH = os.path.join(OUT_DIR, "Baseline_Kaggle_model.weights.h5")


class WarmupCosineDecay(tf.keras.callbacks.Callback):
    def __init__(self, warmup_epochs, total_epochs, base_lr, min_lr=1e-6):
        super().__init__()
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.base_lr = base_lr
        self.min_lr = min_lr

    def on_epoch_begin(self, epoch, logs=None):
        import math
        if epoch < self.warmup_epochs:
            lr = self.base_lr * (epoch + 1) / self.warmup_epochs
        else:
            progress = (epoch - self.warmup_epochs) / max(1, self.total_epochs - self.warmup_epochs)
            lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (1 + math.cos(math.pi * progress))
        self.model.optimizer.learning_rate = float(lr)


callbacks = [
    EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True, verbose=1),
    ModelCheckpoint(CKPT_PATH, monitor="val_loss", save_best_only=True, save_weights_only=True, mode="min", verbose=1),
    WarmupCosineDecay(warmup_epochs=5, total_epochs=EPOCHS, base_lr=1e-4, min_lr=1e-7),
]

print(f"Training samples: {len(y_train)}  Val samples: {len(y_val)}")
print(f"Class distribution in train: {dict(zip(*np.unique(y_train, return_counts=True)))}")
print(f"Class distribution in val:   {dict(zip(*np.unique(y_val, return_counts=True)))}")
print(f"Class distribution in test:  {dict(zip(*np.unique(y_test, return_counts=True)))}")

t0 = time.time()
history = model.fit(
    train_gen,
    steps_per_epoch=train_steps,
    epochs=EPOCHS,
    validation_data=val_gen,
    validation_steps=val_steps,
    callbacks=callbacks,
    verbose=2,
)
print(f"Training wall time: {time.time() - t0:.1f}s")

# EarlyStopping(restore_best_weights=True) already restored the best weights
# into `model` in-memory; avoid reloading from disk (full-model .h5/.keras
# reload hits a TF 2.10 JSON-serialization bug with sample-weighted generators).
model.load_weights(CKPT_PATH)

val_loss, val_accuracy = model.evaluate(val_gen, steps=val_steps, verbose=0)
print(f"Validation Loss:     {val_loss:.4f}")
print(f"Validation Accuracy: {val_accuracy:.4f}")

test_loss, test_accuracy = model.evaluate(test_gen, steps=test_steps, verbose=0)
print(f"Test Loss:     {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy:.4f}")

class_names = ["Mild", "Moderate", "Severe"]

y_test_pred, y_test_true = [], []
test_gen_eval = multimodal_generator(X_test_img, X_test_tab, y_test, BATCH_SIZE, shuffle=False)
for step in range(test_steps):
    batch_inputs, batch_labels = next(test_gen_eval)
    preds = model.predict(batch_inputs, verbose=0)
    y_test_pred.extend(np.argmax(preds, axis=1))
    y_test_true.extend(np.argmax(batch_labels, axis=1))
y_test_pred = np.array(y_test_pred[:len(X_test_img)])
y_test_true = np.array(y_test_true[:len(X_test_img)])

cm_test = confusion_matrix(y_test_true, y_test_pred)
report = classification_report(y_test_true, y_test_pred, target_names=class_names, output_dict=True)
report_txt = classification_report(y_test_true, y_test_pred, target_names=class_names)
print("Test Classification Report:")
print(report_txt)

import json
with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
    json.dump({
        "epochs_ran": len(history.history["loss"]),
        "epochs_budget": EPOCHS,
        "val_loss": float(val_loss),
        "val_accuracy": float(val_accuracy),
        "test_loss": float(test_loss),
        "test_accuracy": float(test_accuracy),
        "confusion_matrix": cm_test.tolist(),
        "classification_report": report,
        "train_samples": len(y_train),
        "val_samples": len(y_val),
        "test_samples": len(y_test),
    }, f, indent=2)

with open(os.path.join(OUT_DIR, "classification_report.txt"), "w") as f:
    f.write(report_txt)

print("Saved results to", OUT_DIR)
