# Went To Event: business sign-up

A one-page Persian (RTL) form for businesses that want to join Went To Event. Hosted on GitHub Pages.

- **Live:** https://ilyatabrizi.github.io/wte-join/
- **Local:** `python3 serve.py` → http://localhost:8251
- **Checks:** `python3 e2e.py [url]` runs 146 checks through system Chrome. Add `--shots` to refresh `docs/shots/`.

## What it asks

| Field | Required | Notes |
|---|---|---|
| نام / نام خانوادگی | yes | letters only, at least 2 |
| نام کسب‌وکار | yes | |
| حوزهٔ فعالیت | yes | one native picker: 10 niches taken from the app's own event categories, plus «سایر», which opens a row to type in |
| شهر | yes | free text; suggests Iranian cities (آ/ا, ی/ي and ک/ك are treated as the same letter) |
| شمارهٔ تماس | yes | Iranian mobile or landline, or any `+` international number. Persian digits are accepted and stored as Latin |
| ایمیل | **no** | validated only if filled; offers a fix for a mistyped domain (gmial.com → gmail.com) |

What people type is kept in `localStorage` as a draft and cleared once the form is sent. A hidden honeypot field catches bots.

## Where submissions go: `js/config.js`

The page ships in **`mode: 'demo'`**. In this mode nothing is sent, and the page says so beside the button and on the confirmation screen. It also stays `noindex`.

To make it live, choose one:

- **`endpoint`**: posts `application/x-www-form-urlencoded` to your own receiver, which should reply `{ "ok": true, "reference": "…" }` with `Access-Control-Allow-Origin: https://ilyatabrizi.github.io`. This is the most reliable option for visitors in Iran if the receiver runs on an Iranian host.
- **`google-form`**: posts to a Google Form's `formResponse` URL. Map each key to its `entry.NNNN` id.

Keys sent: `first_name last_name business_name niche niche_label niche_other city phone email submitted_at page elapsed_ms`.

Once it is live, remove `<meta name="robots" content="noindex, nofollow">` from `index.html` and bump the `?v=` on the CSS/JS links.

## Design (v2, 2026-09-27: dark, iOS-minimal)

- The ground is black: Ink `#0B0A0C`. Text is Bone `#F4F1EC` and the only button is Bone. Orange
  `#FE4222` is used for state only: the caret, the progress ring, errors, and the dot. It was sampled
  from the centre of the dot in the supplied logo; the brand sheet's Ember is `#FF5B3D`.
- The logo is small. Its canvas is built around the **letter**, not the lockup
  (`scripts/build_logo.py`), so a plainly centred image puts the e dead centre and lets the dot hang
  to the right. `e2e.py` measures this on pixels at 10 widths.
- The form uses iOS inset-grouped rows: label on the leading edge, value next to it, hairlines
  inset from the leading edge. Sections are «دربارهٔ شما», «کسب‌وکار» and «راه ارتباط».
- Niche is **one native picker**. The select lies invisibly over the whole row, so iOS opens its own
  wheel and a Mac its own menu; the row shows the chosen value and an up-down chevron. Choosing
  «سایر» opens one more row for it.
- Glass is used only on the chrome: two floating capsules (brand, and a progress ring counting the six
  required answers) and a scroll edge that softens the page as it passes beneath them. No glass sits
  under a transformed, filtered or translucent ancestor; `e2e.py` checks this.
- One centred column (≤ 560px) at every width.
- Type is IRANYekanX FaNum (variable, round dots, `"dots" 4`), which turns Latin digits into ۰–۹ by
  itself. Only the email field uses a Latin subset.

## Files

- `index.html`, `css/main.css`, `js/config.js`, `js/main.js`: the page. No build step, no dependencies.
- `assets/brand/logo-*.webp`: built from the supplied logo by `scripts/build_logo.py`. It re-levels the lossy alpha, defringes the edge, and centres the canvas on the e.
- `assets/og.jpg`: the link-preview card, built by `scripts/build_og.py` from `scripts/og.html`.
- `assets/fonts/`: IRANYekanX with its licence file. The font is proprietary (fontiran.com), so the licence must cover web use.
- Favicons come from the brand's own `e.` icon set.
