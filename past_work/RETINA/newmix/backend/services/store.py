"""SQLite persistence for saved cases and batch results (standard library only).

Privacy by construction: patients are identified by a study ID matching STUDY_ID_RE
(no names, no dates of birth), and images are never stored: `strip_images` removes
heatmaps, previews and data URLs from anything a client sends as `detail`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import settings

STUDY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
MODULES = ("glaucoma", "diabetes", "multimodal")
MAX_DETAIL_BYTES = 256 * 1024
MAX_STR = 5000

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(
    study_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(study_id) ON DELETE CASCADE,
    module TEXT NOT NULL CHECK(module IN ('glaucoma','diabetes','multimodal')),
    title TEXT NOT NULL,
    result TEXT NOT NULL,
    confidence REAL,
    inputs TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '{}',
    explanation TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cases_patient ON cases(patient_id, created_at);
CREATE TABLE IF NOT EXISTS batches(
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    result TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _db():
    conn = sqlite3.connect(settings.db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    path = settings.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    gi = path.parent / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n")  # never let the database (or its journal) reach git
    with _db() as c:
        c.executescript(SCHEMA)


def status() -> dict:
    try:
        with _db() as c:
            c.execute("SELECT 1 FROM cases LIMIT 1")
        return {"ready": True}
    except sqlite3.Error:
        return {"ready": False}


# ---- validation / sanitising ------------------------------------------------------------------------
def valid_study_id(value: str) -> bool:
    return bool(STUDY_ID_RE.match(value or ""))


def strip_images(obj):
    """Recursively drop anything that could be an image: heatmap/preview/overlay keys, data URLs, huge strings."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if "heatmap" in kl or kl.endswith("preview") or "overlay" in kl or "thumbnail" in kl:
                continue
            out[str(k)] = strip_images(v)
        return out
    if isinstance(obj, list):
        return [strip_images(v) for v in obj]
    if isinstance(obj, str) and (obj.startswith("data:") or len(obj) > MAX_STR):
        return None
    return obj


# ---- row mapping ------------------------------------------------------------------------------------
def _case(row: sqlite3.Row, with_detail: bool = True) -> dict:
    out = {"id": row["id"], "patient_id": row["patient_id"], "module": row["module"], "title": row["title"],
           "result": row["result"], "confidence": row["confidence"], "inputs": row["inputs"],
           "explanation": row["explanation"], "created_at": row["created_at"]}
    if with_detail:
        out["detail"] = json.loads(row["detail"] or "{}")
    return out


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


# ---- cases ------------------------------------------------------------------------------------------
def create_case(patient_id: str, module: str, title: str, result: str, confidence: float | None = None,
                inputs: str = "", detail: dict | None = None, explanation: str | None = None) -> dict:
    if not valid_study_id(patient_id):
        raise ValueError("patient_id must be a study ID: letters, digits, '-' or '_', 1 to 32 characters")
    if module not in MODULES:
        raise ValueError(f"module must be one of {list(MODULES)}")
    clean = strip_images(detail or {})
    blob = json.dumps(clean)
    if len(blob.encode()) > MAX_DETAIL_BYTES:
        raise ValueError("detail is too large")
    ts = now()
    with _db() as c:
        c.execute("INSERT OR IGNORE INTO patients(study_id, created_at) VALUES(?, ?)", (patient_id, ts))
        cur = c.execute(
            "INSERT INTO cases(patient_id, module, title, result, confidence, inputs, detail, explanation, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (patient_id, module, title, result, confidence, inputs, blob, explanation, ts))
        row = c.execute("SELECT * FROM cases WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _case(row)


def get_case(case_id: int) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return _case(row) if row else None


def list_cases(patient_id: str | None = None, q: str | None = None, module: str | None = None,
               limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    where, args = [], []
    if patient_id:
        where.append("patient_id = ?")
        args.append(patient_id)
    if module:
        where.append("module = ?")
        args.append(module)
    if q:
        where.append("(title LIKE ? ESCAPE '\\' OR result LIKE ? ESCAPE '\\' OR patient_id LIKE ? ESCAPE '\\')")
        args += [_like(q)] * 3
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    with _db() as c:
        total = c.execute(f"SELECT COUNT(*) FROM cases {clause}", args).fetchone()[0]
        rows = c.execute(f"SELECT * FROM cases {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                         [*args, limit, offset]).fetchall()
    return [_case(r, with_detail=False) for r in rows], total


def delete_case(case_id: int) -> bool:
    with _db() as c:
        return c.execute("DELETE FROM cases WHERE id = ?", (case_id,)).rowcount > 0


# ---- patients ---------------------------------------------------------------------------------------
def list_patients(q: str | None = None) -> list[dict]:
    sql = (
        "SELECT p.study_id, p.created_at,"
        " (SELECT COUNT(*) FROM cases c WHERE c.patient_id = p.study_id) AS case_count,"
        " (SELECT created_at FROM cases c WHERE c.patient_id = p.study_id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_case_at,"
        " (SELECT result FROM cases c WHERE c.patient_id = p.study_id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_result,"
        " (SELECT module FROM cases c WHERE c.patient_id = p.study_id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_module"
        " FROM patients p"
    )
    args: list = []
    if q:
        sql += " WHERE p.study_id LIKE ? ESCAPE '\\'"
        args.append(_like(q))
    sql += " ORDER BY COALESCE(last_case_at, p.created_at) DESC, p.study_id"
    with _db() as c:
        rows = c.execute(sql, args).fetchall()
    return [{"study_id": r["study_id"], "case_count": r["case_count"], "last_case_at": r["last_case_at"],
             "last_result": r["last_result"], "last_module": r["last_module"]} for r in rows]


def get_patient(study_id: str) -> dict | None:
    with _db() as c:
        p = c.execute("SELECT * FROM patients WHERE study_id = ?", (study_id,)).fetchone()
        if not p:
            return None
        rows = c.execute("SELECT * FROM cases WHERE patient_id = ? ORDER BY created_at DESC, id DESC",
                         (study_id,)).fetchall()
    cases = [_case(r, with_detail=False) for r in rows]
    trend = [{"at": r["created_at"], "module": r["module"], "result": r["result"], "confidence": r["confidence"]}
             for r in reversed(rows)]
    return {"study_id": study_id, "created_at": p["created_at"], "cases": cases, "trend": trend}


def delete_patient(study_id: str) -> int | None:
    with _db() as c:
        if not c.execute("SELECT 1 FROM patients WHERE study_id = ?", (study_id,)).fetchone():
            return None
        n = c.execute("SELECT COUNT(*) FROM cases WHERE patient_id = ?", (study_id,)).fetchone()[0]
        c.execute("DELETE FROM patients WHERE study_id = ?", (study_id,))  # cases cascade
    return n


# ---- batches ----------------------------------------------------------------------------------------
def save_batch(batch_id: str, result: dict) -> None:
    with _db() as c:
        c.execute("INSERT INTO batches(id, created_at, result) VALUES(?,?,?)", (batch_id, now(), json.dumps(result)))


def get_batch(batch_id: str) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT result FROM batches WHERE id = ?", (batch_id,)).fetchone()
    return json.loads(row["result"]) if row else None
