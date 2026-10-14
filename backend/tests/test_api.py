"""
API contract tests for the inference backend.

Validation paths run with no checkpoints at all (they are rejected before any
model is touched). The real-inference tests are skipped, not faked, when the
gitignored checkpoints in training/checkpoints/ are absent - so a green run
on a fresh clone proves the contract, and a green run on a full checkout also
proves the model path.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as backend_app
import inference


@pytest.fixture(scope="module")
def client():
    # Context manager so the lifespan (model loading) actually runs.
    with TestClient(backend_app.app) as c:
        yield c


def _png(color: tuple[int, int, int], size: int = 96) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


# A saturated, orange-red image passes the "looks like a colour fundus" check;
# mid-grey passes the "looks like an OCT B-scan" check.
FUNDUS_LIKE = _png((200, 90, 40))
OCT_LIKE = _png((110, 110, 110))


def _files(**named: bytes):
    return {k: (f"{k}.png", v, "image/png") for k, v in named.items()}


def test_health_reports_only_models_that_really_loaded(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert set(body["models_loaded"]).isdisjoint(body["model_errors"])
    assert set(body["models_loaded"]) | set(body["model_errors"]) <= {"fundus", "oct", "fusion"}


def test_rejects_unknown_modality(client):
    r = client.post("/api/predict", data={"modality": "mri"})
    assert r.status_code == 400
    assert "modality" in r.json()["detail"]


def test_fundus_modality_requires_a_fundus_image(client):
    r = client.post("/api/predict", data={"modality": "fundus"})
    assert r.status_code == 400
    assert "fundus" in r.json()["detail"]


def test_rejects_non_image_content_type(client):
    r = client.post(
        "/api/predict",
        data={"modality": "fundus"},
        files={"fundus": ("x.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert "unsupported content type" in r.json()["detail"]


def test_rejects_corrupt_image(client):
    r = client.post(
        "/api/predict",
        data={"modality": "fundus"},
        files={"fundus": ("x.png", b"not really a png", "image/png")},
    )
    assert r.status_code == 400
    assert "not a valid image" in r.json()["detail"]


def test_rejects_oversized_upload(client):
    too_big = b"\0" * (backend_app.MAX_UPLOAD_BYTES + 1)
    r = client.post(
        "/api/predict",
        data={"modality": "fundus"},
        files={"fundus": ("big.png", too_big, "image/png")},
    )
    assert r.status_code == 413


def test_rejects_grayscale_image_in_fundus_slot(client):
    r = client.post("/api/predict", data={"modality": "fundus"}, files=_files(fundus=OCT_LIKE))
    assert r.status_code == 400
    assert "grayscale" in r.json()["detail"]


def test_rejects_colour_image_in_oct_slot(client):
    r = client.post("/api/predict", data={"modality": "oct"}, files=_files(oct=FUNDUS_LIKE))
    assert r.status_code == 400
    assert "color-saturated" in r.json()["detail"]


def test_never_fabricates_a_prediction_when_model_is_not_loaded(client):
    if "fundus" in inference._models:
        pytest.skip("fundus checkpoint is present; unloaded-model path not reachable")
    r = client.post("/api/predict", data={"modality": "fundus"}, files=_files(fundus=FUNDUS_LIKE))
    assert r.status_code == 503


@pytest.mark.skipif(
    not all(p.exists() for p in inference.CHECKPOINT_FILES.values()),
    reason="demo checkpoints not present (training/checkpoints/ is gitignored)",
)
class TestRealInference:
    def test_fundus_prediction_shape(self, client):
        r = client.post(
            "/api/predict",
            data={"modality": "fundus", "explain": "true"},
            files=_files(fundus=FUNDUS_LIKE),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["oct_mode"] == "n/a"
        probs = body["probabilities"]
        assert set(probs) == {"normal", "early", "progressive"}
        assert sum(probs.values()) == pytest.approx(1.0, abs=1e-2)
        assert body["prediction"] == max(probs, key=probs.get)
        assert body["fundus_heatmap"].startswith("data:image/png;base64,")

    def test_fusion_with_wrong_slice_count_is_rejected(self, client):
        files = [("oct_slices", (f"s{i}.png", OCT_LIKE, "image/png")) for i in range(3)]
        files.append(("fundus", ("f.png", FUNDUS_LIKE, "image/png")))
        r = client.post("/api/predict", data={"modality": "fusion"}, files=files)
        assert r.status_code == 400
        assert "exactly" in r.json()["detail"]


# --- standalone tabular models (HVF, RNFL/GCC) -------------------------------

RNFL_VALUES = {
    "Average_RNFL": 60, "RNFL_Superior": 70, "RNFL_Inferior": 65, "RNFL_Nasal": 50,
    "RNFL_Temporal": 45, "Average_GCC": 62, "GCC_Superior": 60, "GCC_Inferior": 58,
    "GCC_Supero_nasal": 60, "GCC_Supero_temporal": 60, "GCC_Infero_nasal": 58,
    "GCC_Infero_temporal": 57, "age": 60,
}


def test_tabular_models_load_and_schema_has_reliability(client):
    health = client.get("/api/health").json()
    assert set(health["tabular_loaded"]) == {"hvf", "rnfl_gcc"}, health["tabular_errors"]
    schema = client.get("/api/tabular/schema").json()
    assert schema["hvf"]["reliability"]["tier"] in {"strong", "moderate", "weak", "chance"}
    assert {f["key"] for f in schema["rnfl_gcc"]["features"]} >= {"Average_RNFL", "Average_GCC", "age"}


def test_tabular_prediction_shape_and_explanation(client):
    r = client.post("/api/predict/tabular/rnfl_gcc", json={"values": RNFL_VALUES})
    assert r.status_code == 200, r.text
    body = r.json()
    probs = body["probabilities"]
    assert set(probs) == {"mild", "moderate", "severe"}
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-2)
    assert body["prediction"] == max(probs, key=probs.get)
    assert body["drivers"] and body["reliability"]["tier"]
    assert body["imputed_features"] == []


def test_tabular_reports_imputed_and_out_of_range(client):
    vals = {**RNFL_VALUES, "GCC_Inferior": None, "age": 250}
    body = client.post("/api/predict/tabular/rnfl_gcc", json={"values": vals}).json()
    assert body["imputed_features"] == ["GCC_Inferior"]
    assert [o["feature"] for o in body["out_of_range"]] == ["age"]


def test_tabular_rejects_unknown_feature_and_too_many_missing(client):
    r = client.post("/api/predict/tabular/rnfl_gcc", json={"values": {"bogus": 1}})
    assert r.status_code == 400
    r = client.post("/api/predict/tabular/hvf", json={"values": {"age_years": 60}})
    assert r.status_code == 400 and "missing" in r.json()["detail"]
    assert client.post("/api/predict/tabular/mri", json={"values": {}}).status_code == 404
