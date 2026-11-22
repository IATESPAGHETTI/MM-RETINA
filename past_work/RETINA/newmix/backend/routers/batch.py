"""Batch ZIP analysis (GAMMA multimodal) with CSV export."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool

from services import batch_service, compare_service, store

router = APIRouter(prefix="/api", tags=["batch"])


@router.post("/batch")
async def run_batch(file: UploadFile = File(...), save: bool = Form(False)):
    data = await file.read(batch_service.MAX_ZIP_BYTES + 1)
    if len(data) > batch_service.MAX_ZIP_BYTES:
        raise HTTPException(413, "ZIP is larger than 150 MB")
    try:
        return await run_in_threadpool(batch_service.process, data, save)
    except batch_service.BatchError as e:
        raise HTTPException(400, str(e))
    except compare_service.ModelsNotReady as e:
        raise HTTPException(503, f"{e}; see /api/health")


def _get_or_404(batch_id: str) -> dict:
    result = store.get_batch(batch_id) if batch_service.BATCH_ID_RE.match(batch_id) else None
    if result is None:
        raise HTTPException(404, "batch not found")
    return result


@router.get("/batch/{batch_id}.csv")
def batch_csv(batch_id: str):
    csv_text = batch_service.to_csv(_get_or_404(batch_id))
    return Response(content=csv_text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{batch_id}.csv"'})


@router.get("/batch/{batch_id}")
def batch_json(batch_id: str):
    return _get_or_404(batch_id)
