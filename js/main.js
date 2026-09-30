/* Went To Event — business sign-up.
 * One form, seven typed answers, six of them required. Validation is quiet while someone types and
 * speaks up when they leave a field or press the button; an error clears the moment it is fixed.
 * Delivery lives in send() and is chosen in js/config.js — nothing else knows where data goes.
 */
(() => {
  'use strict';

  const C = Object.assign({ mode: 'demo', endpoint: '', googleForm: { action: '', fields: {} }, timeoutMs: 15000 }, window.WTE_CONFIG || {});
  const live = (C.mode === 'endpoint' && !!C.endpoint) || (C.mode === 'google-form' && !!(C.googleForm && C.googleForm.action));
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const t0 = Date.now();

  const form = $('#form');
  const sheet = $('#join');
  const viewForm = $('[data-view="form"]');
  const viewDone = $('[data-view="done"]');
  const submitBtn = $('[data-submit]');
  const submitLabel = $('[data-submit-label]');
  const alertBox = $('[data-alert]');
  const announcer = $('[data-announce]');
  const progressBtn = $('[data-progress]');
  const progressText = $('[data-progress-text]');
  const ringFill = $('.ring__fill');
  const suggestBox = $('#city-suggest');
  const emailHint = $('#email-hint');

  const inputs = {
    first_name: $('#f-first'), last_name: $('#f-last'), business_name: $('#f-business'),
    niche: $('#f-niche'), city: $('#f-city'), phone: $('#f-phone'), email: $('#f-email'),
  };
  const REQUIRED = ['first_name', 'last_name', 'business_name', 'niche', 'city', 'phone'];
  const ORDER = ['first_name', 'last_name', 'business_name', 'niche', 'city', 'phone', 'email'];
  const RING = 2 * Math.PI * 9.5;
  const DRAFT = 'wte-join:draft:v2';               // v1 stored the niche as a picker key

  // Suggestions only — any city can be typed. Ordered roughly by size, so ties favour the likelier one.
  const CITIES = ('تهران،مشهد،اصفهان،کرج،شیراز،تبریز،قم،اهواز،کرمانشاه،ارومیه،رشت،زاهدان،همدان،کرمان،یزد،اردبیل،' +
    'بندرعباس،اراک،اسلامشهر،زنجان،سنندج،قزوین،خرم‌آباد،گرگان،ساری،شهریار،قدس،کاشان،ملارد،دزفول،نیشابور،بابل،' +
    'خمینی‌شهر،سبزوار،آمل،پاکدشت،نجف‌آباد،بروجرد،آبادان،قرچک،بجنورد،ورامین،بوشهر،ساوه،قائم‌شهر،سیرجان،بوکان،' +
    'ملایر،خوی،مراغه،شاهرود،بیرجند،رفسنجان،مرودشت،ایلام،شهرکرد،سمنان،یاسوج،مهاباد،تربت حیدریه،کاشمر،جهرم،مرند،' +
    'میاندوآب،بهبهان،اندیمشک،شوشتر،ماهشهر،ایذه،مسجدسلیمان،خرمشهر،سقز،مریوان،بانه،بندر انزلی،لاهیجان،تنکابن،' +
    'رامسر،چالوس،نوشهر،گنبد کاووس،دامغان،فسا،لار،کازرون،آباده،اسلام‌آباد غرب،چابهار،کیش،قشم،بم،جیرفت،زابل،' +
    'ایرانشهر،تربت جام،قوچان،گناباد،اهر،سراب،میانه،ماکو،سلماس،نقده،پیرانشهر،سردشت،الیگودرز،دورود،کوهدشت،نهاوند،' +
    'تویسرکان،اسدآباد،ابهر،تاکستان،محلات،خمین،دلیجان،شاهین‌شهر،فولادشهر،مبارکه،گلپایگان،نطنز،اردکان،میبد،بافق،ابرکوه').split('،');
  const POPULAR = ['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج'];

  const EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com', 'live.com', 'ymail.com', 'proton.me', 'protonmail.com', 'chmail.ir', 'mail.ir'];

  // ── Text helpers ──────────────────────────────────────────────────────────
  const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
  const AR_DIGITS = '٠١٢٣٤٥٦٧٨٩';
  const toLatin = (s) => s.replace(/[۰-۹٠-٩]/g, (d) => String(FA_DIGITS.includes(d) ? FA_DIGITS.indexOf(d) : AR_DIGITS.indexOf(d)));
  const toFa = (s) => String(s).replace(/\d/g, (d) => FA_DIGITS[d]);
  const tidy = (s) => s.replace(/ي/g, 'ی').replace(/ى/g, 'ی').replace(/ك/g, 'ک').replace(/\s+/g, ' ').trim();
  const ltr = (s) => `\u2066${s}\u2069`;          // isolate a number or address inside Persian copy
  const fold = (s) => tidy(toLatin(s)).toLowerCase()
    .replace(/[\u064b-\u065f\u0670]/g, '').replace(/[آأإ]/g, 'ا').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ی')
    .replace(/[\u200c\s\-]/g, '');

  // ── Phone ─────────────────────────────────────────────────────────────────
  // Iranian mobile or landline (11 digits from a 0), or any international number from a +.
  function parsePhone(raw) {
    let s = toLatin(raw).replace(/[\s\-().\u200c\u200e\u200f]/g, '');
    if (s.startsWith('00')) s = '+' + s.slice(2);
    if (s.startsWith('+98')) s = '0' + s.slice(3);
    else if (/^98\d{10}$/.test(s)) s = '0' + s.slice(2);
    if (/^9\d{9}$/.test(s)) s = '0' + s;
    if (/^0[1-9]\d{9}$/.test(s)) return { ok: true, value: s };
    if (/^\+[1-9]\d{7,14}$/.test(s)) return { ok: true, value: s };
    return { ok: false, value: s };
  }
  function formatIR(d) {
    if (d.startsWith('09')) return [d.slice(0, 4), d.slice(4, 7), d.slice(7, 11)].filter(Boolean).join(' ');
    if (d.startsWith('0')) return [d.slice(0, 3), d.slice(3, 7), d.slice(7, 11)].filter(Boolean).join(' ');
    return d;
  }

  // ── Email ─────────────────────────────────────────────────────────────────
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  function distance(a, b) {
    const m = a.length, n = b.length;
    if (Math.abs(m - n) > 2) return 3;
    const row = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      let prev = row[0]; row[0] = i;
      for (let j = 1; j <= n; j++) {
        const tmp = row[j];
        row[j] = Math.min(row[j] + 1, row[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
        prev = tmp;
      }
    }
    return row[n];
  }
  function emailSuggestion(v) {
    const at = v.lastIndexOf('@');
    if (at < 1) return '';
    const domain = v.slice(at + 1).toLowerCase();
    if (!domain || EMAIL_DOMAINS.includes(domain)) return '';
    let best = '', score = 3;
    for (const d of EMAIL_DOMAINS) { const k = distance(domain, d); if (k < score) { score = k; best = d; } }
    return score <= 2 && best ? v.slice(0, at + 1) + best : '';
  }

  // ── Rules ─────────────────────────────────────────────────────────────────
  const LETTERS = /^[\p{L}\p{M}\s\u200c'’.\-]+$/u;
  const countLetters = (s) => (s.match(/\p{L}/gu) || []).length;

  const rules = {
    first_name(v) {
      if (!v) return 'نام خود را بنویسید.';
      if (!LETTERS.test(v)) return 'نام فقط از حروف تشکیل می‌شود.';
      if (countLetters(v) < 2) return 'نام دست‌کم دو حرف دارد.';
      return '';
    },
    last_name(v) {
      if (!v) return 'نام خانوادگی را بنویسید.';
      if (!LETTERS.test(v)) return 'نام خانوادگی فقط از حروف تشکیل می‌شود.';
      if (countLetters(v) < 2) return 'نام خانوادگی دست‌کم دو حرف دارد.';
      return '';
    },
    business_name(v) {
      if (!v) return 'نام کسب‌وکار را بنویسید.';
      if (v.replace(/[\s\u200c]/g, '').length < 2) return 'نام کسب‌وکار دست‌کم دو حرف دارد.';
      return '';
    },
    niche(v) {
      if (!v) return 'حوزهٔ فعالیت را بنویسید.';
      if (countLetters(v) < 2) return 'حوزهٔ فعالیت دست‌کم دو حرف دارد.';
      return '';
    },
    city(v) {
      if (!v) return 'شهر را بنویسید.';
      if (/\d/.test(toLatin(v))) return 'نام شهر عدد ندارد.';
      if (countLetters(v) < 2) return 'نام شهر دست‌کم دو حرف دارد.';
      return '';
    },
    phone(v) {
      if (!v) return 'شمارهٔ تماس را وارد کنید.';
      return parsePhone(v).ok ? '' : `این شماره کامل یا درست نیست؛ نمونه: ${ltr('0912 345 6789')}`;
    },
    email(v) {
      if (!v) return '';
      return EMAIL.test(v) ? '' : `ایمیل درست نیست؛ نمونه: ${ltr('name@example.com')}`;
    },
  };

  const valueOf = (name) => tidy(inputs[name].value);
  const cellOf = (name) => $(`[data-name="${name}"]`);
  const shown = new Set();        // cells whose verdict the reader has been shown
  let attempted = false;

  function paint(name, message) {
    const cell = cellOf(name);
    const msg = cell && $(':scope > .msg > span', cell);
    if (!cell || !msg) return;
    const bad = !!message;
    cell.classList.toggle('is-invalid', bad);
    if (msg.textContent !== message) msg.textContent = message;
    inputs[name].setAttribute('aria-invalid', String(bad));
  }

  function check(name, reveal) {
    const message = rules[name](valueOf(name));
    if (reveal) shown.add(name);
    if (shown.has(name)) paint(name, message);
    return !message;
  }

  function shake(name) {
    if (reduce.matches) return;
    const cell = cellOf(name);
    if (!cell) return;
    cell.classList.remove('shake'); void cell.offsetWidth; cell.classList.add('shake');
    setTimeout(() => cell.classList.remove('shake'), 500);
  }

  // ── Progress ──────────────────────────────────────────────────────────────
  function progress() {
    const done = REQUIRED.filter((n) => !rules[n](valueOf(n))).length;
    const all = done === REQUIRED.length;
    ringFill.style.strokeDashoffset = String(RING * (1 - done / REQUIRED.length));
    progressBtn.toggleAttribute('data-complete', all);
    progressBtn.toggleAttribute('data-empty', done === 0);
    progressText.textContent = all ? 'آمادهٔ ثبت' : `${done} از ${REQUIRED.length}`;
    progressBtn.setAttribute('aria-label', all
      ? 'همهٔ موارد ضروری کامل است؛ رفتن به دکمهٔ ثبت'
      : `${toFa(done)} از ${toFa(REQUIRED.length)} مورد ضروری کامل شده؛ رفتن به مورد بعدی`);
    return done;
  }

  function firstIncomplete() {
    return ORDER.find((n) => {
      if (n === 'email') return !!rules.email(valueOf('email'));
      return REQUIRED.includes(n) && !!rules[n](valueOf(n));
    });
  }

  function focusField(name, { center = true } = {}) {
    inputs[name].focus({ preventScroll: true });
    cellOf(name).scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: center ? 'center' : 'nearest' });
  }

  progressBtn.addEventListener('click', () => {
    if (!viewDone.hidden) { sheet.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' }); return; }
    const next = firstIncomplete();
    if (next) { focusField(next); return; }
    submitBtn.focus({ preventScroll: true });
    submitBtn.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'center' });
  });

  // ── Draft: what has been typed survives a reload, and is gone once it is sent ──
  const store = {
    get() { try { return JSON.parse(localStorage.getItem(DRAFT) || 'null'); } catch { return null; } },
    set(v) { try { localStorage.setItem(DRAFT, JSON.stringify(v)); } catch { /* private mode: fine */ } },
    clear() { try { localStorage.removeItem(DRAFT); } catch { /* fine */ } },
  };
  let saveTimer = 0;
  function saveDraft() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      const d = {};
      Object.keys(inputs).forEach((k) => { d[k] = inputs[k].value; });
      if (Object.values(d).some(Boolean)) store.set(d); else store.clear();
    }, 250);
  }
  function restoreDraft() {
    const d = store.get();
    if (!d || typeof d !== 'object') return;
    Object.keys(inputs).forEach((k) => { if (typeof d[k] === 'string') inputs[k].value = d[k].slice(0, inputs[k].maxLength > 0 ? inputs[k].maxLength : 200); });
  }

  // ── City suggestions ──────────────────────────────────────────────────────
  function cityMatches(q) {
    const n = fold(q);
    if (!n) return POPULAR;
    const starts = [], has = [];
    const typed = tidy(q);
    for (const c of CITIES) {
      const f = fold(c);
      if (f === n && c === typed) return [];               // spelled exactly: nothing to suggest
      if (f === n) starts.unshift(c);                      // same city, other spelling (امل → آمل): offer it first
      else if (f.startsWith(n)) starts.push(c); else if (f.includes(n)) has.push(c);
    }
    return starts.concat(has).slice(0, 6);
  }
  function renderSuggestions() {
    const list = cityMatches(inputs.city.value);
    suggestBox.replaceChildren();
    if (!list.length || document.activeElement !== inputs.city) { suggestBox.hidden = true; return; }
    for (const c of list) {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.city = c;
      b.setAttribute('aria-label', `انتخاب ${c}`);
      b.append(c);
      suggestBox.append(b);
    }
    suggestBox.hidden = false;
  }
  // pointerdown keeps focus in the field, so the list is still there when the click lands.
  ['pointerdown', 'mousedown'].forEach((t) => suggestBox.addEventListener(t, (e) => { if (e.target.closest('button')) e.preventDefault(); }));
  suggestBox.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-city]');
    if (!b) return;
    inputs.city.value = b.dataset.city;
    suggestBox.hidden = true;
    check('city', true); progress(); saveDraft();
    if (!inputs.phone.value) inputs.phone.focus(); else inputs.city.focus();
  });
  inputs.city.addEventListener('focus', renderSuggestions);
  inputs.city.addEventListener('blur', () => setTimeout(() => {
    if (document.activeElement !== inputs.city && !suggestBox.contains(document.activeElement)) suggestBox.hidden = true;
  }, 120));
  suggestBox.addEventListener('focusout', () => setTimeout(() => {
    if (document.activeElement !== inputs.city && !suggestBox.contains(document.activeElement)) suggestBox.hidden = true;
  }, 120));

  // ── Phone: any digits in, Latin digits stored, grouped as it is typed ──────
  inputs.phone.addEventListener('input', () => {
    const el = inputs.phone;
    const atEnd = el.selectionStart === el.value.length;
    let v = toLatin(el.value);
    if (atEnd && !/^\s*(\+|00)/.test(v)) {
      const digits = v.replace(/\D/g, '');
      v = digits.startsWith('0') ? formatIR(digits.slice(0, 11)) : digits;
    }
    if (v !== el.value) {
      el.value = v;
      if (atEnd) el.setSelectionRange(v.length, v.length);
    }
  });

  // ── Email: offer the likely address when the domain looks mistyped ─────────
  function renderEmailHint() {
    const v = inputs.email.value.trim();
    const s = EMAIL.test(v) ? emailSuggestion(v) : '';
    emailHint.replaceChildren();
    if (!s) { emailHint.hidden = true; return; }
    const addr = document.createElement('span'); addr.className = 'brand'; addr.dir = 'ltr'; addr.textContent = s;
    const fix = document.createElement('button'); fix.type = 'button'; fix.textContent = 'اصلاح';
    fix.addEventListener('click', () => {
      inputs.email.value = s; emailHint.hidden = true;
      check('email', true); saveDraft(); inputs.email.focus();
    });
    emailHint.append('منظورتان ', addr, ' است؟ ', fix);
    emailHint.hidden = false;
  }

  // ── Wiring: quiet while typing, honest on leaving ──────────────────────────
  Object.keys(inputs).forEach((name) => {
    const el = inputs[name];
    el.addEventListener('input', () => {
      if (shown.has(name) && $(`[data-name="${name}"]`).classList.contains('is-invalid')) check(name, true);
      if (name === 'city') renderSuggestions();
      if (name === 'email') emailHint.hidden = true;
      progress(); saveDraft();
      hideAlert();
    });
    el.addEventListener('blur', () => {
      if (name === 'phone') {
        const p = parsePhone(el.value);
        if (p.ok && p.value.startsWith('0')) el.value = formatIR(p.value);
      }
      if (name !== 'email' && name !== 'phone') { const t = tidy(el.value); if (t !== el.value) el.value = t; }
      if (el.value.trim() || attempted) check(name, true);
      if (name === 'email') renderEmailHint();
      progress();
    });
    // Enter moves on, the way the keyboard's "next" key promises; the last field sends.
    el.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || e.isComposing || name === 'email') return;
      e.preventDefault();
      if (name === 'city' && !suggestBox.hidden && suggestBox.firstElementChild && tidy(el.value)) {
        suggestBox.firstElementChild.click();                  // Enter takes the first suggestion
        return;
      }
      const next = ORDER[ORDER.indexOf(name) + 1];
      if (next) focusField(next, { center: false });
    });
  });

  // ── Delivery ──────────────────────────────────────────────────────────────
  const failure = (code) => Object.assign(new Error(code), { code });
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  async function send(data) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), C.timeoutMs);
    try {
      if (C.mode === 'endpoint' && C.endpoint) {
        const res = await fetch(C.endpoint, {
          method: 'POST', body: new URLSearchParams(data), signal: ctrl.signal,
          headers: { Accept: 'application/json' }, credentials: 'omit',
        });
        let body = null;
        try { body = await res.json(); } catch { /* not JSON: a server fault */ }
        if (res.status === 429) throw failure('rate');
        if (!res.ok || !body || body.ok !== true) throw failure('server');
        return { ok: true, reference: typeof body.reference === 'string' ? body.reference.slice(0, 40) : '' };
      }
      if (C.mode === 'google-form' && C.googleForm && C.googleForm.action) {
        const body = new URLSearchParams();
        Object.entries(C.googleForm.fields || {}).forEach(([key, entry]) => body.append(entry, data[key] || ''));
        await fetch(C.googleForm.action, { method: 'POST', mode: 'no-cors', body, signal: ctrl.signal, credentials: 'omit' });
        return { ok: true };
      }
      // Preview: ?demo=fail and ?demo=slow let every state be seen. Nothing is sent.
      const hook = new URLSearchParams(location.search).get('demo');
      await wait(hook === 'slow' ? 3500 : 900);
      if (hook === 'fail') throw failure('network');
      console.info('[Went To Event] Preview mode — nothing was sent. Fields:', Object.keys(data).join(', '));
      return { ok: true, demo: true };
    } catch (err) {
      if (err && err.name === 'AbortError') throw failure('timeout');
      if (err && err.code) throw err;
      throw failure('network');
    } finally {
      clearTimeout(timer);
    }
  }

  const FAILURES = {
    network: 'ارسال نشد؛ اتصال اینترنت را بررسی کنید و دوباره «ثبت درخواست» را بزنید.',
    timeout: 'پاسخی نرسید؛ چند لحظهٔ دیگر دوباره امتحان کنید.',
    rate: 'درخواست‌های زیادی پشت سر هم رسید؛ کمی بعد دوباره امتحان کنید.',
    server: 'مشکلی پیش آمد و درخواست ثبت نشد؛ دوباره امتحان کنید.',
  };
  function showAlert(code) { alertBox.textContent = FAILURES[code] || FAILURES.server; alertBox.hidden = false; }
  function hideAlert() { if (!alertBox.hidden) alertBox.hidden = true; }
  function announce(text) { announcer.textContent = ''; setTimeout(() => { announcer.textContent = text; }, 60); }

  function payload() {
    const phone = parsePhone(inputs.phone.value);
    return {
      first_name: tidy(inputs.first_name.value),
      last_name: tidy(inputs.last_name.value),
      business_name: tidy(inputs.business_name.value),
      niche: tidy(inputs.niche.value),
      city: tidy(inputs.city.value),
      phone: phone.value,
      email: inputs.email.value.trim(),
      submitted_at: new Date().toISOString(),
      page: location.origin + location.pathname,
      elapsed_ms: String(Date.now() - t0),
    };
  }

  let busy = false;
  function setBusy(on) {
    busy = on;
    submitBtn.setAttribute('aria-busy', String(on));
    submitLabel.textContent = on ? 'در حال ثبت…' : 'ثبت درخواست';
    form.setAttribute('aria-busy', String(on));
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (busy) return;
    attempted = true;
    hideAlert();
    suggestBox.hidden = true;

    const names = ORDER;
    const bad = names.filter((n) => !check(n, true));
    progress();
    if (bad.length) {
      bad.forEach(shake);
      focusField(bad[0]);
      announce(bad.length === 1 ? 'یک مورد نیاز به اصلاح دارد.' : `${toFa(bad.length)} مورد نیاز به اصلاح دارد.`);
      return;
    }

    const data = payload();
    if ($('#f-website').value) { showDone(data, { ok: true, demo: !live }); return; }   // a bot: thank it, send nothing

    setBusy(true);
    try {
      const result = await send(data);
      store.clear();
      showDone(data, result);
    } catch (err) {
      showAlert(err && err.code);
      announce(alertBox.textContent);
    } finally {
      setBusy(false);
    }
  });

  // ── Done ──────────────────────────────────────────────────────────────────
  function row(label, value, kind) {
    const d = document.createElement('div');
    const dt = document.createElement('dt'); dt.textContent = label;
    const dd = document.createElement('dd'); dd.textContent = value;
    if (kind) dd.dir = 'ltr';
    if (kind === 'lat') dd.className = 'lat';
    d.append(dt, dd);
    return d;
  }
  function showDone(data, result) {
    const demo = !!result.demo;
    $('#done-title').textContent = demo ? 'فرم کامل و درست است' : 'درخواستتان ثبت شد';
    $('[data-done-text]').textContent = demo
      ? `ممنون ${data.first_name}! پاسخ‌ها کامل و درست است.`
      : `ممنون ${data.first_name}! اطلاعات «${data.business_name}» به دست ما رسید؛ پس از بررسی با شما تماس می‌گیریم.`;
    const sum = $('[data-summary]');
    const phoneShown = data.phone.startsWith('0') ? formatIR(data.phone) : data.phone;
    sum.replaceChildren(
      row('نام', `${data.first_name} ${data.last_name}`),
      row('کسب‌وکار', data.business_name),
      row('حوزهٔ فعالیت', data.niche),
      row('شهر', data.city),
      row('شمارهٔ تماس', phoneShown, 'ltr'),
      ...(data.email ? [row('ایمیل', data.email, 'lat')] : []),
      ...(result.reference ? [row('کد پیگیری', result.reference, 'lat')] : []),
    );
    $('[data-done-demo]').hidden = !demo;
    viewForm.hidden = true;
    viewDone.hidden = false;
    progressBtn.hidden = true;
    sheet.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' });
    $('#done-title').focus({ preventScroll: true });
    announce($('#done-title').textContent);
  }

  // Another business, same person: keep who they are and how to reach them.
  $('[data-again]').addEventListener('click', () => {
    ['business_name', 'niche', 'city'].forEach((k) => { inputs[k].value = ''; });
    shown.clear(); attempted = false;
    ORDER.forEach((n) => paint(n, ''));
    viewDone.hidden = true;
    viewForm.hidden = false;
    progressBtn.hidden = false;
    viewForm.classList.remove('is-back'); void viewForm.offsetWidth; viewForm.classList.add('is-back');
    progress(); saveDraft();
    focusField('business_name');
  });

  // ── The scroll edge: on once anything has slid beneath the capsules ─────────
  const edge = $('[data-edge]');
  let edgeQueued = false;
  const paintEdge = () => { edgeQueued = false; edge.toggleAttribute('data-on', scrollY > 8); };
  addEventListener('scroll', () => { if (!edgeQueued) { edgeQueued = true; requestAnimationFrame(paintEdge); } }, { passive: true });
  paintEdge();

  // ── Boot ──────────────────────────────────────────────────────────────────
  if (!live) $('[data-preview-flag]').hidden = false;
  restoreDraft();
  // A restored draft shows its verdicts only for what was actually filled in.
  Object.keys(inputs).forEach((n) => { if (inputs[n].value.trim()) check(n, true); });
  progress();
  document.addEventListener('touchstart', () => {}, { passive: true });   // lets iOS show :active
  window.__wte = { ready: true, live, mode: C.mode };
})();
