"""Unified retinal-analysis API: glaucoma (OCT, clinical, multimodal) + diabetes.

Run from this folder:   uvicorn app:app --port 8000
No authentication on purpose (prototype); put it behind one before real use.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

os.environ.setdefault("KERAS_BACKEND", "torch")  # Kartik's Keras-3 models run on torch; no TensorFlow
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routers import diabetes, glaucoma, system  # noqa: E402
from services import clinical_service, defer_service, diabetes_service, gamma_service, oct_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("newmix")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for name, fn in (("deferral cut-offs", defer_service.load), ("OCT model", oct_service.load), ("clinical models", clinical_service.load),
                     ("GAMMA multimodal", gamma_service.load), ("diabetes models", diabetes_service.load)):
        try:
            log.info("loaded %s: %s", name, fn())
        except Exception:  # noqa: BLE001 - one failing module must not take the others down
            log.exception("failed to load %s", name)
    yield


app = FastAPI(title="Retina Suite API", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(system.router)
app.include_router(glaucoma.router)
app.include_router(diabetes.router)
# the original /demo page posts here
app.add_api_route("/api/predict", glaucoma.multimodal, methods=["POST"], tags=["legacy"])
