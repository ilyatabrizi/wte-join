#!/usr/bin/env python3
"""End-to-end checks, through system Chrome.

    python3 e2e.py                                         # against the local server (:8251)
    python3 e2e.py https://ilyatabrizi.github.io/wte-join/
    python3 e2e.py --shots                                 # also refresh docs/shots/

Asserts what a visitor would see or be told — geometry, behaviour, contrast measured on the
rendered pixels — never class names for their own sake.
"""
import io
import json
import pathlib
import sys
from urllib.parse import parse_qs

from PIL import Image
from playwright.sync_api import sync_playwright

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
URL = ARGS[0] if ARGS else "http://localhost:8251/"
SHOTS = "--shots" in sys.argv
ROOT = pathlib.Path(__file__).resolve().parent
LRI, PDI = chr(0x2066), chr(0x2069)
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))


def fresh(browser, w=390, h=844, mobile=True, **kw):
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                              is_mobile=mobile, has_touch=mobile, locale="fa-IR", **kw)
    page = ctx.new_page()
    page.errors = []
    page.infos = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else page.infos.append(m.text))
    return ctx, page


def goto(page, suffix=""):
    page.goto(URL + suffix, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_function("window.__wte && window.__wte.ready === true")
    page.wait_for_timeout(1300)          # arrival animations finish; fill-mode backwards leaves nothing behind


def fill_valid(page, email=True, niche="food"):
    page.fill("#f-first", "سارا")
    page.fill("#f-last", "رضایی")
    page.fill("#f-business", "کافه نور")
    page.click(f"label.chip:has(input[value={niche}])")
    page.fill("#f-city", "تبریز")
    page.fill("#f-phone", "09141234567")
    if email:
        page.fill("#f-email", "sara@example.com")
    page.click(".sheet__title")          # blur the last field


def invalid(page):
    return page.evaluate("[...document.querySelectorAll('.is-invalid')].map(e => e.dataset.name)")


GLASS_ANCESTORS = """() => [...document.querySelectorAll('*')].filter(e => {
    const s = getComputedStyle(e); return (s.backdropFilter && s.backdropFilter !== 'none') || (s.webkitBackdropFilter && s.webkitBackdropFilter !== 'none'); })
  .flatMap(e => { const bad = []; for (let a = e.parentElement; a; a = a.parentElement) { const s = getComputedStyle(a);
      if (s.transform !== 'none' || s.filter !== 'none' || s.perspective !== 'none' || parseFloat(s.opacity) < 1 || s.mixBlendMode !== 'normal')
        bad.push((e.className.baseVal ?? e.className) + ' <- ' + (a.className.baseVal ?? a.className ?? a.tagName)); } return bad; })"""

TEXT_BOXES = """(sels) => {
  const out = [];
  for (const sel of sels) for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || r.bottom < 90 || r.top > innerHeight - 4 || r.top < 90) continue;
    if (!el.textContent.trim()) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    out.push({ sel, text: el.textContent.trim().slice(0, 24), x: r.left, y: r.top, w: r.width, h: r.height,
               color: s.color, size: parseFloat(s.fontSize), weight: parseInt(s.fontWeight, 10) });
  }
  return out;
}"""


def rgba(css):
    nums = [float(v) for v in css[css.index("(") + 1:css.index(")")].replace("/", ",").replace(" ", ",").split(",") if v]
    return (nums + [1.0])[:4] if len(nums) == 3 else nums[:4]


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_audit(page, selectors):
    """Worst-case contrast of each text box against the pixels actually behind it, measured with
    every glyph made transparent — sampling with the text present measures anti-aliasing instead."""
    boxes = page.evaluate(TEXT_BOXES, selectors)
    page.add_style_tag(content="*,*::before,*::after{color:transparent!important;-webkit-text-fill-color:transparent!important;"
                                "text-shadow:none!important;caret-color:transparent!important} ::placeholder{color:transparent!important}"
                                " .edge{display:none!important}")
    page.wait_for_timeout(120)
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    page.evaluate("document.head.lastElementChild.remove()")
    scale = img.width / page.viewport_size["width"]
    fails = []
    for b in boxes:
        x0, y0 = int((b["x"] + 1) * scale), int((b["y"] + 1) * scale)
        x1, y1 = int((b["x"] + b["w"] - 1) * scale), int((b["y"] + b["h"] - 1) * scale)
        if x1 <= x0 or y1 <= y0:
            continue
        px = list(img.crop((x0, y0, x1, y1)).resize((max(1, (x1 - x0) // 3), max(1, (y1 - y0) // 3))).getdata())
        px.sort(key=lum)
        lo, hi = px[int(len(px) * .02)], px[int(len(px) * .98) - 1 if len(px) > 1 else 0]
        r, g, bl, a = rgba(b["color"])
        worst = 99
        for bg in (lo, hi):
            fg = tuple(a * c + (1 - a) * k for c, k in zip((r, g, bl), bg))
            worst = min(worst, ratio(fg, bg))
        large = b["size"] >= 24 or (b["size"] >= 18.66 and b["weight"] >= 700)
        need = 3.0 if large else 4.5
        if worst < need:
            fails.append(f"{b['sel']} «{b['text']}» {worst:.2f}<{need}")
    return len(boxes), fails


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")

        # ── Document ──────────────────────────────────────────────────────────
        print("Document")
        ctx, page = fresh(browser)
        resp = page.goto(URL, wait_until="networkidle")
        check("page answers 200", resp and resp.status == 200, resp and resp.status)
        goto(page)
        check("no console or page errors on load", not page.errors, "; ".join(page.errors))
        check("<html lang=fa dir=rtl>", page.get_attribute("html", "lang") == "fa" and page.get_attribute("html", "dir") == "rtl")
        check("exactly one h1", page.locator("h1").count() == 1)
        check("title names Went To Event", "Went To Event" in page.title(), page.title())
        check("IRANYekanX FaNum loaded and in use",
              page.evaluate("document.fonts.check('17px YekanX') && [...document.fonts].some(f => f.family.includes('YekanX') && f.status === 'loaded')"))
        fam = page.evaluate("getComputedStyle(document.body).fontFamily")
        check("body is set in YekanX first", fam.strip('"').startswith("YekanX"), fam)
        logo = page.evaluate("(() => { const i = document.querySelector('.hero__logo'); const r = i.getBoundingClientRect(); return {ok: i.complete && i.naturalWidth > 0, alt: i.alt, w: r.width, top: r.top}; })()")
        check("hero logo decoded, with alt text", logo["ok"] and logo["alt"] == "Went To Event", logo)
        check("hero logo is big on a phone (≥ 300px of a 390px screen)", logo["w"] >= 300, logo["w"])
        check("hero logo sits in the first screen", logo["top"] < 200, logo["top"])
        og = page.evaluate("document.querySelector('meta[property=\"og:image\"]').content")
        check("og:image is an absolute URL", og.startswith("https://"), og)
        ogimg = Image.open(ROOT / "assets" / "og.jpg")
        check("link-preview card is 1200×630", ogimg.size == (1200, 630), ogimg.size)
        demo = not page.evaluate("window.__wte.live")
        if demo:
            check("preview: robots noindex while nothing is wired", "noindex" in (page.get_attribute("meta[name=robots]", "content") or ""))
            check("preview: says so beside the button", page.is_visible("[data-preview-flag]"))
        body_text = page.evaluate("document.body.innerText")
        check("no middle dot anywhere (it reads as ۰ beside Persian numerals)", "·" not in body_text)
        pal = page.evaluate("""[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.body).color,
                              getComputedStyle(document.querySelector('.mark__dot')).fill]""")
        check("palette: bone ground, ink type, the dot's orange", pal == ["rgb(244, 241, 236)", "rgb(11, 10, 12)", "rgb(254, 66, 34)"], pal)

        print("Form semantics")
        labels = page.evaluate("""['f-first','f-last','f-business','f-city','f-phone','f-email','f-other'].map(id => {
            const l = document.querySelector('label[for=' + id + ']'); return l ? l.textContent.trim() : ''; })""")
        check("every text field has a visible label", all(labels), labels)
        req = page.evaluate("['f-first','f-last','f-business','f-city','f-phone'].every(id => document.getElementById(id).required)")
        check("name, last name, business, city and phone are required", req)
        check("niche is a required radio group", page.evaluate("document.querySelector('input[name=niche]').required"))
        check("email alone is optional", not page.evaluate("document.getElementById('f-email').required"))
        check("the optional one is labelled so", "اختیاری" in page.text_content("label[for=f-email]"))
        check("11 niche options including 'other'", page.locator("input[name=niche]").count() == 11 and page.locator("input[name=niche][value=other]").count() == 1)
        check("phone and email are typed left-to-right", page.get_attribute("#f-phone", "dir") == "ltr" and page.get_attribute("#f-email", "dir") == "ltr")
        check("email keeps Latin figures", "YekanX Latin" in page.evaluate("getComputedStyle(document.getElementById('f-email')).fontFamily"))
        check("inputs are ≥ 16px (no iOS zoom on focus)", page.evaluate("[...document.querySelectorAll('.field input')].every(i => parseFloat(getComputedStyle(i).fontSize) >= 16)"))
        hp = page.evaluate("(() => { const r = document.getElementById('f-website').getBoundingClientRect(); return r.right < 0 || r.left > innerWidth || r.width <= 1; })()")
        check("the honeypot is out of sight and out of the tab order", hp and page.get_attribute("#f-website", "tabindex") == "-1")
        small = page.evaluate("""[...document.querySelectorAll('.chip, .btn, .cap')].filter(e => e.offsetParent)
                                .map(e => e.getBoundingClientRect()).filter(r => r.height < 44 || r.width < 44).length""")
        check("tap targets are at least 44×44", small == 0, small)

        print("Glass")
        bad = page.evaluate(GLASS_ANCESTORS)
        check("no glass sits under a backdrop root (transform, filter, opacity, blend)", not bad, "; ".join(bad[:4]))
        bf = page.evaluate("['.sheet', '.cap--brand', '.cap--progress', '.kicker'].map(s => getComputedStyle(document.querySelector(s)).backdropFilter)")
        check("sheet, capsules and kicker really blur what is behind them", all(v and v != "none" and "blur" in v for v in bf), bf)
        check("floating bar is positioned without a transform",
              page.evaluate("getComputedStyle(document.querySelector('.bar')).transform") == "none")
        n, fails = contrast_audit(page, [".hero__title", ".hero__lede", ".kicker"])
        check(f"contrast, hero ({n} boxes, measured on pixels)", not fails and n >= 3, "; ".join(fails))
        page.evaluate("document.getElementById('join').scrollIntoView({block: 'start'})"); page.wait_for_timeout(500)
        n, fails = contrast_audit(page, [".sheet__title", ".sheet__note", ".group__title", ".field label", ".niche__label", ".chip span", ".cap__name", ".cap__text"])
        check(f"contrast, top of the sheet over the orb ({n} boxes)", not fails and n >= 6, "; ".join(fails))
        page.evaluate("document.querySelector('.submit').scrollIntoView({block: 'center'})"); page.wait_for_timeout(500)
        n, fails = contrast_audit(page, [".field label", ".group__title", ".fine", ".preview-flag", ".btn__label"])
        check(f"contrast, foot of the sheet ({n} boxes)", not fails and n >= 3, "; ".join(fails))
        ctx.close()

        print("Layout")
        for w, h, mob in [(320, 640, True), (360, 740, True), (375, 667, True), (390, 844, True), (414, 896, True),
                          (768, 1024, True), (1024, 768, False), (1280, 800, False), (1440, 900, False), (1920, 1080, False)]:
            ctx, page = fresh(browser, w, h, mob)
            goto(page)
            over = page.evaluate("document.scrollingElement.scrollWidth - innerWidth")
            check(f"{w}px: no sideways scroll", over <= 0, over)
            if w >= 1080:
                geo = page.evaluate("""(() => { const h = document.querySelector('.hero').getBoundingClientRect(), s = document.getElementById('join').getBoundingClientRect(),
                    l = document.querySelector('.hero__logo').getBoundingClientRect(); return {heroLeft: h.left, sheetRight: s.right, sheetTop: s.top, logoW: l.width}; })()""")
                check(f"{w}px: brand on the right, form on the left, both in the first screen",
                      geo["heroLeft"] >= geo["sheetRight"] - 1 and geo["sheetTop"] < h * .4, geo)
                check(f"{w}px: logo at least 400px wide", geo["logoW"] >= 400, geo["logoW"])
                page.mouse.wheel(0, 900); page.wait_for_timeout(600)
                top = page.evaluate("document.querySelector('.hero').getBoundingClientRect().top")
                check(f"{w}px: the brand column holds still while the form scrolls", abs(top) < 2, top)
            ctx.close()

        # ── Validation ────────────────────────────────────────────────────────
        print("Validation")
        ctx, page = fresh(browser)
        goto(page)
        page.click("[data-submit]")
        page.wait_for_timeout(500)
        check("an empty send flags exactly the six required answers",
              sorted(invalid(page)) == sorted(["first_name", "last_name", "business_name", "niche", "city", "phone"]), invalid(page))
        check("…and moves focus to the first of them", page.evaluate("document.activeElement.id") == "f-first")
        check("…and says how many, aloud", "۶" in page.text_content("[data-announce]"), page.text_content("[data-announce]"))
        check("errors are tied to their fields (aria-invalid + describedby)",
              page.get_attribute("#f-first", "aria-invalid") == "true" and page.get_attribute("#f-first", "aria-describedby") == "first_name-msg")
        check("the message says what to do", "بنویسید" in page.text_content("#first_name-msg"))
        check("nothing was sent", page.is_hidden("[data-view=done]"))
        page.type("#f-first", "سارا")
        check("an error clears as soon as it is fixed", "first_name" not in invalid(page))
        page.fill("#f-last", "Rezaei2"); page.click(".sheet__title")
        check("digits in a name are refused", "last_name" in invalid(page))
        page.fill("#f-last", "رضایی")
        check("…and accepted once gone", "last_name" not in invalid(page))
        page.fill("#f-business", "ک"); page.click(".sheet__title")
        check("a one-letter business name is refused", "business_name" in invalid(page))
        page.fill("#f-business", "کافه نور")
        page.fill("#f-phone", "12345"); page.click(".sheet__title")
        check("a short number is refused", "phone" in invalid(page))
        msg = page.text_content("#phone-msg")
        check("the phone example is bidi-isolated (reads 0912 345 6789, not reversed)", LRI in msg and PDI in msg, repr(msg))
        page.fill("#f-phone", "")
        page.type("#f-phone", "۰۹۱۲۳۴۵۶۷۸۹")
        check("Persian digits become Latin, grouped as typed", page.input_value("#f-phone") == "0912 345 6789", page.input_value("#f-phone"))
        check("…and the number is accepted", "phone" not in invalid(page))
        for raw, ok in [("+98 912 345 6789", True), ("00989123456789", True), ("9123456789", True), ("021 8877 6655", True),
                        ("+971 50 123 4567", True), ("0912 345 678", False), ("+12", False)]:
            page.fill("#f-phone", raw); page.click(".sheet__title")
            check(f"phone {raw!r} {'accepted' if ok else 'refused'}", ("phone" not in invalid(page)) == ok, invalid(page))
        page.fill("#f-phone", "09141234567"); page.click(".sheet__title")
        check("a valid number is shown grouped on leaving the field", page.input_value("#f-phone") == "0914 123 4567", page.input_value("#f-phone"))
        page.fill("#f-email", "sara@"); page.click(".sheet__title")
        check("a broken email is refused", "email" in invalid(page))
        page.fill("#f-email", ""); page.click(".sheet__title")
        check("an empty email is fine", "email" not in invalid(page))
        page.fill("#f-email", "sara@gmial.com"); page.click(".sheet__title")
        hint = page.evaluate("document.getElementById('email-hint').hidden ? '' : document.getElementById('email-hint').textContent")
        check("a mistyped domain is questioned", "sara@gmail.com" in hint, hint)
        page.click("#email-hint button")
        check("…and fixed in one tap", page.input_value("#f-email") == "sara@gmail.com")
        page.fill("#f-city", "12"); page.click(".sheet__title")
        check("a number is not a city", "city" in invalid(page))
        page.fill("#f-city", "")

        print("Niche")
        check("'other' has no field until chosen", page.is_hidden("#f-other"))
        page.click("label.chip:has(input[value=other])"); page.wait_for_timeout(450)
        check("choosing 'other' opens a field for it", page.is_visible("#f-other"))
        check("…focuses it", page.evaluate("document.activeElement.id") == "f-other")
        check("…and makes it required", page.evaluate("document.getElementById('f-other').required"))
        page.click("label.chip:has(input[value=music])"); page.wait_for_timeout(450)
        check("choosing another niche puts it away again", page.is_hidden("#f-other") and not page.evaluate("document.getElementById('f-other').required"))
        on = page.evaluate("[...document.querySelectorAll('.chip.is-on')].map(c => c.querySelector('input').value)")
        check("exactly one tile reads as chosen", on == ["music"], on)
        chosen_bg = page.evaluate("getComputedStyle(document.querySelector('.chip.is-on')).backgroundImage")
        check("the chosen tile is Ink", "rgb(11, 10, 12)" in chosen_bg, chosen_bg)

        print("City")
        page.click("#f-city"); page.wait_for_timeout(150)
        pop = page.evaluate("[...document.querySelectorAll('#city-suggest button')].map(b => b.dataset.city)")
        check("an empty city field offers the big six", pop == ["تهران", "مشهد", "اصفهان", "شیراز", "تبریز", "کرج"], pop)
        page.keyboard.type("مش"); page.wait_for_timeout(150)
        sug = page.evaluate("[...document.querySelectorAll('#city-suggest button')].map(b => b.dataset.city)")
        check("typing narrows the list", sug and sug[0] == "مشهد", sug)
        page.fill("#f-city", ""); page.keyboard.type("امل"); page.wait_for_timeout(150)
        sug = page.evaluate("[...document.querySelectorAll('#city-suggest button')].map(b => b.dataset.city)")
        check("matching ignores آ/ا (typing امل finds آمل)", "آمل" in sug, sug)
        page.fill("#f-city", ""); page.keyboard.type("تبر"); page.wait_for_timeout(150)
        page.keyboard.press("Enter")
        check("Enter takes the first suggestion", page.input_value("#f-city") == "تبریز", page.input_value("#f-city"))
        page.fill("#f-city", ""); page.keyboard.type("شی"); page.wait_for_timeout(150)
        page.click("#city-suggest button[data-city='شیراز']")
        check("a tapped suggestion fills the field", page.input_value("#f-city") == "شیراز")
        check("…and hides the list", page.is_hidden("#city-suggest"))
        check("…and moves on to the next empty field", page.evaluate("document.activeElement.id") in ("f-phone", "f-city"))
        page.fill("#f-city", "دبی"); page.click(".sheet__title")
        check("a city outside the list is still accepted", "city" not in invalid(page))
        ctx.close()

        print("Keyboard")
        ctx, page = fresh(browser, 1280, 800, False)
        goto(page)
        page.focus("#f-first"); page.keyboard.type("سارا"); page.keyboard.press("Enter")
        check("Enter in first name moves to last name", page.evaluate("document.activeElement.id") == "f-last")
        page.keyboard.type("رضایی"); page.keyboard.press("Enter")
        check("…then to business name", page.evaluate("document.activeElement.id") == "f-business")
        page.keyboard.type("کافه نور"); page.keyboard.press("Enter")
        check("…then to the niche tiles", page.evaluate("document.activeElement.name") == "niche")
        page.keyboard.press("ArrowLeft")
        check("arrow keys choose a tile", page.evaluate("!!document.querySelector('input[name=niche]:checked')"))
        ring = page.evaluate("getComputedStyle(document.querySelector('.chip:has(input:focus-visible)')).outlineColor")
        check("keyboard focus shows the orange ring", ring == "rgb(254, 66, 34)", ring)
        page.focus("#f-phone"); page.keyboard.type("09123456789"); page.keyboard.press("Enter")
        check("Enter in phone moves to email", page.evaluate("document.activeElement.id") == "f-email")
        ctx.close()

        print("Progress")
        ctx, page = fresh(browser)
        goto(page)
        check("progress starts at 0 of 6", page.text_content("[data-progress-text]") == "0 از 6")
        page.fill("#f-first", "سارا"); page.fill("#f-last", "رضایی")
        check("…counts only what is valid", page.text_content("[data-progress-text]") == "2 از 6", page.text_content("[data-progress-text]"))
        page.click("[data-progress]"); page.wait_for_timeout(700)
        check("the ring jumps to the next thing to answer", page.evaluate("document.activeElement.id") == "f-business")
        fill_valid(page, email=False)
        check("…and says ready when all six are in", page.text_content("[data-progress-text]") == "آمادهٔ ثبت" and page.get_attribute("[data-progress]", "data-complete") is not None)
        page.click("[data-progress]"); page.wait_for_timeout(700)
        check("…then takes you to the button", page.evaluate("document.activeElement.hasAttribute('data-submit')"))

        print("Draft")
        page.reload(wait_until="networkidle"); page.wait_for_function("window.__wte && window.__wte.ready")
        kept = page.evaluate("['f-first','f-business','f-city','f-phone'].map(id => document.getElementById(id).value)")
        check("a reload keeps what was typed", kept == ["سارا", "کافه نور", "تبریز", "0914 123 4567"], kept)
        check("…including the chosen niche", page.evaluate("document.querySelector('input[name=niche]:checked')?.value") == "food")

        print("Send (preview)")
        page.click("[data-submit]")
        busy = page.get_attribute("[data-submit]", "aria-busy")
        check("the button shows it is working", busy == "true", busy)
        page.wait_for_selector("[data-view=done]:not([hidden])", timeout=6000); page.wait_for_timeout(700)
        check("the confirmation replaces the form", page.is_hidden("[data-view=form]"))
        check("focus lands on the confirmation", page.evaluate("document.activeElement.id") == "done-title")
        rows = page.evaluate("[...document.querySelectorAll('.summary > div')].map(d => [d.querySelector('dt').textContent, d.querySelector('dd').textContent])")
        check("it reads the answers back (no email row when none was given)", len(rows) == 5 and rows[1] == ["کسب‌وکار", "کافه نور"], rows)
        if demo:
            check("preview: the confirmation does not claim anything was sent", page.is_visible("[data-done-demo]") and "ثبت شد" not in page.text_content("#done-title"))
            check("preview: nothing left the page", any("nothing was sent" in m for m in page.infos), page.infos)
        check("the draft is gone once sent", page.evaluate("localStorage.getItem('wte-join:draft:v1')") is None)
        page.click("[data-again]"); page.wait_for_timeout(500)
        again = page.evaluate("['f-first','f-last','f-phone','f-business','f-city'].map(id => document.getElementById(id).value)")
        check("'another business' keeps the person, clears the business", again == ["سارا", "رضایی", "0914 123 4567", "", ""], again)
        check("…and starts at the business name", page.evaluate("document.activeElement.id") == "f-business")
        check("…with no niche chosen", not page.evaluate("!!document.querySelector('input[name=niche]:checked')"))
        ctx.close()

        ctx, page = fresh(browser)
        goto(page, "?demo=fail")
        fill_valid(page)
        page.click("[data-submit]"); page.wait_for_timeout(1400)
        check("a failed send says so, in words", page.is_visible("[data-alert]") and "اینترنت" in page.text_content("[data-alert]"))
        check("…and keeps every answer", page.input_value("#f-business") == "کافه نور" and page.is_visible("[data-view=form]"))
        ctx.close()

        ctx, page = fresh(browser)
        goto(page)
        fill_valid(page)
        page.evaluate("document.getElementById('f-website').value = 'http://spam.example'")
        page.click("[data-submit]"); page.wait_for_timeout(500)
        check("a filled honeypot is thanked and ignored", page.is_visible("[data-view=done]") and not any("nothing was sent" in m for m in page.infos))
        ctx.close()

        # ── Delivery modes ────────────────────────────────────────────────────
        print("Delivery: endpoint")

        def with_config(page, cfg):
            page.route("**/js/config.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body="window.WTE_CONFIG = " + json.dumps(cfg) + ";"))

        ctx, page = fresh(browser)
        with_config(page, {"mode": "endpoint", "endpoint": "https://receiver.test/join", "timeoutMs": 8000})
        seen = {}

        def receiver(route):
            seen["method"], seen["body"], seen["type"] = route.request.method, route.request.post_data, route.request.headers.get("content-type", "")
            route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"},
                          body='{"ok": true, "reference": "WTE-7F3K"}')
        page.route("https://receiver.test/join", receiver)
        goto(page)
        check("endpoint mode: no preview flag", page.is_hidden("[data-preview-flag]"))
        fill_valid(page)
        page.click("[data-submit]")
        page.wait_for_selector("[data-view=done]:not([hidden])", timeout=6000)
        form = {k: v[0] for k, v in parse_qs(seen.get("body") or "", keep_blank_values=True).items()}
        check("POSTs a simple urlencoded body (no CORS preflight)", seen.get("method") == "POST" and seen.get("type", "").startswith("application/x-www-form-urlencoded"), seen.get("type"))
        want = {"first_name": "سارا", "last_name": "رضایی", "business_name": "کافه نور", "niche": "food", "niche_label": "کافه و رستوران",
                "city": "تبریز", "phone": "09141234567", "email": "sara@example.com"}
        check("sends every answer, phone normalised", all(form.get(k) == v for k, v in want.items()), {k: form.get(k) for k in want})
        check("sends when and from where", form.get("submitted_at", "").endswith("Z") and form.get("page", "").startswith("http"))
        check("confirmation claims the send once it really happened", page.text_content("#done-title") == "درخواستتان ثبت شد")
        check("the receiver's reference is shown", "WTE-7F3K" in page.text_content(".summary"))
        check("no preview caveat on a real send", page.is_hidden("[data-done-demo]"))
        ctx.close()

        for status, word in [(500, "مشکلی"), (429, "کمی بعد")]:
            ctx, page = fresh(browser)
            with_config(page, {"mode": "endpoint", "endpoint": "https://receiver.test/join", "timeoutMs": 8000})
            def refuse(code):
                return lambda route: route.fulfill(status=code, content_type="application/json",
                                                   headers={"Access-Control-Allow-Origin": "*"}, body='{"ok": false}')
            page.route("https://receiver.test/join", refuse(status))
            goto(page); fill_valid(page); page.click("[data-submit]"); page.wait_for_timeout(1200)
            check(f"a {status} is reported, not swallowed", page.is_visible("[data-alert]") and word in page.text_content("[data-alert]"), page.text_content("[data-alert]"))
            ctx.close()

        ctx, page = fresh(browser)
        with_config(page, {"mode": "endpoint", "endpoint": "https://receiver.test/join", "timeoutMs": 8000})
        page.route("https://receiver.test/join", lambda r: r.abort())
        goto(page); fill_valid(page); page.click("[data-submit]"); page.wait_for_timeout(1200)
        check("an unreachable receiver reads as a connection problem", page.is_visible("[data-alert]") and "اینترنت" in page.text_content("[data-alert]"))
        ctx.close()

        print("Delivery: Google Form")
        ctx, page = fresh(browser)
        fields = {"first_name": "entry.101", "last_name": "entry.102", "business_name": "entry.103", "niche_label": "entry.104",
                  "niche_other": "entry.105", "city": "entry.106", "phone": "entry.107", "email": "entry.108"}
        with_config(page, {"mode": "google-form", "googleForm": {"action": "https://forms.test/d/e/X/formResponse", "fields": fields}})
        got = {}

        def gform(route):
            got["body"] = route.request.post_data
            route.fulfill(status=200, body="")
        page.route("https://forms.test/d/e/X/formResponse", gform)
        goto(page); fill_valid(page); page.click("[data-submit]")
        page.wait_for_selector("[data-view=done]:not([hidden])", timeout=6000)
        gf = {k: v[0] for k, v in parse_qs(got.get("body") or "", keep_blank_values=True).items()}
        check("maps each answer onto its entry id", gf.get("entry.101") == "سارا" and gf.get("entry.104") == "کافه و رستوران" and gf.get("entry.107") == "09141234567", gf)
        ctx.close()

        print("Motion")
        ctx, page = fresh(browser, reduced_motion="reduce")
        goto(page)
        anim = page.evaluate("['.sheet', '.hero__logo', '.orb i'].map(s => getComputedStyle(document.querySelector(s)).animationName)")
        check("reduced motion: nothing arrives or breathes", all(a == "none" for a in anim), anim)
        ctx.close()

        if SHOTS:
            out = ROOT / "docs" / "shots"
            out.mkdir(parents=True, exist_ok=True)
            ctx, page = fresh(browser, 390, 844, True)
            goto(page)
            page.screenshot(path=str(out / "phone-1-hero.png"))
            page.evaluate("document.getElementById('join').scrollIntoView({block: 'start'})"); page.wait_for_timeout(600)
            page.screenshot(path=str(out / "phone-2-form.png"))
            fill_valid(page)
            page.evaluate("document.querySelector('[data-name=niche]').scrollIntoView({block: 'start'})"); page.wait_for_timeout(600)
            page.screenshot(path=str(out / "phone-3-filled.png"))
            page.click("[data-submit]"); page.wait_for_selector("[data-view=done]:not([hidden])"); page.wait_for_timeout(1200)
            page.screenshot(path=str(out / "phone-4-done.png"))
            ctx.close()
            ctx, page = fresh(browser, 1440, 900, False)
            goto(page)
            page.screenshot(path=str(out / "desktop.png"))
            ctx.close()
            print(f"  shots → {out}")

        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
