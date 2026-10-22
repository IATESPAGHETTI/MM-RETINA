"""End-to-end smoke test against a running backend.

    python tests/smoke_test.py [http://localhost:8000]

Exits non-zero if any check fails. Uses the sample images shipped in frontend/public.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "frontend" / "public"
SAMPLES = json.loads((ROOT / "frontend" / "src" / "lib" / "samples.json").read_text())
failures: list[str] = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


def img(path: Path, field="file"):
    return {field: (path.name, path.read_bytes(), "image/jpeg")}


h = requests.get(f"{BASE}/api/health", timeout=30).json()
svc = h["services"]
check("health reports all four services", all(k in svc for k in ("glaucoma_oct", "glaucoma_clinical", "glaucoma_multimodal", "diabetes")))
for k in ("glaucoma_oct", "glaucoma_clinical", "glaucoma_multimodal"):
    check(f"service ready: {k}", bool(svc[k]["ready"]), str(svc[k].get("error") or ""))
check("service ready: diabetes", svc["diabetes"]["vessels"] and svc["diabetes"]["hba1c"])

# ---- clinical ----
for s in SAMPLES:
    r = requests.post(f"{BASE}/api/glaucoma/clinical", json=s["values"], timeout=30).json()
    check(f"clinical returns stage for {s['label']}", "multiclass" in r and 0 < r["p_glaucoma"] <= 1, r.get("multiclass", {}).get("prediction", ""))
by_id = {s["id"]: s for s in SAMPLES}
cl = lambda s: requests.post(f"{BASE}/api/glaucoma/clinical", json=s["values"], timeout=30).json()
check("typical eye is answered, not deferred", cl(by_id["mild"])["defer"]["deferred"] is False)
bd = cl(by_id["borderline"])
check("borderline eye is deferred with an HVF recommendation", bd["defer"]["deferred"] is True and "visual-field" in bd["defer"]["action"], bd["defer"]["action"][:40])
check("deferred result still reports glaucoma score", 0 < bd["p_glaucoma"] <= 1)
check("clinical rejects <4 fields", requests.post(f"{BASE}/api/glaucoma/clinical", json={"Age": 60}, timeout=30).status_code == 400)

# ---- OCT + fusion ----
for s in [x for x in SAMPLES if x["image"]]:
    path = PUB / s["image"].lstrip("/")
    r = requests.post(f"{BASE}/api/glaucoma/assess", files=img(path), data={"clinical_json": json.dumps(s["values"]), "explain": "true"}, timeout=60)
    j = r.json()
    ok = r.status_code == 200 and {"oct", "clinical", "fused"} <= set(j.get("components", [])) and bool(j["oct"]["heatmap"])
    check(f"assess (OCT+clinical+Grad-CAM) {s['label']}", ok, j.get("fused", {}).get("prediction", j.get("detail", "")))
check("OCT slot rejects colour fundus", requests.post(f"{BASE}/api/glaucoma/oct", files=img(PUB / "samples" / "diabetes-1.jpg"), timeout=30).status_code == 400)
check("assess rejects empty request", requests.post(f"{BASE}/api/glaucoma/assess", data={"clinical_json": "{}"}, timeout=30).status_code == 400)
check("assess rejects bad JSON", requests.post(f"{BASE}/api/glaucoma/assess", data={"clinical_json": "{nope"}, timeout=30).status_code == 400)
check("rejects non-image upload", requests.post(f"{BASE}/api/glaucoma/oct", files={"file": ("x.jpg", b"not an image", "image/jpeg")}, timeout=30).status_code == 400)

# ---- multimodal (GAMMA) ----
files = [("oct_slices", (f"s{i}.jpg", (PUB / "oct-volume" / "0001" / f"{i:03d}.jpg").read_bytes(), "image/jpeg")) for i in (0, 36, 73, 109, 146, 182, 219, 255)]
files.append(("fundus", ("f.jpg", (PUB / "demo" / "fundus" / "gamma-0001.jpg").read_bytes(), "image/jpeg")))
r = requests.post(f"{BASE}/api/glaucoma/multimodal", data={"modality": "fusion", "explain": "true"}, files=files, timeout=90).json()
check("multimodal fusion on real volume", r.get("oct_mode") == "real_volume" and bool(r.get("fundus_heatmap")), r.get("prediction", ""))
check("multimodal rejects bad modality", requests.post(f"{BASE}/api/glaucoma/multimodal", data={"modality": "x"}, timeout=30).status_code == 400)

# ---- diabetes ----
r = requests.post(f"{BASE}/api/diabetes/analyze", files=img(PUB / "samples" / "diabetes-1.jpg"), timeout=120).json()
m = r.get("modules", {})
check("diabetes vessels", "vessels" in m and 0 < m["vessels"]["vessel_density_pct"] < 40)
check("diabetes fractal dimension in plausible range", "fractal" in m and 1.0 < m["fractal"]["fractal_dimension"] < 2.0)
check("diabetes hba1c returns consistency flag", "hba1c" in m and "consistent" in m["hba1c"])
check("diabetes rejects OCT in fundus slot", requests.post(f"{BASE}/api/diabetes/analyze", files=img(PUB / "samples" / "oct-mild.jpg"), timeout=30).status_code == 400)

# ---- evidence ----
mods = requests.get(f"{BASE}/api/models", timeout=30).json()
check("models endpoint serves clinical + oct + fusion + gamma", all(mods.get(k) for k in ("clinical", "oct", "fusion", "gamma")))
check("models endpoint serves the leakage-protocol evidence", len(mods.get("paper_protocol", [])) == 2)
check("models endpoint serves deferral evidence", set(mods.get("defer", {})) >= {"clinical", "oct", "fused"})
check("audit endpoint serves research counts", requests.get(f"{BASE}/api/audit", timeout=30).json().get("research", {}).get("eyes") == 303)

print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
