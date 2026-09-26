# Went To Event: business sign-up

A one-page Persian (RTL) form for businesses that want to join Went To Event. Hosted on GitHub Pages.

- **Live:** https://ilyatabrizi.github.io/wte-join/
- **Local:** `python3 serve.py` → http://localhost:8251
- **Checks:** `python3 e2e.py [url]` runs 132 checks through system Chrome. Add `--shots` to refresh `docs/shots/`.

## What it asks

| Field | Required | Notes |
|---|---|---|
| نام / نام خانوادگی | yes | letters only, at least 2 |
| نام کسب‌وکار | yes | |
| حوزهٔ فعالیت | yes | 10 tiles taken from the app's own event categories, plus «سایر», which opens a text field |
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

## Design

- Bone `#F4F1EC`, Ink `#0B0A0C`, and orange `#FE4222`. The orange was sampled from the centre of the dot in the supplied logo. Went To Event's brand sheet lists Ember as `#FF5B3D`, which is slightly lighter.
- Type is IRANYekanX FaNum (variable, round dots, `"dots" 4`), which turns Latin digits into ۰–۹ by itself. Only the email field uses a Latin subset (`iranyekanx-latin-vf.woff2`).
- iOS glass: floating capsules and one glass sheet. A scroll edge softens content as it passes under the capsules. The logo's dot, enlarged, sits behind the sheet's corner so the glass has something to frost. Glass elements never sit under a transformed, filtered or translucent ancestor; `e2e.py` checks this.
- Wide screens: the brand stays fixed on the right and the form scrolls on the left.

## Files

- `index.html`, `css/main.css`, `js/config.js`, `js/main.js`: the page. No build step, no dependencies.
- `assets/brand/logo-*.webp`: built from the supplied logo by `scripts/build_logo.py` (re-levels the lossy alpha and defringes the edge).
- `assets/og.jpg`: the link-preview card, built by `scripts/build_og.py` from `scripts/og.html`.
- `assets/fonts/`: IRANYekanX with its licence file. The font is proprietary (fontiran.com), so the licence must cover web use.
- Favicons come from the brand's own `e.` icon set.
