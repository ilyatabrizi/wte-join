#!/usr/bin/env python3
"""Link-preview card (Telegram, WhatsApp, iMessage): scripts/og.html → assets/og.jpg, 1200×630.
Rendered at 2× and resampled, so the Persian type is set by the browser, never drawn by a model."""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "og.jpg"
TMP = HERE / "og@2x.png"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
    pg.goto((HERE / "og.html").as_uri())
    pg.evaluate("document.fonts.ready")
    pg.wait_for_function("[...document.images].every(i => i.complete && i.naturalWidth > 0)")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(TMP))
    b.close()

Image.open(TMP).convert("RGB").resize((1200, 630), Image.LANCZOS).save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
TMP.unlink()
print(OUT, OUT.stat().st_size, "bytes")
