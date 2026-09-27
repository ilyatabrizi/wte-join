#!/usr/bin/env python3
"""The hero logo: scripts/src/logo-original.webp (as supplied) → assets/brand/logo-{420,600,900,1338}.webp.

The canvas is built around the LETTER, not the lockup: the e's own centre is the canvas centre,
so a plainly centred <img> puts the e dead centre and lets the dot hang off to the right.

The supplied file is already cut out, but lossy: its solid areas sit at alpha 252–253 (so the ground
showed through by about 1%) and a faint haze of alpha 1–7 surrounds the letter. So:
  1. alpha is re-levelled — ≤10 becomes 0, ≥250 becomes 255, the 1–2px edge ramp in between is kept;
  2. every edge pixel takes the colour of its nearest solid pixel, so no matte fringe shows;
  3. the canvas is padded symmetrically about the e (found as the ink left of the empty column band
     that separates it from the dot) and exported at four widths for srcset.
"""
import pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "brand"
PAD = 6

a = np.asarray(Image.open(HERE / "src" / "logo-original.webp").convert("RGBA")).astype(np.float64)
alpha = np.round(np.clip((a[..., 3] - 10.0) / 240.0, 0, 1) * 255).astype(np.uint8)
solid = alpha == 255
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
rgb = a[..., :3].copy()
edge = (alpha > 0) & (alpha < 255)
rgb[edge] = a[iy[edge], ix[edge], :3]
out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])

ink = alpha > 0
cols = np.nonzero(ink.any(0))[0]
band = [x for x in range(cols.min(), cols.max()) if not ink[:, x].any()]      # between the e and the dot
e_cols = np.nonzero(ink[:, :band[0]].any(0))[0]
e_left, e_right = int(e_cols.min()), int(e_cols.max()) + 1                    # [left, right)
centre = (e_left + e_right) / 2
half = int(np.ceil(max(centre - e_left, cols.max() + 1 - centre))) + PAD
x0, x1 = int(round(centre - half)), int(round(centre + half))
rows = np.nonzero(ink.any(1))[0]
y0, y1 = int(rows.min()) - PAD, int(rows.max()) + 1 + PAD

H, W = out.shape[:2]
canvas = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
sx0, sx1, sy0, sy1 = max(0, x0), min(W, x1), max(0, y0), min(H, y1)
canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = out[sy0:sy1, sx0:sx1]
crop = Image.fromarray(canvas)
print(f"e spans {e_left}–{e_right} (centre {centre}); canvas {crop.size}, e is {(e_right - e_left) / crop.width:.4f} of its width")

for w in (420, 600, 900, crop.width):
    img = crop if w == crop.width else crop.resize((w, round(crop.height * w / crop.width)), Image.LANCZOS)
    img.save(OUT / f"logo-{w}.webp", "WEBP", quality=86, method=6, alpha_quality=100)
    print(OUT / f"logo-{w}.webp", img.size)
