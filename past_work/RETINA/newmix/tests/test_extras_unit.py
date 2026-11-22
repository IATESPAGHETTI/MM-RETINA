"""Unit tests for the Retina Suite extras (comparison logic, store, explain, batch ZIP, PDF).

No server and no model checkpoints needed:
    python tests/test_extras_unit.py        (plain asserts, exits non-zero on failure)
    python -m pytest tests/test_extras_unit.py   (also works if pytest is installed)
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["SUITE_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["DEEPSEEK_API_KEY"] = ""  # tests must never call the real provider

from PIL import Image  # noqa: E402

from services import batch_service, compare_service, explain_service, report_service, store  # noqa: E402


def _jpg(color=(120, 60, 40), size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


# ---- comparison logic -------------------------------------------------------------------------------
def test_agreement_all_agree():
    a = compare_service.agreement({"fundus": "normal", "oct": "normal", "fusion": "normal"})
    assert a["all_agree"] and a["majority"] == "normal" and a["outliers"] == []
    assert a["banner"] == "All 3 models agree on normal"


def test_agreement_two_vs_one():
    a = compare_service.agreement({"fundus": "early", "oct": "normal", "fusion": "early"})
    assert not a["all_agree"] and a["n_agree"] == 2 and a["majority"] == "early" and a["outliers"] == ["oct"]
    assert a["banner"] == "2 of 3 models agree on early; oct disagrees"


def test_agreement_all_differ():
    a = compare_service.agreement({"fundus": "early", "oct": "normal", "fusion": "progressive"})
    assert not a["all_agree"] and a["majority"] is None and a["outliers"] == []
    assert a["banner"] == "All 3 models disagree"


def test_review_flags():
    agree = {"all_agree": True}
    assert compare_service.review(agree, 0.9) == {"flag": False, "reasons": [], "confidence_threshold": 0.6}
    r = compare_service.review({"all_agree": False}, 0.48)
    assert r["flag"] and r["reasons"] == ["models disagree", "low fusion confidence (0.48 < 0.60)"]
    assert compare_service.review(agree, 0.59)["flag"] and not compare_service.review(agree, 0.60)["flag"]


def test_risk_bands():
    def lvl(p_normal):
        return compare_service.risk({"normal": p_normal})["level"]

    assert lvl(0.9) == "low" and lvl(0.66) == "low"
    assert lvl(0.65) == "elevated" and lvl(0.4) == "elevated"
    assert lvl(0.35) == "high" and lvl(0.1) == "high"
    assert compare_service.risk({"normal": 0.41})["score"] == 0.59


# ---- store ------------------------------------------------------------------------------------------
def test_store_roundtrip_privacy_and_cascade():
    store.init()
    assert store.status() == {"ready": True}
    detail = {"probabilities": {"normal": 0.4}, "fundus_heatmap": "data:image/png;base64,AAAA", "input_preview": "x",
              "nested": {"overlay_png": "zzz", "keep": 1}, "blob": "data:image/jpeg;base64,BBBB"}
    c = store.create_case("P-001", "multimodal", "GAMMA fusion", "early", 0.48, "fundus + 8 slices", detail, "text")
    got = store.get_case(c["id"])
    assert got["detail"] == {"probabilities": {"normal": 0.4}, "nested": {"keep": 1}, "blob": None}, got["detail"]
    store.create_case("P-001", "glaucoma", "OCT", "moderate", 0.7)
    store.create_case("P-002", "diabetes", "Vessels", "low", None)
    pts = {p["study_id"]: p for p in store.list_patients()}
    assert pts["P-001"]["case_count"] == 2 and pts["P-001"]["last_module"] == "glaucoma"
    assert [p["study_id"] for p in store.list_patients("P-00")] == ["P-002", "P-001"] or len(store.list_patients("P-00")) == 2
    assert len(store.list_patients("%")) == 0, "LIKE wildcards must be escaped"
    detail_p = store.get_patient("P-001")
    assert [t["result"] for t in detail_p["trend"]] == ["early", "moderate"] and "detail" not in detail_p["cases"][0]
    items, total = store.list_cases(patient_id="P-001", limit=1)
    assert total == 2 and len(items) == 1 and "detail" not in items[0]
    assert store.delete_patient("P-001") == 2 and store.get_case(c["id"]) is None and store.delete_patient("P-001") is None


def test_store_rejects_names_and_bad_modules():
    store.init()
    for bad in ("Jane Doe", "john@example.com", "", "-lead", "x" * 33, "a/b", "1990-05-12 anna"):
        try:
            store.create_case(bad, "glaucoma", "t", "r")
        except ValueError:
            continue
        raise AssertionError(f"study id {bad!r} should have been rejected")
    try:
        store.create_case("P-9", "nonsense", "t", "r")
        raise AssertionError("bad module accepted")
    except ValueError:
        pass
    try:
        store.create_case("P-9", "glaucoma", "t", "r", detail={"k": ["x" * 100] * 4000})  # ~400 KB of short strings
        raise AssertionError("oversized detail accepted")
    except ValueError:
        pass
    # a single huge string (e.g. a raw base64 blob) is dropped rather than stored
    c = store.create_case("P-9", "glaucoma", "t", "r", detail={"blob": "x" * 300_000, "ok": 1})
    assert c["detail"] == {"blob": None, "ok": 1}


# ---- explain ----------------------------------------------------------------------------------------
def test_explain_sanitiser_keeps_confidence_drops_identifiers():
    s = explain_service.sanitize_summary({"prediction": "early", "confidence": 0.4812, "study_id": "P-1", "patient_id": "P-1",
                                          "fundus_heatmap": "data:image/png;base64,AA", "unknown": 1,
                                          "needs_review": {"flag": True, "reasons": ["ok", "y" * 500]}})
    assert s == {"prediction": "early", "confidence": 0.481, "needs_review": {"flag": True, "reasons": ["ok"]}}, s


def test_explain_falls_back_to_template_without_key_and_rate_limits():
    explain_service._hits.clear()
    r = explain_service.explain({"prediction": "early", "confidence": 0.48, "models": {"fundus": "early", "oct": "normal"},
                                 "agreement": {"all_agree": False}, "needs_review": {"flag": True, "reasons": ["models disagree"]}})
    assert r["source"] == "template" and r["model"] is None and "research prototype" in r["explanation"].lower()
    assert r["disclaimer"]
    old = explain_service.RATE_LIMIT
    try:
        explain_service.RATE_LIMIT, _ = 2, explain_service._hits.clear()
        explain_service.explain({"prediction": "normal"})
        explain_service.explain({"prediction": "normal"})
        try:
            explain_service.explain({"prediction": "normal"})
            raise AssertionError("rate limit not enforced")
        except explain_service.RateLimited:
            pass
    finally:
        explain_service.RATE_LIMIT = old
        explain_service._hits.clear()


# ---- batch ZIP --------------------------------------------------------------------------------------
def test_zip_layout_natural_sort_and_wrapper():
    files = {"cases/P-001/fundus.jpg": _jpg(), "cases/P-001/oct/10.jpg": _jpg(), "cases/P-001/oct/2.jpg": _jpg(),
             "cases/P-001/oct/1.jpg": _jpg(), "cases/P-002/fundus.jpg": _jpg(), "cases/P-002/oct.jpg": _jpg(),
             "__MACOSX/cases/._junk.jpg": b"x", "cases/P-001/.DS_Store": b"x"}
    cases = batch_service.read_zip(_zip(files))
    assert sorted(cases) == ["P-001", "P-002"]
    assert [n for n, _ in cases["P-001"]["slices"]] == ["1.jpg", "2.jpg", "10.jpg"], "natural sort, not lexicographic"
    assert cases["P-002"]["oct"] is not None and cases["P-002"]["slices"] == []


def test_zip_rejects_traversal_absolute_and_junk():
    for name in ("../evil/fundus.jpg", "P-1/../../x.jpg", "/abs/fundus.jpg", "C:/x/fundus.jpg"):
        try:
            batch_service.read_zip(_zip({name: _jpg()}))
            raise AssertionError(f"{name!r} accepted")
        except batch_service.BatchError:
            pass
    # zipfile itself rewrites '\' to '/' when writing on Windows, so check the path validator directly
    for name in ("P-1\\fundus.jpg", "..\\x.jpg", "a/../../b.jpg"):
        try:
            batch_service._safe_parts(name)
            raise AssertionError(f"{name!r} accepted")
        except batch_service.BatchError:
            pass
    for bad in (b"not a zip", _zip({"readme.txt": b"hi"}), _zip({"fundus.jpg": _jpg()})):
        try:
            batch_service.read_zip(bad)
            raise AssertionError("bad zip accepted")
        except batch_service.BatchError:
            pass


def test_corrupt_zip_is_a_clean_error_not_a_crash():
    raw = bytearray(_zip({"P-1/fundus.jpg": _jpg(size=(256, 256)), "P-1/oct.jpg": _jpg(size=(256, 256))}))
    mid = len(raw) // 3
    raw[mid:mid + 40] = b"\xff" * 40  # damage compressed data so the CRC check fails
    try:
        batch_service.process(bytes(raw))
        raise AssertionError("corrupt ZIP accepted")
    except batch_service.BatchError as e:
        assert "cannot read the ZIP" in str(e) or "not a valid ZIP" in str(e), str(e)


def test_unreadable_image_is_a_per_case_error():
    item = batch_service._analyse("P-1", {"fundus": b"definitely not an image", "oct": None, "slices": []})
    assert item["status"] == "error" and "not a readable image" in item["error"]
    item = batch_service._analyse("Jane Doe", {"fundus": _jpg(), "oct": None, "slices": []})
    assert item["status"] == "error" and "study ID" in item["error"]


def test_zip_case_limit():
    files = {f"P-{i:03d}/fundus.jpg": b"x" for i in range(batch_service.MAX_CASES + 1)}
    try:
        batch_service.read_zip(_zip(files))
        raise AssertionError("case limit not enforced")
    except batch_service.BatchError as e:
        assert "too many cases" in str(e)


def test_csv_header_and_formula_injection():
    result = {"items": [{"study_id": "P-1", "status": "error", "error": "=HYPERLINK(\"http://x\")"},
                        {"study_id": "P-2", "status": "ok", "fusion_prediction": "early", "fusion_confidence": 0.5,
                         "probabilities": {"normal": 0.3, "early": 0.5, "progressive": 0.2}, "fundus_prediction": "early",
                         "oct_prediction": "normal", "all_agree": False, "needs_review": True, "risk_level": "elevated"}]}
    import csv
    rows = list(csv.reader(io.StringIO(batch_service.to_csv(result))))
    assert rows[0] == batch_service.CSV_COLUMNS
    assert rows[1][2].startswith("'="), "formula cell must be neutralised"
    assert rows[2] == ["P-2", "ok", "", "early", "0.5", "0.3", "0.5", "0.2", "early", "normal", "False", "True", "elevated"]


# ---- PDF --------------------------------------------------------------------------------------------
def test_pdf_builds_with_and_without_heatmap_and_escapes_markup():
    base = {"patient_id": "P-001", "module": "multimodal", "title": "<b>GAMMA</b> & fusion", "result": "early",
            "confidence": 0.48, "inputs": "fundus + 8 slices", "explanation": "a <script> & b",
            "detail": {"probabilities": {"normal": 0.41, "early": 0.48, "progressive": 0.11},
                       "needs_review": {"flag": True, "reasons": ["models disagree"]}}}
    pdf = report_service.build_pdf(base)
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, format="PNG")
    import base64
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    with_img = report_service.build_pdf(base, report_service.decode_heatmap(url))
    assert with_img.startswith(b"%PDF") and len(with_img) > len(pdf)


def test_heatmap_decoder_rejects_bad_input():
    for bad in ("", "http://x/y.png", "data:text/html;base64,AAAA", "data:image/png;base64,!!!!",
                "data:image/png;base64," + "A" * 40, "data:image/png;base64," + "A" * (3 * 1024 * 1024)):
        try:
            report_service.decode_heatmap(bad)
            raise AssertionError(f"accepted {bad[:30]!r}")
        except ValueError:
            pass


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"[FAIL] {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
