# RNFL/GCC workbook provenance audit

Requested check: can a real patient/eye/date identifier be recovered from
`Glaucoma AI.xlsx` itself (delivered twice, identically, at
`dataset_baseline/Augmented_Multimodal/RNFL_GCC/Glaucoma AI.xlsx` and
`dataset/hvf_and)rnfl_gcc/RNFL and GCC data/Glaucoma AI.xlsx`), by
inspecting hidden sheets, workbook metadata, formulas, comments, embedded
objects, defined names, and filenames — rather than the visible grid alone
(which only has `SI NO`, `Age`, `Gender`, `Eye`, `Glaucoma_Severity`, and
the RNFL/GCC measurement columns).

**First confirmed: the two delivered copies are byte-identical** at the
worksheet-XML level (`xl/worksheets/sheet1.xml` diffs clean) — this is one
file, delivered twice, not two independent exports to cross-reference.

An XLSX is a zip of XML parts, so every part was opened directly (not
through Excel/pandas, which only render the visible grid) via
`zipfile`/`openpyxl` on the raw file. Full contents of the archive:

```
[Content_Types].xml
_rels/.rels
xl/_rels/workbook.xml.rels
xl/workbook.xml
xl/sharedStrings.xml
xl/worksheets/_rels/sheet1.xml.rels
xl/theme/theme1.xml
xl/styles.xml
xl/worksheets/sheet1.xml
docProps/core.xml
xl/printerSettings/printerSettings1.bin
docProps/app.xml
```

## Checks performed and results

| Check | Method | Result |
|---|---|---|
| Hidden/very-hidden sheets | `xl/workbook.xml` `<sheets>` | Only `Sheet1` exists; not hidden (`docProps/app.xml` confirms `Worksheets: 1`) |
| Hidden rows/columns | `xl/worksheets/sheet1.xml` — no `hidden="1"` on any `<row>`; no `<cols>` element at all | None. Nothing hidden. |
| Data extends beyond the visible A1:Q172 grid | `<dimension ref="A1:Q172"/>` | Dimension exactly matches the visible table — no extra populated cells anywhere on the sheet |
| Formulas (could reference an external source workbook/ID) | Searched `sheet1.xml` for `<f>` elements | **Zero formulas** — every cell is a static pasted value, not a live link to another file |
| Cell comments / notes | No `xl/comments*.xml` part exists in the archive at all | No comments were ever added |
| Embedded objects / linked files / hyperlinks | No `legacyDrawing`, no OLE parts; `sheet1.xml.rels` contains only a printer-settings relationship; `docProps/app.xml` reports `HyperlinksChanged: false`, `LinksUpToDate: false` (no links) | No embedded or linked files |
| Defined names (named ranges can leak structure) | `xl/workbook.xml` `<definedNames>` | One: `_xlnm._FilterDatabase` = `Sheet1!$A$1:$Q$172` — just an AutoFilter over the visible range, not a hidden reference to anything else |
| Extra/orphaned text strings (could reveal a name, ID, or comment not shown in the grid) | Full `xl/sharedStrings.xml` dump | Exactly 24 unique strings, `uniqueCount="24"`, and every one of them is a header or a categorical value already visible (`SI NO`, `Age`, `Gender`, `Eye`, `Glaucoma_Severity`, the 12 RNFL/GCC column names, `Male`/`Female`, `OD`/`OS`, `MILD`/`MODERATE`/`SEVERE`) — nothing extra |
| Author / company / creator metadata | `docProps/core.xml`, `docProps/app.xml` | `dc:creator` and `cp:lastModifiedBy` are both **empty strings**; `Company` is empty; `Application: Microsoft Excel` is the only populated field |
| Creation/modification dates | `docProps/core.xml` | `created: 2006-09-16` — Excel's generic default timestamp for a workbook with stripped/never-set creation metadata, not a real creation date; `modified: 2026-07-03` — just reflects when it was last saved before delivery, no identifying information |
| Zip-internal per-file timestamps | `ZipFile.infolist()` | All parts stamped `1980-01-01 00:00:00` — the archive was repacked/normalized by some tool before delivery (further evidence this isn't a pristine, untouched original export) |
| Filename itself | `Glaucoma AI.xlsx` | Generic; carries no patient, site, or date information |

## One inconclusive detail

`sheet1.xml`'s saved cursor position is `activeCell="X9" sqref="X9"` —
column X is 15 columns to the right of the last populated column (Q). This
is *not* evidence of deleted data (the `<dimension>` tag is authoritative
and confirms no data exists past Q, and there is no `<cols>` hidden-column
entry either); it most likely means someone last had the cursor briefly
outside the data table before saving. Noted for completeness only — it is
not a finding.

## Conclusion

**No real patient ID, eye-visit key, or examination date is recoverable
from this workbook by any means** — not just absent from the visible
columns, but absent from every non-visible part of the file that could
plausibly carry one (hidden sheets, hidden rows/columns, formulas,
comments, embedded/linked objects, defined names, extra shared strings,
or document metadata). The file contains exactly what
`MM_RETINA_SAFE_MULTIMODAL_STRATEGY.md` already established from the
visible grid: `SI NO` (a meaningless serial number), `Age`, `Gender`,
`Eye`, `Glaucoma_Severity`, and the RNFL/GCC measurements — nothing more.

This closes the "is there a hidden identifier" question definitively: the
only way a real Patient ID / eye / date mapping between this file and the
HVF DICOM cohort will ever exist is if the **data provider** supplies it
from their own original records — it cannot be recovered from the
delivered artifact itself.
