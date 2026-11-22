"""PDF report for one analysis (reportlab). No patient identifiers beyond the study ID, and the
only image ever embedded is a Grad-CAM overlay the client sends at report time (never stored)."""

from __future__ import annotations

import base64
import binascii
import io
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import core

MODULE_LABELS = {"glaucoma": "Glaucoma (OCT and clinical features)", "diabetes": "Diabetes (experimental)",
                 "multimodal": "Glaucoma multimodal (GAMMA fundus + OCT)"}
MAX_HEATMAP_BYTES = 2 * 1024 * 1024
_DATA_URL = re.compile(r"^data:image/(?:png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)$")
INK, MUTED, ACCENT, TRACK = colors.HexColor("#0f172a"), colors.HexColor("#64748b"), colors.HexColor("#0e7490"), colors.HexColor("#e2e8f0")


class _Bar(Flowable):
    def __init__(self, value: float, width: float = 70 * mm, height: float = 4 * mm):
        super().__init__()
        self.value, self.width, self.height = max(0.0, min(1.0, value)), width, height

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        self.canv.setFillColor(TRACK)
        self.canv.roundRect(0, 0, self.width, self.height, 2, stroke=0, fill=1)
        self.canv.setFillColor(ACCENT)
        self.canv.roundRect(0, 0, max(self.width * self.value, 1), self.height, 2, stroke=0, fill=1)


def decode_heatmap(data_url: str) -> bytes:
    """Validates a data URL, decodes it, and re-encodes as a clean PNG. Raises ValueError."""
    m = _DATA_URL.match((data_url or "").strip())
    if not m:
        raise ValueError("fundus_heatmap must be a data:image/...;base64 URL")
    try:
        raw = base64.b64decode(m.group(1), validate=False)
    except (binascii.Error, ValueError):
        raise ValueError("fundus_heatmap is not valid base64")
    if len(raw) > MAX_HEATMAP_BYTES:
        raise ValueError("fundus_heatmap is larger than 2 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        out = io.BytesIO()
        img.convert("RGB").save(out, format="PNG")
    except Exception:  # noqa: BLE001 - any decode failure is a client error
        raise ValueError("fundus_heatmap is not a readable image")
    return out.getvalue()


def _probabilities(data: dict) -> dict:
    detail = data.get("detail") or {}
    return (data.get("probabilities") or detail.get("probabilities")
            or (detail.get("models") or {}).get("fusion", {}).get("probabilities") or {})


def _flags(data: dict) -> list[str]:
    detail = data.get("detail") or {}
    flags = list(data.get("flags") or [])
    review = detail.get("needs_review") or {}
    if review.get("flag") and not flags:
        flags = ["Flagged for specialist review: " + "; ".join(str(r) for r in review.get("reasons", []))]
    return [str(f)[:200] for f in flags[:10]]


def _p(text, style) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def build_pdf(data: dict, heatmap_png: bytes | None = None) -> bytes:
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, textColor=INK, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=11, textColor=ACCENT,
                        spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10, leading=14, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=MUTED)
    big = ParagraphStyle("big", parent=body, fontSize=20, leading=24, fontName="Helvetica-Bold")

    when = data.get("created_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    module = data.get("module", "")
    story: list = [_p("Retina Suite - analysis report", h1), _p("Research prototype. Not a medical device.", small), Spacer(1, 6)]

    meta = Table([[_p("Study ID", small), _p(data.get("patient_id", "-"), body)],
                  [_p("Module", small), _p(MODULE_LABELS.get(module, module), body)],
                  [_p("Date (UTC)", small), _p(when, body)],
                  [_p("Inputs", small), _p(data.get("inputs") or "-", body)]], colWidths=[28 * mm, 140 * mm])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, TRACK),
                              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [meta, _p("Result", h2), _p(data.get("title", ""), small), _p(str(data.get("result", "")).upper(), big)]
    if data.get("confidence") is not None:
        story.append(_p(f"Model confidence: {float(data['confidence']) * 100:.0f}%", body))

    probs = _probabilities(data)
    if probs:
        rows = [[_p(k.capitalize(), body), _p(f"{float(v) * 100:.1f}%", body), _Bar(float(v))] for k, v in probs.items()]
        t = Table(rows, colWidths=[35 * mm, 22 * mm, 75 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        story += [_p("Class probabilities", h2), t]

    flags = _flags(data)
    if flags:
        story += [_p("Review flags", h2)] + [_p("- " + f, body) for f in flags]

    if data.get("explanation"):
        story += [_p("Plain-language explanation", h2), _p(data["explanation"], body),
                  _p("AI-generated text. Not medical advice.", small)]

    if heatmap_png:
        img = RLImage(io.BytesIO(heatmap_png), width=52 * mm, height=52 * mm, kind="proportional")
        story += [_p("Grad-CAM overlay (fundus)", h2), img,
                  _p("Highlights image regions that most influenced the model. It is not a lesion detector.", small)]

    story += [Spacer(1, 8), _p(core.DISCLAIMER, small)]
    if module == "multimodal":
        story.append(_p(core.GAMMA_CAVEAT, small))
    if module == "diabetes":
        story.append(_p("Experimental: the HbA1c estimate shipped without validation and is not a lab value.", small))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "Retina Suite research prototype")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="Retina Suite analysis report", author="Retina Suite").build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
