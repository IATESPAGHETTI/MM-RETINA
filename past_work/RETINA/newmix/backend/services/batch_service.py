"""Batch analysis of a ZIP of GAMMA cases. The ZIP is read strictly in memory (nothing is
extracted to disk), so entry names can never write outside anything; we still reject
absolute paths and '..' outright.

Layout (one folder per case, the folder name is the study ID):
    P-001/fundus.jpg
    P-001/oct/00.jpg ... 07.jpg      (8 slices, sorted naturally by file name)   OR   P-001/oct.jpg
A single wrapper folder around all the case folders is tolerated.
"""

from __future__ import annotations

import csv
import io
import posixpath
import re
import uuid
import zipfile

from PIL import Image, UnidentifiedImageError

import core
from services import compare_service, store

MAX_ZIP_BYTES = 150 * 1024 * 1024
MAX_CASES = 100
MAX_TOTAL_UNCOMPRESSED = 600 * 1024 * 1024
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
CSV_COLUMNS = ["study_id", "status", "error", "fusion_prediction", "fusion_confidence", "p_normal", "p_early",
               "p_progressive", "fundus_prediction", "oct_prediction", "all_agree", "needs_review", "risk_level"]
BATCH_ID_RE = re.compile(r"^b_[0-9a-f]{12}$")


class BatchError(Exception):
    """A problem with the ZIP as a whole; the router turns it into HTTP 400."""


def _natural(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _safe_parts(name: str) -> list[str] | None:
    if "\\" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise BatchError(f"unsafe path in ZIP: {name!r}")
    parts = [p for p in posixpath.normpath(name).split("/") if p not in ("", ".")]
    if ".." in parts:
        raise BatchError(f"unsafe path in ZIP: {name!r}")
    if not parts or parts[0] == "__MACOSX" or parts[-1].startswith("."):
        return None
    return parts


def read_zip(data: bytes) -> dict[str, dict]:
    """Returns {study_id: {"fundus": bytes|None, "oct": bytes|None, "slices": [(name, bytes), ...]}}."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise BatchError("not a valid ZIP file")
    zf = zipfile.ZipFile(io.BytesIO(data))
    entries = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = _safe_parts(info.filename)
        if parts and parts[-1].lower().endswith(IMAGE_EXT):
            entries.append((parts, info))
    if not entries:
        raise BatchError("the ZIP contains no images")
    if sum(i.file_size for _, i in entries) > MAX_TOTAL_UNCOMPRESSED:
        raise BatchError("the ZIP expands to more than 600 MB")
    # tolerate one wrapper folder: <wrapper>/<case>/<files>
    if all(len(p) >= 3 for p, _ in entries) and len({p[0] for p, _ in entries}) == 1:
        entries = [(p[1:], i) for p, i in entries]
    if any(len(p) < 2 for p, _ in entries):
        raise BatchError("put each case in its own folder, e.g. P-001/fundus.jpg and P-001/oct/00.jpg")

    cases: dict[str, dict] = {}
    for parts, info in entries:
        sid, rest = parts[0], parts[1:]
        slot = cases.setdefault(sid, {"fundus": None, "oct": None, "slices": []})
        if info.file_size > core.MAX_UPLOAD_BYTES:
            slot.setdefault("errors", []).append(f"{'/'.join(rest)}: larger than {core.MAX_UPLOAD_BYTES // 2**20} MB")
            continue
        stem = posixpath.splitext(rest[-1])[0].lower()
        if len(rest) == 1 and stem == "fundus":
            slot["fundus"] = zf.read(info)
        elif len(rest) == 1 and stem == "oct":
            slot["oct"] = zf.read(info)
        elif len(rest) == 2 and rest[0].lower() == "oct":
            slot["slices"].append((rest[1], zf.read(info)))
        else:
            slot.setdefault("errors", []).append(f"unexpected file {'/'.join(rest)}")
    if len(cases) > MAX_CASES:
        raise BatchError(f"too many cases: {len(cases)} (limit {MAX_CASES})")
    for slot in cases.values():
        slot["slices"].sort(key=lambda t: _natural(t[0]))
    return cases


def _open(data: bytes, label: str) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return img
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError(f"{label}: not a readable image")


def _analyse(study_id: str, slot: dict) -> dict:
    if not store.valid_study_id(study_id):
        return {"study_id": study_id, "status": "error", "error": "folder name is not a valid study ID"}
    if slot.get("errors"):
        return {"study_id": study_id, "status": "error", "error": "; ".join(slot["errors"][:3])}
    try:
        if slot["fundus"] is None:
            raise ValueError("fundus: missing fundus.jpg")
        fundus = _open(slot["fundus"], "fundus")
        slices = [_open(b, f"oct slice {n}") for n, b in slot["slices"]] or None
        single = _open(slot["oct"], "oct") if slot["oct"] is not None and slices is None else None
        out = compare_service.run(fundus, single, slices)
    except ValueError as e:
        return {"study_id": study_id, "status": "error", "error": str(e)}
    m = out["models"]
    return {
        "study_id": study_id, "status": "ok",
        "fusion_prediction": m["fusion"]["prediction"], "fusion_confidence": m["fusion"]["confidence"],
        "probabilities": m["fusion"]["probabilities"],
        "fundus_prediction": m["fundus"]["prediction"], "oct_prediction": m["oct"]["prediction"],
        "all_agree": out["agreement"]["all_agree"], "needs_review": out["needs_review"]["flag"],
        "risk_level": out["risk"]["level"],
        "_detail": {"models": {k: {"prediction": v["prediction"], "probabilities": v["probabilities"]} for k, v in m.items()},
                    "agreement": out["agreement"], "needs_review": out["needs_review"], "risk": out["risk"],
                    "oct_mode": out["oct_mode"]},
        "_inputs": f"fundus + {len(slices)} OCT slices" if slices else "fundus + 1 OCT slice",
    }


def process(data: bytes, save: bool = False) -> dict:
    try:
        cases = read_zip(data)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as e:
        # corrupt entries, bad CRC / lying size headers, encrypted or unsupported compression
        raise BatchError(f"cannot read the ZIP ({type(e).__name__}); re-create it without a password")
    items = []
    for study_id in sorted(cases):
        item = _analyse(study_id, cases[study_id])
        detail, inputs = item.pop("_detail", None), item.pop("_inputs", "")
        if save and item["status"] == "ok":
            store.create_case(study_id, "multimodal", "GAMMA fusion (batch)", item["fusion_prediction"],
                              item["fusion_confidence"], inputs, detail)
            item["saved"] = True
        items.append(item)
    result = {"batch_id": "b_" + uuid.uuid4().hex[:12], "n_cases": len(items),
              "n_ok": sum(i["status"] == "ok" for i in items), "n_error": sum(i["status"] != "ok" for i in items),
              "items": items}
    store.save_batch(result["batch_id"], result)
    return result


def _cell(value) -> str:
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s  # neutralise spreadsheet formula injection


def to_csv(result: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for it in result["items"]:
        p = it.get("probabilities") or {}
        w.writerow([_cell(x) for x in (
            it["study_id"], it["status"], it.get("error"), it.get("fusion_prediction"), it.get("fusion_confidence"),
            p.get("normal"), p.get("early"), p.get("progressive"), it.get("fundus_prediction"), it.get("oct_prediction"),
            it.get("all_agree"), it.get("needs_review"), it.get("risk_level"))])
    return buf.getvalue()
