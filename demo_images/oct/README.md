# Demo OCT images

Where appropriately licensed/public OCT B-scan images for the live demo's
"Select Demo" option should go.

The one currently wired into the website is a real, unmodified B-scan
extracted from the GAMMA dataset's actual OCT volume for training sample
0001 (slice 128 of 256 — see `../../dataset/extract_oct_slices.py` and
`../../dataset/README.md` for provenance/license, CC BY-NC-ND). It is
served from `../../website/public/oct-volume/0001/128.jpg` (already used
by the site's interactive OCT viewer on `/model`) rather than duplicated
into this folder.

Note: the live demo backend accepts a single OCT image and repeats it
across the model's expected 8-slice input — see
`../../backend/inference.py`'s module docstring for why, and
`../../backend/README.md` for the full limitation. This is disclosed to
the user in the demo UI, not hidden.

Do not add real patient images from any source you don't have explicit
rights to redistribute.
