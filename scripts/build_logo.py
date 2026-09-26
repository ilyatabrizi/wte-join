#!/usr/bin/env python3
"""The hero logo: scripts/src/logo-original.webp (as supplied) → assets/brand/logo-{520,760,1117}.webp.

The supplied file is already cut out, but lossy: its solid areas sit at alpha 252–253 (so the ground
showed through by about 1%) and a faint haze of alpha 1–7 surrounds the letter. So:
  1. alpha is re-levelled — ≤10 becomes 0, ≥250 becomes 255, the 1–2px edge ramp in between is kept;
  2. every edge pixel takes the colour of its nearest solid pixel, so no matte fringe shows on Bone;
  3. the canvas is cropped to the mark plus 6px, and exported at three widths for srcset.
"""
import pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "brand"

a = np.asarray(Image.open(HERE / "src" / "logo-original.webp").convert("RGBA")).astype(np.float64)
alpha = np.round(np.clip((a[..., 3] - 10.0) / 240.0, 0, 1) * 255).astype(np.uint8)
solid = alpha == 255
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
rgb = a[..., :3].copy()
edge = (alpha > 0) & (alpha < 255)
rgb[edge] = a[iy[edge], ix[edge], :3]
out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])

ys, xs = np.nonzero(alpha)
pad = 6
crop = Image.fromarray(out[max(0, ys.min() - pad):ys.max() + 1 + pad, max(0, xs.min() - pad):xs.max() + 1 + pad])
for w in (520, 760, crop.width):
    img = crop if w == crop.width else crop.resize((w, round(crop.height * w / crop.width)), Image.LANCZOS)
    img.save(OUT / f"logo-{w}.webp", "WEBP", quality=86, method=6, alpha_quality=100)
    print(OUT / f"logo-{w}.webp", img.size)
