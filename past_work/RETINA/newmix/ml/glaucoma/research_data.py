"""Master table for the Research (Sankara Nethralaya) glaucoma cohort.

One row per eye: OCT B-scan path, 4-class label, clinical features and a
reconstructed patient group id. See docs/DATA_AUDIT.md for why:

  * HVF_MD defines the severity label (100% agreement with the -6/-12 dB
    cut-offs), so it is kept out of the learned feature sets.
  * Pachymetry / CFT are excluded: their missingness differs between
    glaucoma and control rows and would leak the label.
  * No patient ids exist; OD/OS of one patient sit in adjacent rows with the
    same age and sex, which is how `group` is rebuilt so folds never split a
    patient's two eyes.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(os.environ.get("NEWMIX_ROOT", Path(__file__).resolve().parents[2]))
RESEARCH_DIR = ROOT / "data" / "research"
EXCEL = RESEARCH_DIR / "Glaucoma_Excel.xlsx"

CLASS_NAMES = ["Control", "Mild", "Moderate", "Severe"]
STRUCT_FEATURES = [
    "Age", "Gender", "IOP", "CDR",
    "RNFL_Avg", "RNFL_S", "RNFL_I", "RNFL_N", "RNFL_T",
    "GCC_Avg", "GCC_SUPERIOR", "GCC_INFERIOR", "GCC_ST", "GCC_SN", "GCC_IT", "GCC_IN",
]
NO_AGE_FEATURES = [f for f in STRUCT_FEATURES if f != "Age"]
LEAKY_MD_FEATURES = STRUCT_FEATURES + ["HVF_MD"]  # only for the leak demonstration

_SEV = {"Mild": 1, "Moderate": 2, "Severe": 3}


def _parse_cdr(v) -> float:
    s = str(v).strip()
    if s in ("", "nan", "None"):
        return np.nan
    try:
        return float(np.mean([float(p) for p in s.replace("–", "-").split("-")]))
    except ValueError:
        return np.nan


def _assign_groups(df: pd.DataFrame, offset: int) -> np.ndarray:
    """Adjacent rows with opposite eye + same age + same sex -> same patient."""
    gid = np.zeros(len(df), dtype=int)
    cur = offset
    paired = False
    for i in range(len(df)):
        if i > 0 and not paired and df.Eye.iloc[i] != df.Eye.iloc[i - 1] \
                and df.Age.iloc[i] == df.Age.iloc[i - 1] and df.Gender.iloc[i] == df.Gender.iloc[i - 1]:
            paired = True
        else:
            cur += 1
            paired = False
        gid[i] = cur
    return gid


def load_master() -> pd.DataFrame:
    g = pd.read_excel(EXCEL, sheet_name="Glaucoma").dropna(subset=["SI No"]).reset_index(drop=True)
    c = pd.read_excel(EXCEL, sheet_name="Controls").dropna(subset=["SI_NO"]).reset_index(drop=True)
    g = g.rename(columns={"SI No": "si"})
    c = c.rename(columns={"SI_NO": "si"})
    g["label"] = g["Category"].map(_SEV)
    c["label"] = 0
    g["image"] = [str(RESEARCH_DIR / "Glaucoma" / f"{int(i)}.jpg") for i in g.si]
    c["image"] = [str(RESEARCH_DIR / "Control" / f"{int(i)}.jpg") for i in c.si]
    g["source"], c["source"] = "glaucoma", "control"
    g["group"] = _assign_groups(g, 0)
    c["group"] = _assign_groups(c, int(g["group"].max()))
    df = pd.concat([g, c], ignore_index=True)
    df["Gender"] = (df["Gender"].str.strip().str.lower() == "male").astype(int)
    df["CDR"] = df["CDR"].map(_parse_cdr)
    num = [f for f in LEAKY_MD_FEATURES if f not in ("Gender",)]
    for col in num:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["binary"] = (df["label"] > 0).astype(int)
    missing = [p for p in df.image if not Path(p).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} OCT images missing, first: {missing[0]}")
    keep = ["image", "source", "si", "group", "label", "binary", "Eye", *LEAKY_MD_FEATURES]
    return df[keep].reset_index(drop=True)


def assign_folds(df: pd.DataFrame, k: int = 5, seed: int = 42) -> np.ndarray:
    """Patient-grouped, class-stratified folds shared by every model so that
    out-of-fold predictions from different models can be fused honestly."""
    folds = np.full(len(df), -1)
    skf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    for f, (_, te) in enumerate(skf.split(df, df.label, df.group)):
        folds[te] = f
    return folds


if __name__ == "__main__":
    d = load_master()
    d["fold"] = assign_folds(d)
    print(d.shape, "patients:", d.group.nunique())
    print(d.groupby("fold").label.value_counts().unstack(fill_value=0))
    leak = d.groupby("group").fold.nunique().max()
    print("max folds per patient (must be 1):", leak)
