"""Rebuilds ml/results/oct/cv_summary.json entries from saved out-of-fold CSVs
(used when a long run is stopped early, so completed seeds are not lost)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from research_data import ROOT, load_master
from train_clinical import score

OUT = ROOT / "ml" / "results" / "oct"
df = load_master(); y = df.label.values
p = OUT / "cv_summary.json"; summ = {}
for arch in sys.argv[1:]:
    runs, seeds = [], []
    for f in sorted(OUT.glob(f"oof_{arch}_seed*.csv")):
        oof = pd.read_csv(f)[[f"p{i}" for i in range(4)]].values
        runs.append({"multiclass": score(y, oof, "multiclass"),
                     "binary": score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")})
        seeds.append(f.stem.split("seed")[1])
    summ[arch] = {"epochs": 30, "seeds": ",".join(seeds), "runs": runs}
    print(arch, "seeds", seeds, "acc", round(np.mean([r["multiclass"]["accuracy"] for r in runs]), 3),
          "bal", round(np.mean([r["multiclass"]["balanced_accuracy"] for r in runs]), 3))
p.write_text(json.dumps(summ, indent=2))
