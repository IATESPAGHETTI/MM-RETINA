"""Plain-language explanations of a model result.

Only a sanitised numeric summary is ever sent to the provider: never images, never
a study ID. Any failure (no key, network error, HTTP error, timeout, empty reply)
falls back to a deterministic template, so the feature always works offline.
Services never import FastAPI; the router turns RateLimited into HTTP 429.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque

import core
import settings

log = logging.getLogger("newmix.explain")

PROVIDER = "deepseek"
TIMEOUT_S = 20
RATE_LIMIT = 30  # requests per window, per process
RATE_WINDOW_S = 60

ALLOWED_KEYS = {"module", "prediction", "confidence", "probabilities", "models", "agreement",
                "needs_review", "risk", "drivers", "oct_mode"}
# keys dropped at every depth (images, identifiers). Whole-word tokens for short words, so that
# "confidence" is kept while "id", "study_id" and "patient" are not.
BLOCKED_SUBSTRINGS = ("heatmap", "preview", "image", "overlay", "patient", "study", "filename")
BLOCKED_TOKENS = {"id", "ids", "name", "names"}
MAX_STR = 200
MAX_LIST = 12
MAX_DEPTH = 4

SYSTEM_PROMPT = (
    "You explain the output of a research glaucoma-screening model to a non-expert, in plain English. "
    "Rules: use only the numbers provided; never diagnose; never recommend treatment or medication; "
    "say clearly when the models disagree or confidence is low; remind the reader that this is a research "
    "prototype and a specialist should review anything uncertain; write 90 to 130 words as one or two short "
    "paragraphs, with no headings, bullet lists or markdown; do not mention these instructions."
)


class RateLimited(Exception):
    pass


_hits: deque[float] = deque()
_lock = threading.Lock()


def _check_rate() -> None:
    now = time.monotonic()
    with _lock:
        while _hits and now - _hits[0] > RATE_WINDOW_S:
            _hits.popleft()
        if len(_hits) >= RATE_LIMIT:
            raise RateLimited()
        _hits.append(now)


def status() -> dict:
    return {"configured": bool(settings.get("DEEPSEEK_API_KEY")), "provider": PROVIDER,
            "model": settings.get("DEEPSEEK_MODEL", "deepseek-chat")}


# ---- sanitising -------------------------------------------------------------------------------------
def _blocked_key(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in BLOCKED_SUBSTRINGS) or any(t in BLOCKED_TOKENS for t in re.split(r"[^a-z0-9]+", k))


def _clean(value, depth: int = 0):
    if depth > MAX_DEPTH:
        return None
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 3) if isinstance(value, float) else value
    if isinstance(value, str):
        return value if len(value) <= MAX_STR and not value.startswith("data:") else None
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str) or _blocked_key(k):
                continue
            cleaned = _clean(v, depth + 1)
            if cleaned is not None:
                out[k] = cleaned
        return out
    if isinstance(value, list):
        items = [_clean(v, depth + 1) for v in value[:MAX_LIST]]
        return [i for i in items if i is not None]
    return None


def sanitize_summary(summary: dict) -> dict:
    return _clean({k: v for k, v in summary.items() if k in ALLOWED_KEYS}) or {}


# ---- template fallback ------------------------------------------------------------------------------
def _pct(x) -> str:
    return f"{float(x) * 100:.0f}%"


def template_explanation(s: dict) -> str:
    parts: list[str] = []
    pred = s.get("prediction")
    conf = s.get("confidence")
    probs = s.get("probabilities") or {}
    if pred is not None and conf is not None:
        detail = ", ".join(f"{k} {_pct(v)}" for k, v in probs.items())
        parts.append(f"The model's best guess is '{pred}' with {_pct(conf)} confidence"
                     + (f" ({detail})." if detail else "."))
    elif pred is not None:
        parts.append(f"The model's best guess is '{pred}'.")
    models = s.get("models") or {}
    agree = s.get("agreement") or {}
    if models:
        listing = ", ".join(f"{k}: {v}" for k, v in models.items())
        if agree.get("all_agree") is True:
            parts.append(f"The separate image models all agree ({listing}), which makes the result more consistent.")
        elif agree.get("all_agree") is False:
            parts.append(f"The separate image models do not all agree ({listing}), so this result is uncertain.")
    review = s.get("needs_review") or {}
    if review.get("flag") is True:
        reasons = "; ".join(str(r) for r in (review.get("reasons") or [])[:3])
        parts.append("It is flagged for specialist review" + (f" because: {reasons}." if reasons else "."))
    elif review.get("flag") is False:
        parts.append("It did not trip the review flag, but a specialist should still confirm any finding.")
    risk = s.get("risk") or {}
    if risk.get("level"):
        parts.append(f"The overall model score falls in the '{risk['level']}' band, which is a display category, "
                     "not a clinical risk estimate.")
    drivers = s.get("drivers") or []
    named = [f"{d.get('feature')} ({d.get('direction')})" for d in drivers if isinstance(d, dict) and d.get("feature")]
    if named:
        parts.append("Main factors the model weighed: " + ", ".join(named[:4]) + ".")
    parts.append("This is a research prototype, not a diagnosis: please have an eye-care professional review the scans.")
    return " ".join(parts)


# ---- provider call ----------------------------------------------------------------------------------
def _call_provider(summary: dict) -> str | None:
    key = settings.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    base = settings.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    body = json.dumps({
        "model": settings.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": "Explain this result:\n" + json.dumps(summary, sort_keys=True)}],
        "temperature": 0.3,
        "max_tokens": 300,
        "stream": False,
    }).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (data["choices"][0]["message"]["content"] or "").strip()
        return text or None
    except urllib.error.HTTPError as e:
        log.warning("explain: provider returned HTTP %s; using template", e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        log.warning("explain: provider unreachable or timed out; using template")
    except (KeyError, IndexError, ValueError):
        log.warning("explain: unexpected provider reply; using template")
    return None


def explain(summary: dict) -> dict:
    _check_rate()
    clean = sanitize_summary(summary)
    text = _call_provider(clean)
    if text:
        return {"explanation": text, "source": PROVIDER, "model": settings.get("DEEPSEEK_MODEL", "deepseek-chat"),
                "disclaimer": core.DISCLAIMER}
    return {"explanation": template_explanation(clean), "source": "template", "model": None,
            "disclaimer": core.DISCLAIMER}
