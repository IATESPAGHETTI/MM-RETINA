"""End-to-end checks for the Retina Suite extras against a running backend:
compare, explain, saved cases/patients, PDF reports, batch ZIP + CSV.

    python tests/smoke_extras.py [http://localhost:8001]

Needs only the GAMMA sample images that ship in frontend/public (demo/fundus, oct-volume/0001).
Uses unique study IDs per run and deletes what it creates. Exits non-zero if any check fails.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import uuid
import zipfile
from pathlib import Path

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
PUB = Path(__file__).resolve().parents[1] / "frontend" / "public"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


IDX = (0, 36, 73, 109, 146, 182, 219, 255)
FUNDUS_BYTES = (PUB / "demo" / "fundus" / "gamma-0001.jpg").read_bytes()
SLICES = {i: (PUB / "oct-volume" / "0001" / f"{i:03d}.jpg").read_bytes() for i in IDX}
vol = lambda: [("oct_slices", (f"s{i}.jpg", SLICES[i], "image/jpeg")) for i in IDX]  # noqa: E731
fund = ("fundus", ("f.jpg", FUNDUS_BYTES, "image/jpeg"))
tag = uuid.uuid4().hex[:5]

# ---- health, compare ----
health = requests.get(f"{BASE}/api/health", timeout=30).json()["services"].get("extras", {})
check("health reports the extras", health.get("store", {}).get("ready") is True and "explain" in health)

c = requests.post(f"{BASE}/api/glaucoma/compare", data={"explain": "true"}, files=vol() + [fund], timeout=120).json()
check("compare runs fundus, OCT and fusion", set(c.get("models", {})) == {"fundus", "oct", "fusion"})
check("compare derives agreement, review flag and risk band",
      all(k in c for k in ("agreement", "needs_review", "risk")) and c["risk"]["level"] in ("low", "elevated", "high"))
check("compare returns a Grad-CAM on request, plus the checkpoint caveat",
      bool(c.get("fundus_heatmap")) and "single-split" in c.get("caveat", "").lower())
check("compare rejects a wrong slice count", requests.post(f"{BASE}/api/glaucoma/compare", files=vol()[:5] + [fund], timeout=60).status_code == 400)
check("compare rejects a fundus-slot OCT image",
      requests.post(f"{BASE}/api/glaucoma/compare", files=[("fundus", ("f.jpg", SLICES[0], "image/jpeg"))] + vol(), timeout=60).status_code == 400)
check("compare requires OCT input", requests.post(f"{BASE}/api/glaucoma/compare", files=[fund], timeout=60).status_code == 400)

# ---- explain ----
fusion = c["models"]["fusion"]
summary = {"module": "multimodal", "prediction": fusion["prediction"], "confidence": fusion["confidence"],
           "probabilities": fusion["probabilities"], "models": {k: v["prediction"] for k, v in c["models"].items()},
           "agreement": c["agreement"], "needs_review": c["needs_review"], "risk": c["risk"]}
e = requests.post(f"{BASE}/api/explain", json={"summary": summary}, timeout=60).json()
check("explain returns text, a source and the disclaimer",
      e.get("source") in ("deepseek", "template") and len(e.get("explanation", "")) > 40 and bool(e.get("disclaimer")), e.get("source", ""))
check("explain rejects an empty summary", requests.post(f"{BASE}/api/explain", json={"summary": {}}, timeout=30).status_code == 422)

# ---- saved cases and patients ----
sid = f"S{tag}"
body = {"patient_id": sid, "module": "multimodal", "title": "GAMMA fusion", "result": fusion["prediction"],
        "confidence": fusion["confidence"], "inputs": "fundus + 8 OCT slices", "explanation": e.get("explanation"),
        "detail": {**c, "input_preview": "data:image/png;base64,AAAA"}}  # images are sent on purpose; the server must drop them
r = requests.post(f"{BASE}/api/cases", json=body, timeout=30)
case = r.json()
check("save case returns 201 with an id", r.status_code == 201 and "id" in case)
stored = requests.get(f"{BASE}/api/cases/{case['id']}", timeout=30).json()
check("a saved case never keeps images", "data:image" not in json.dumps(stored) and "fundus_heatmap" not in stored["detail"])
check("a name is rejected as a study ID", requests.post(f"{BASE}/api/cases", json={**body, "patient_id": "Jane Doe"}, timeout=30).status_code == 422)
check("an unknown module is rejected", requests.post(f"{BASE}/api/cases", json={**body, "module": "x"}, timeout=30).status_code == 422)
pat = requests.get(f"{BASE}/api/patients/{sid}", timeout=30).json()
check("patient history has the case and a trend point", len(pat.get("cases", [])) == 1 and len(pat.get("trend", [])) == 1)
check("patient search finds it", any(p["study_id"] == sid for p in requests.get(f"{BASE}/api/patients", params={"q": tag}, timeout=30).json()))
check("case search finds it", requests.get(f"{BASE}/api/cases", params={"patient_id": sid, "q": "GAMMA"}, timeout=30).json().get("total") == 1)

# ---- PDF reports ----
rp = requests.get(f"{BASE}/api/cases/{case['id']}/report.pdf", timeout=60)
check("PDF from a saved case", rp.status_code == 200 and rp.headers["content-type"] == "application/pdf" and rp.content.startswith(b"%PDF"))
fresh = {k: body[k] for k in ("patient_id", "module", "title", "result", "confidence", "inputs", "explanation")}
rp2 = requests.post(f"{BASE}/api/report.pdf", json={**fresh, "probabilities": fusion["probabilities"], "fundus_heatmap": c["fundus_heatmap"]}, timeout=60)
rp3 = requests.post(f"{BASE}/api/report.pdf", json={**fresh, "probabilities": fusion["probabilities"]}, timeout=60)
check("PDF from a fresh result embeds the Grad-CAM", rp2.content.startswith(b"%PDF") and len(rp2.content) > len(rp3.content))
check("PDF rejects a bad heatmap", requests.post(f"{BASE}/api/report.pdf", json={**fresh, "fundus_heatmap": "data:image/png;base64,AAAA"}, timeout=30).status_code == 422)
d = requests.delete(f"{BASE}/api/patients/{sid}", timeout=30).json()
check("deleting a patient cascades to their cases", d.get("cases_deleted") == 1 and requests.get(f"{BASE}/api/cases/{case['id']}", timeout=30).status_code == 404)


# ---- batch ZIP + CSV ----
def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


ok_id, short_id, single_id = f"S{tag}A", f"S{tag}B", f"S{tag}C"
cases = {f"{ok_id}/fundus.jpg": FUNDUS_BYTES, f"{short_id}/fundus.jpg": FUNDUS_BYTES, f"{single_id}/fundus.jpg": FUNDUS_BYTES,
         f"{single_id}/oct.jpg": SLICES[73], "Jane Doe/fundus.jpg": FUNDUS_BYTES}
cases.update({f"{ok_id}/oct/{n:02d}.jpg": SLICES[i] for n, i in enumerate(IDX)})
cases.update({f"{short_id}/oct/{n:02d}.jpg": SLICES[i] for n, i in enumerate(IDX[:5])})
b = requests.post(f"{BASE}/api/batch", files={"file": ("cases.zip", make_zip(cases), "application/zip")}, data={"save": "true"}, timeout=300).json()
by = {i["study_id"]: i for i in b.get("items", [])}
check("batch: 2 ok and 2 errors out of 4 cases", (b.get("n_ok"), b.get("n_error"), b.get("n_cases")) == (2, 2, 4), str((b.get("n_ok"), b.get("n_error"))))
check("batch explains each error", "8 slices" in by.get(short_id, {}).get("error", "") and "study ID" in by.get("Jane Doe", {}).get("error", ""))
check("batch accepts one OCT B-scan per case", by.get(single_id, {}).get("status") == "ok")
csv_r = requests.get(f"{BASE}/api/batch/{b.get('batch_id', 'b_000000000000')}.csv", timeout=30)
rows = list(csv.reader(io.StringIO(csv_r.text)))
check("batch CSV has the header and one row per case", csv_r.status_code == 200 and rows[0][0] == "study_id" and len(rows) == 5)
check("batch with save=true stored the good cases as patients", requests.get(f"{BASE}/api/patients/{ok_id}", timeout=30).status_code == 200)
check("batch rejects path traversal in the ZIP",
      requests.post(f"{BASE}/api/batch", files={"file": ("x.zip", make_zip({"../evil/fundus.jpg": FUNDUS_BYTES}), "application/zip")}, timeout=60).status_code == 400)
check("batch rejects a non-ZIP upload", requests.post(f"{BASE}/api/batch", files={"file": ("x.zip", b"not a zip", "application/zip")}, timeout=60).status_code == 400)
check("unknown batch id is a 404", requests.get(f"{BASE}/api/batch/b_000000000000.csv", timeout=30).status_code == 404)
for s in (ok_id, single_id):
    requests.delete(f"{BASE}/api/patients/{s}", timeout=30)

print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
