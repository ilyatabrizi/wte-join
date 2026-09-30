/* Where a finished form goes. The page reads nothing else from here.
 *
 *   mode: 'demo'         Nothing leaves the browser. The page says so beside the button and on
 *                        the confirmation, and index.html keeps <meta name="robots" noindex>.
 *   mode: 'endpoint'     POST, application/x-www-form-urlencoded (a "simple" request, so no CORS
 *                        preflight), to `endpoint`. Expects JSON back: { ok: true, reference? }.
 *                        The receiver must send Access-Control-Allow-Origin for this page's origin.
 *   mode: 'google-form'  POST to a Google Form's formResponse URL, mode no-cors. `fields` maps
 *                        each key below to that form's entry.NNNN id. Responses land in the form.
 *
 * Keys sent: first_name last_name business_name niche city phone email submitted_at page elapsed_ms
 * (niche is free text, exactly as the person typed it, tidied).
 */
window.WTE_CONFIG = {
  mode: 'demo',
  endpoint: '',
  googleForm: { action: '', fields: {} },
  timeoutMs: 15000,
};
