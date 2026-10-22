"""Recomputes every figure in docs/DATA_AUDIT.md from the raw files and writes
ml/results/data_audit.json (served by /api/audit and shown in the UI).

    python ml/glaucoma/audit_data.py --sankara <.../retinal-imaging-research> --hvf-csv <hvf_features.csv>

Both paths are optional: without them only the Research-Excel checks run and the
Sankara checks are reported as null rather than invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from research_data import EXCEL, ROOT, load_master

GC = ["RNFL_Avg", "RNFL_S", "RNFL_I", "RNFL_N", "RNFL_T", "GCC_Avg", "GCC_SUPERIOR", "GCC_INFERIOR",
      "GCC_SN", "GCC_ST", "GCC_IN", "GCC_IT"]
AC = ["Average_RNFL", "RNFL_Superior", "RNFL_Inferior", "RNFL_Nasal", "RNFL_Temporal", "Average_GCC",
      "GCC_Superior", "GCC_Inferior", "GCC_Supero nasal", "GCC_Supero temporal", "GCC_Infero nasal",
      "GCC_Infero temporal"]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sankara", default="")
    ap.add_argument("--hvf-csv", default="")
    a = ap.parse_args()
    g = pd.read_excel(EXCEL, sheet_name="Glaucoma").dropna(subset=["SI No"]).reset_index(drop=True)
    c = pd.read_excel(EXCEL, sheet_name="Controls").dropna(subset=["SI_NO"]).reset_index(drop=True)
    md = pd.to_numeric(g.HVF_MD, errors="coerce")
    rule = md.map(lambda m: "Mild" if m > -6 else ("Moderate" if m > -12 else "Severe"))
    master = load_master()
    out: dict = {
        "research": {
            "eyes": len(master), "controls": int((master.label == 0).sum()),
            "glaucoma": {k: int((g.Category == k).sum()) for k in ("Mild", "Moderate", "Severe")},
            "reconstructed_patients": int(master.group.nunique()),
            "md_rule_agreement": round(float((rule == g.Category).mean()), 4),
            "pachy_missing_pct": {"glaucoma": round(float(g.Pachy.isna().mean() * 100), 1),
                                  "control": round(float(c.Pachy.isna().mean() * 100), 1)},
            "cft_missing_pct": {"glaucoma": round(float(g.CFT.isna().mean() * 100), 1),
                                "control": round(float(c.CFT.isna().mean() * 100), 1)},
            "mean_age": {"glaucoma": round(float(g.Age.mean()), 1), "control": round(float(pd.to_numeric(c.Age).mean()), 1)},
        },
        "sankara": None,
    }
    if a.sankara:
        S = Path(a.sankara)
        fund = {p: md5(p) for p in (S / "Glaucoma AI Project 1" / "Fundus image").rglob("*.jpg")}
        disc = {p: md5(p) for p in (S / "Glaucoma Disc photos").glob("*.jpg")}
        rn = pd.read_excel(S / "Glaucoma AI Project 1" / "RNFL and GCC data" / "Glaucoma AI.xlsx")
        rn.columns = [x.strip() for x in rn.columns]
        G = g[GC].apply(pd.to_numeric, errors="coerce").values
        A = rn[AC].apply(pd.to_numeric, errors="coerce").values
        exact = [int(np.where(np.nansum(np.abs(G - r), 1) == 0)[0][0]) for r in A if (np.nansum(np.abs(G - r), 1) == 0).any()]
        sk = {"fundus_images": len(fund), "disc_photos": len(disc),
              "disc_identical_to_fundus": int(sum(h in set(fund.values()) for h in disc.values())),
              "rnfl_gcc_rows": len(rn), "rnfl_gcc_exact_matches_in_research": len(exact)}
        if a.hvf_csv:
            h = pd.read_csv(a.hvf_csv)
            gm = g.assign(md=md)
            loose = strict = 0
            for _, r in h.iterrows():
                eye = {"R": "OD", "L": "OS"}[r.eye]
                cand = gm[(gm.md.sub(r.md_db).abs() < 0.011) & (gm.Eye == eye)]
                loose += len(cand) > 0
                strict += int((cand.Age.sub(r.age_years).abs() <= 2).sum() == 1)
            sk.update(hvf_files=len(h), hvf_md_eye_matches=int(loose), hvf_unique_strict_matches=int(strict))
        out["sankara"] = sk
    p = ROOT / "ml" / "results" / "data_audit.json"
    p.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
