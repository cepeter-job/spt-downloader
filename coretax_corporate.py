"""Readonly corporate UI bindings pinned to reviewed public build bytes."""
import json
import re
import time
from time import perf_counter as _paginator_clock
from coretax_build_pins import load_build_pins, resolve_role_url
from coretax_json import ORIGIN, JsonSafetyError

# A rotation renames the chunk, so the URL is resolved through the role: the
# reviewed default is used until the overlay records a new filename for it.
CIT_SOURCE_URL = resolve_role_url(
    'cit', ORIGIN + '/returnsheets/id-ID/525.4e63a9d496f5561d.js')
CIT_SOURCE_SHA256 = load_build_pins().get(CIT_SOURCE_URL)
FORMS = {
 'Induk': ('rshshr-citr-main-form', 'MainFormData'),
 'L1-B': ('rshshr-citr-l1b-form', 'L1bFormData'),
 'L1-D': ('rshshr-citr-l1d-form', 'L1dFormData'),
 'L2': ('rshshr-citr-l2-form', 'ListOfOwnership'),
 'L3': ('rshshr-citr-l3-form', 'ListIncomeTaxWithheldByOtherParties'),
 'L4': ('rshshr-citr-l4-form', 'ListOfIncomeSubjectToFinalTaxAndNonTaxableObject'),
 'L6': ('rshshr-citr-l6-form', 'FiscalYearIncomeTax'),
 'L7': ('rshshr-citr-l7-form', 'CalculationOfFiscalLossCompensation'),
 'L8': ('rshshr-citr-l8-form', 'CalculationFacilitiesIncomeTaxRateReduction'),
 'L9': ('rshshr-citr-l9-form', 'RecapitulationFiscalDepreciationAmortization'),
 'L10-A': ('rshshr-citr-l10a-form', 'DeclarationTransactionRelatedParties'),
 'L10-B': ('rshshr-citr-l10b-form', 'L10bFormData'),
 'L10-C': ('rshshr-citr-l10c-form', 'L10cFormData'),
 'L10-D': ('rshshr-citr-l10d-form', 'L10dFormData'),
 'L11-A': ('rshshr-citr-l11a-form', 'L11AFormData'),
 'L11-B': ('rshshr-citr-l11b-form', 'L11BFormData'),
 'L11-C': ('rshshr-citr-l11c-form', 'L11CFormData'),
}
# The inspected native fifth input is not a numeric Group 5 alias.
GROUPS = ('Group 1', 'Group 2', 'Group 3', 'Group 4', 'Other Group')
GRID_ROLES = {
 'L4': (('rshshr-citr-l4-grid1', 'l4-table-a-grid', (None,)),),
 'L9': (('rshshr-citr-l9-form-grid1', 'l9-table-1-grid', GROUPS),
        ('rshshr-citr-l9-form-grid2', 'l9-table-2-grid', ('Permanent','Non-permanent')),
        ('rshshr-citr-l9-form-grid3', 'l9-table-3-grid', GROUPS)),
 'L10-A': (('rshshr-citr-l10a-form-grid1', 'l10a-grid', (None,)),),
}
_REFERENCE_REACQUIRE_TIMEOUT_MS = 8000
_BUILD_HASH = r'''async url => {
 const loaded=[...document.scripts].some(s=>s.src===url) ||
   performance.getEntriesByType('resource').some(e=>e.name===url);
 if(!loaded)return null;
 const response=await fetch(url,{credentials:'same-origin',redirect:'error',cache:'no-store'});
 if(!response.ok || !/javascript/i.test(response.headers.get('content-type')||''))return null;
 const bytes=await response.arrayBuffer();
 if(bytes.byteLength>4*1024*1024)return null;
 return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
   .map(x=>x.toString(16).padStart(2,'0')).join('');
}'''

# Same measurement as _BUILD_HASH but without the "already loaded" precondition:
# a redeploy may serve chunks this page never pulled in, and the overlay records
# what the portal currently serves rather than what this document happened to
# load. Content-type and size guards are identical.
#
# Unlike _BUILD_HASH this returns a fixed state tag instead of null on refusal,
# so the caller can name the failing asset class in a diagnostic without a
# second request: 'missing' (non-2xx), 'fallback_html' (2xx but not JS, the
# ~8 KB shell a retired chunk name serves), 'too_large' (over the byte budget).
_MEASURE_PIN_JS = r'''async url => {
 const response=await fetch(url,{credentials:'same-origin',redirect:'error',cache:'no-store'});
 if(!response.ok)return 'missing';
 if(!/javascript/i.test(response.headers.get('content-type')||''))return 'fallback_html';
 const bytes=await response.arrayBuffer();
 if(bytes.byteLength>4*1024*1024)return 'too_large';
 return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
   .map(x=>x.toString(16).padStart(2,'0')).join('');
}'''

# MAIN is the one reviewed chunk above 4 MiB, so it keeps the same larger byte
# budget the loaded-asset readers already use for it. Measuring it with the
# 4 MiB guard would refuse the very asset a redeploy changes.
_MEASURE_MAIN_PIN_JS = _MEASURE_PIN_JS.replace('4*1024*1024', '5*1024*1024')

# Fixed asset states for the refresh diagnostic. States only: never a URL,
# digest or byte count, which would make the record a source fingerprint.
_REFRESH_STATES = ('alive', 'missing', 'fallback_html', 'too_large')

# Resolve what the portal currently serves for each pinned asset. A rotation
# renames the hashed filename but keeps the numeric chunk id, so the reviewed
# URL's id is looked up in the live webpack map; named chunks (main, vendor)
# are read straight from the shell's script tags. Returns {reviewed_url:
# live_url} for the roles it could resolve, so a rename is followed instead of
# refused. Same-origin only, and never widens the allowlist: the caller still
# measures and verifies whatever comes back.
_DISCOVER_PIN_JS = r'''async urls => {
 const out = {};
 const base = document.baseURI;
 const shell = await (await fetch(base, {credentials:'same-origin',cache:'no-store'})).text();
 const srcs = [...shell.matchAll(/<script[^>]+src="([^"]+)"/g)].map(m => m[1]);
 const runtime = srcs.find(s => /^runtime\./.test(s));
 let map = {};
 if (runtime) {
   const text = await (await fetch(new URL(runtime, base),
     {credentials:'same-origin',cache:'no-store'})).text();
   for (const m of text.matchAll(/(\d{2,4}):"([0-9a-f]{16})"/g)) map[m[1]] = m[2];
 }
 for (const url of urls) {
   const name = url.split('/').pop();
   const id = (name.match(/^(\d{3,4})\./) || [])[1];
   if (id && map[id]) { out[url] = new URL(id + '.' + map[id] + '.js', base).href; continue; }
   const named = srcs.find(s => s.startsWith(name.split('.')[0] + '.'));
   if (named) out[url] = new URL(named, base).href;
 }
 return out;
}'''


def _refresh_asset_role(url):
    """Map a pinned URL to its fixed role, never echoing the URL itself."""
    from coretax_build_pins import role_for_url
    return role_for_url(url)


def _auto_refresh_build_pins(page, check_cancel=None, *, expected_digest):
    """Re-measure every pinned asset from the live page and record it locally.

    The Coretax frontend redeploys without notice; each redeploy used to break
    native capture silently until someone re-measured the JS hashes by hand and
    shipped a release. On drift we measure the assets the reviewed file already
    pins and store the result in a user-scoped overlay, so a redeploy self-heals.

    Only URLs already in the reviewed allowlist are measured and recorded, so
    this can never widen the allowlist.

    Assets are measured independently. A retired chunk name that now serves the
    ~8 KB shell no longer aborts the whole refresh: the assets that still verify
    are recorded, and each refusal is named by fixed role and state.

    Recording and admission are separate. ``expected_digest`` is the digest the
    page loaded, or None when it loaded nothing (a renamed chunk the document
    never referenced). A usable expectation must equal the re-measured CIT asset
    before the build is admitted; when the expectation is missing the verified
    assets are still recorded for the next run, but nothing is admitted. Returns
    the verified mapping when the build is admitted, otherwise None, and the
    caller then keeps the fail-closed DOM fallback.
    """
    from coretax_build_pins import load_build_pins, record_local_pins
    from coretax_browser import _check_cancel
    pins = load_build_pins()
    if not pins:
        return None
    # Follow a rename before measuring: the reviewed URL may now serve the SPA
    # shell, but the same chunk id usually still exists under a new hash.
    try:
        discovered = page.evaluate(_DISCOVER_PIN_JS, list(pins)) or {}
    except Exception:
        discovered = {}
    if not isinstance(discovered, dict):
        discovered = {}
    measured, refused = {}, []
    for url in pins:
        _check_cancel(check_cancel)
        live = discovered.get(url) or url
        script = _MEASURE_MAIN_PIN_JS if _refresh_asset_role(url) == 'main' else _MEASURE_PIN_JS
        try:
            result = page.evaluate(script, live)
        except Exception:
            # A driver/navigation failure is this asset's refusal, not the
            # whole refresh's: the remaining assets still get measured.
            refused.append((url, 'missing'))
            continue
        if isinstance(result, str) and len(result) == 64:
            # Recorded under the live URL so the role follows the rename.
            measured[live] = result
        else:
            refused.append((url, result if result in _REFRESH_STATES else 'missing'))
    _record_refresh_refusals(refused)
    # A missing/unusable expectation means this page loaded nothing we can
    # compare against (a renamed chunk). Record what does verify so the next
    # run can use it, but never admit: None == None must not admit a build.
    usable = (isinstance(expected_digest, str) and len(expected_digest) == 64
              and all(c in '0123456789abcdef' for c in expected_digest))
    if not usable:
        # Persist only a positively measured CIT asset; an unverified build is
        # never recorded as admitted.
        if measured.get(discovered.get(CIT_SOURCE_URL) or CIT_SOURCE_URL) is not None:
            record_local_pins(measured)
        return None
    if measured.get(discovered.get(CIT_SOURCE_URL) or CIT_SOURCE_URL) != expected_digest:
        # A positive mismatch means the page and the server disagree right now,
        # so nothing is persisted: recording it would poison the next run.
        return None
    if not record_local_pins(measured):
        return None
    return measured


def _record_refresh_refusals(refused):
    """Name each asset that did not verify, by fixed role and state only."""
    if not refused:
        return
    from spt_desktop import diagnostics
    for url, state in refused:
        diagnostics.record('build.refresh_refused', level='WARNING',
                           build_source='corporate',
                           refresh_asset=_refresh_asset_role(url),
                           refresh_asset_state=state)


def _tabs(page):
    view = page.locator('.main-content .p-tabview').first
    tabs = view.locator(':scope > .p-tabview-nav-container > .p-tabview-nav-content > .p-tabview-nav > li > a[role=tab]')
    if not tabs.count():
        tabs = view.locator(':scope > .p-tabview-nav > li > a[role=tab]')
    return view, tabs


def _enabled_form_binding(form, tab, caption):
    """Recheck only inspected tab/panel ownership, never business controls."""
    handle = tab.element_handle()
    try:
        return form.evaluate('''(form, {tab, caption}) => {
            if (!tab || !tab.isConnected || !form.isConnected) return false;
            const li=tab.closest('li'), view=form.closest('.p-tabview');
            const panel=form.closest('.p-tabview-panel'), id=tab.getAttribute('aria-controls');
            const href=tab.getAttribute('href');
            const bounds=form.getBoundingClientRect(), style=getComputedStyle(form);
            return !!li && !!view && !!panel && tab.closest('.p-tabview')===view &&
                style.visibility==='visible' && bounds.width>0 && bounds.height>0 &&
                tab.textContent.trim()===caption && !li.classList.contains('p-disabled') &&
                tab.getAttribute('aria-disabled')!=='true' && !!id && panel.id===id &&
                [...view.querySelectorAll('[id]')].filter(e=>e.id===id).length===1 &&
                (href===null || href==='' || href==='#' || href==='#'+id);
        }''', {'tab': handle, 'caption': caption}) is True
    finally:
        if handle is not None:
            try:
                handle.dispose()
            except Exception:  # nosec B110 - Owned cleanup must not replace Stop or the original failure.
                pass


def _native_panel(page, view, tab, caption, record, check_cancel):
    """Tunggu binding tab terbaru, lalu pertahankan batas struktur native."""
    from coretax_browser import (_check_cancel, _wait_tab_panel, wait_idle,
                                 verify_detail_url, list_taxpayer_id)
    _check_cancel(check_cancel)
    initial_id = tab.get_attribute('aria-controls')
    allowed_href = (None, '', '#') + (('#' + initial_id,) if initial_id else ())
    if tab.get_attribute('href') not in allowed_href:
        return None
    if tab.inner_text().strip() != caption:
        return None
    tab.click()
    wait_idle(page)
    verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
    panel = _wait_tab_panel(view, tab, caption, check_cancel,
                            initial_panel_id=initial_id or None)
    _check_cancel(check_cancel)
    current_id = tab.get_attribute('aria-controls')
    allowed_href = (None, '', '#') + (('#' + current_id,) if current_id else ())
    if tab.get_attribute('href') not in allowed_href:
        return None
    # Native bindings still reject duplicate IDs, including nested targets.
    if current_id and view.locator('[id=' + json.dumps(current_id) + ']').count() != 1:
        return None
    owner = view.element_handle()
    try:
        direct = panel.evaluate('''(e, owner) => {
            const parent = e.parentElement;
            const panels = parent.matches('p-tabpanel') ? parent.parentElement : parent;
            return e.matches('.p-tabview-panel') && panels.matches('.p-tabview-panels') &&
                panels.parentElement === owner && e.closest('.p-tabview') === owner;
        }''', owner)
        if direct is not True:
            return None
    finally:
        owner.dispose()
    verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
    return panel


def _turn_grid(page, table, max_pages, check_cancel):
    from coretax_browser import (
        _check_cancel, wait_idle, NATIVE_PAGINATOR_INSPECT_JS,
        NATIVE_PAGINATOR_CLICK_JS,
    )
    from spt_desktop import diagnostics
    if type(max_pages) is not int or max_pages <= 0:
        return False
    previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
    next_selector = '.p-paginator-next:not([disabled]):not(.p-disabled)'
    marker = table.locator('.p-paginator-current')
    owner = table.element_handle()
    if owner is None:
        return False

    # Keep the original table owner and marker deadlines. Per-page control
    # inspection now takes one owned renderer RPC; clicking takes one more.
    # Only fixed timing categories are logged; marker text never leaves memory.
    steps = {step: [0.0, 0] for step in (
        'reset_probe', 'reset_click', 'reset_marker_wait', 'reset_overlay_wait',
        'advance_probe', 'advance_click', 'advance_marker_wait',
        'advance_overlay_wait')}
    wall_start = _paginator_clock()

    def timed(step, action):
        began = _paginator_clock()
        try:
            return action()
        finally:
            steps[step][0] += (_paginator_clock() - began) * 1000
            steps[step][1] += 1

    def inspect(selector, direction):
        # The owned p-table must remain connected and unambiguous. Do not
        # re-resolve against the document or infer a page from business rows.
        return timed(direction + '_probe',
                     lambda: owner.evaluate(NATIVE_PAGINATOR_INSPECT_JS, selector))

    def advance(state, selector, direction):
        _check_cancel(check_cancel)
        clicked = timed(direction + '_click',
                        lambda: owner.evaluate(NATIVE_PAGINATOR_CLICK_JS,
                                               {'selector': selector, 'marker': state}))
        if clicked is not True:
            return False

        def marker_change():
            deadline = time.monotonic() + 30
            while marker.inner_text() == state:
                _check_cancel(check_cancel)
                if time.monotonic() >= deadline:
                    return False
                page.wait_for_timeout(100)
            return True

        if not timed(direction + '_marker_wait', marker_change):
            return False
        timed(direction + '_overlay_wait', lambda: wait_idle(page))
        return True

    try:
        if marker.count() != 1:
            return False
        resets = set()
        for _ in range(max_pages):
            _check_cancel(check_cancel)
            previous = inspect(previous_selector, 'reset')
            if previous.get('status') == 'absent':
                break
            if previous.get('status') != 'ready' or type(previous.get('marker')) is not str:
                return False
            state = previous['marker']
            if state in resets or not advance(state, previous_selector, 'reset'):
                return False
            resets.add(state)
        # The reset must demonstrably reach the first page; no bounded
        # fallback can treat a remaining Previous control as complete.
        _check_cancel(check_cancel)
        previous = inspect(previous_selector, 'reset')
        if previous.get('status') != 'absent':
            return False

        seen = set()
        for ordinal in range(max_pages):
            _check_cancel(check_cancel)
            next_page = inspect(next_selector, 'advance')
            if (next_page.get('status') not in ('ready', 'absent')
                    or type(next_page.get('marker')) is not str):
                return False
            state = next_page['marker']
            if state in seen:
                return False
            seen.add(state)
            if next_page['status'] == 'absent':
                return True
            if ordinal + 1 >= max_pages or not advance(state, next_selector, 'advance'):
                return False
        return False
    finally:
        owner.dispose()
        wall_ms = (_paginator_clock() - wall_start) * 1000
        attributed_ms = sum(duration for duration, _ in steps.values())
        for step, (duration, count) in steps.items():
            if count:
                diagnostics.record('native.paginator_timing',
                                   native_paginator_step=step, duration_ms=duration,
                                   count=count)
        # Residual covers non-probe host checks and accounting, not network.
        diagnostics.record('native.paginator_timing',
                           native_paginator_step='other',
                           duration_ms=max(0.0, wall_ms - attributed_ms), count=1)
        diagnostics.record('native.paginator_timing',
                           native_paginator_step='total', duration_ms=wall_ms,
                           count=1)


_L1D_OMISSION_SHAPE = '''table => {
    if(!table.isConnected || table.tBodies.length!==1)return false;
    const rows=[...table.tBodies[0].rows];
    const visible=e=>!!e.getClientRects().length &&
        !['hidden','collapse'].includes(getComputedStyle(e).visibility);
    return rows.length===34 && rows.every(row=>visible(row) && row.cells.length===10 &&
        [...row.cells].every(cell=>cell.closest('table')===table &&
            cell.colSpan===1 && cell.rowSpan===1 && visible(cell)));
}'''


def _observe_l10c_history(form, tab, panel, capture, check_cancel):
    """Observe C-owned custody only; this does not authorize a body projection.

    Returns None on success, or a fixed-enum subreason naming the first failed
    predicate so a live run can be diagnosed without payloads.
    """
    from coretax_browser import _check_cancel
    if any(not callable(getattr(capture, name, None)) for name in
           ('bind_l10c_structure', 'observe_l10c_lifetime')):
        return 'capture_api'
    _check_cancel(check_cancel)
    # Source controls are inspected by identity and disabled structure, never
    # by values/checked state. Legacy/safely unsupported shapes keep fallback.
    if (form.locator('input[formcontrolname="PeriodYear"]').count() != 1
            or form.locator('input[formcontrolname="CollectorTin"]').count() != 1
            or form.locator('p-radiobutton[formcontrolname="Question"]').count() != 2):
        return 'source_controls'
    grid = form.locator('rsh-citr-l10c-grid1')
    table = grid.locator('table')
    if (grid.count() != 1 or grid.locator('ui-grid-offline').count() != 1
            or grid.locator('p-table').count() != 1 or table.count() != 1
            or form.locator('table').count() != 1):
        return 'grid_structure'
    if not capture.bind_l10c_structure(form, grid, table, tab, panel,
                                       phase='start', check_cancel=check_cancel):
        return 'bind_start_' + (getattr(capture, '_l10c_bind_reason', None) or 'unknown')
    if not capture.bind_l10c_structure(form, grid, table, tab, panel,
                                       phase='end', check_cancel=check_cancel):
        return 'bind_end_' + (getattr(capture, '_l10c_bind_reason', None) or 'unknown')
    if capture.observe_l10c_lifetime(check_cancel=check_cancel) is None:
        return 'lifetime'
    return None


def _observe_l10c_projection(page, form, tab, panel, capture, check_cancel):
    """Offer only shared passive catalogs and positively loaded exact providers."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import (L10C_BUILD_DIGESTS, L10C_HEADERS, MAIN_SOURCE, VENDOR_SOURCE)
    from coretax_json import CORPORATE_REFERENCE_REQUESTS
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH
    from spt_desktop import diagnostics

    def _refuse(gate):
        # Fixed-enum diagnostic: name the exact predicate that dropped the
        # L10-C projection so a live run can be diagnosed without payloads.
        diagnostics.record('corporate.l10c_detail_gate', corporate_l10c_detail_gate=gate)
        return None

    history = _observe_l10c_history(form, tab, panel, capture, check_cancel)
    if history is not None:
        return _refuse('history_' + history)
    needed = {'COUNTRY_CODE', 'TRANSACTION_TYPE'}
    urls = {url: kinds for url, kinds in CORPORATE_REFERENCE_REQUESTS.items() if set(kinds) <= needed}
    if set().union(*map(set, urls.values())) != needed:
        return _refuse('reference_catalogs')  # The independent shared producer has not been integrated.
    pins = L10C_BUILD_DIGESTS
    if (set(pins) != {CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value) for value in pins.values())):
        return _refuse('build_pins')
    route, builds = page.url, {}
    for url in (CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE):
        _check_cancel(check_cancel)
        script = _PPN_MAIN_BUILD_HASH if url == MAIN_SOURCE else _BUILD_HASH
        script = script.replace('s=>s.src===url', 's=>s.isConnected&&s.src===url').replace(
            'e=>e.name===url)', "e=>e.name===url&&e.initiatorType==='script')")
        digest = page.evaluate(script, url)
        _check_cancel(check_cancel)
        if type(digest) is not str or not re.fullmatch(r'[a-f0-9]{64}', digest) or digest != pins[url]:
            return _refuse('build_digests')
        builds[url] = digest
    environment = page.evaluate('''() => ({locale:navigator.language,
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})''')
    _check_cancel(check_cancel)
    if environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}:
        return _refuse('environment')
    metadata = form.locator('rsh-citr-l10c-grid1').locator('table').evaluate(TABLE.replace('GROUP', '()=>""'))
    if (not isinstance(metadata, dict) or metadata.get('headers') != L10C_HEADERS
            or metadata.get('footer_spans') != []):
        return _refuse('table_metadata')
    references, kinds_seen = [], set()
    observations = _reacquire_reference_observations(page, capture, list(urls), check_cancel)
    for url, kinds in sorted(urls.items()):
        sequences = sorted({event['sequence'] for event in observations if event['url'] == url
                            and event['method'] == 'GET' and event['request_json'] is None
                            and event.get('status') in (None, 200)})
        if sequences:
            references.append({'endpoint': url, 'method': 'GET', 'sequences': sequences})
            kinds_seen.update(kinds)
    if (kinds_seen != needed or page.url != route
            or capture.observe_l10c_lifetime(check_cancel=check_cancel) is None):
        return _refuse('references_or_lifetime')
    return {'kind': 'corporate-l10c-v1', 'builds': builds, 'route': route, **environment,
        'visibility_binding': 'current-induk-enabled-v1', 'references': references,
        'tables': [{'component': 'rsh-citr-l10c-grid1', 'headers': list(L10C_HEADERS), 'footer_spans': []}]}


def _observe_l7_negative(page, form, grid, tab, panel, capture, legacy, check_cancel):
    """Additive value-free capability; v1 survives unavailable optional proof."""
    from spt_desktop import diagnostics
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import (L7_NEGATIVE_BUILD_DIGESTS, L7_OWNER_CHAIN,
                                              MAIN_SOURCE, VENDOR_SOURCE)
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH

    def gate(name):
        # Fixed enum only: this optional proof must name its own refusal stage
        # without carrying payloads, digests, routes, identifiers or values.
        diagnostics.record('corporate.l7_negative_gate', corporate_l7_negative_gate=name)
        return None

    def read(operation):
        _check_cancel(check_cancel)
        try:
            result = operation()
        except JsonSafetyError:
            _check_cancel(check_cancel)
            raise
        except Exception:
            result = None  # Driver/source unavailability never certifies a provider.
        _check_cancel(check_cancel)
        # Reconcile callback-pumped route/Document contradictions even when an
        # optional driver operation failed. Stop remains outside the catch.
        capture.observe_component_lifetime(check_cancel=check_cancel)
        return result

    pins = L7_NEGATIVE_BUILD_DIGESTS
    urls = (CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE)
    if any(not callable(getattr(capture, name, None)) for name in
           ('observe_component_lifetime', 'bind_l7_structure', 'observe_l7_lifetime')):
        return gate('protocol')  # Legacy structural callers need no new optional protocol.
    if (set(pins) != set(urls) or any(type(value) is not str
            or not re.fullmatch(r'[a-f0-9]{64}', value) for value in pins.values())):
        return gate('pins')
    if read(lambda: _enabled_form_binding(form, tab, 'L7')) is not True:
        return gate('enabled')
    table = grid.locator('table')
    if not capture.bind_l7_structure(form, grid, table, tab, panel, phase='start', check_cancel=check_cancel):
        return gate('structure_start')
    first = read(lambda: table.evaluate(TABLE.replace('GROUP', '()=>""')))
    environment = read(lambda: page.evaluate('''() => ({locale:navigator.language,
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})'''))
    if environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}:
        return gate('environment')
    builds = {}
    for url in urls:
        # Preserve MAIN's 5MiB reader. Only this optional capability strengthens
        # provider predicates; generic/v1 readers remain byte-for-byte separate.
        script = _PPN_MAIN_BUILD_HASH if url == MAIN_SOURCE else _BUILD_HASH
        script = script.replace('s=>s.src===url', 's=>s.isConnected&&s.src===url').replace(
            'e=>e.name===url)', "e=>e.name===url&&e.initiatorType==='script')")
        digest = read(lambda: page.evaluate(script, url))
        if type(digest) is not str or not re.fullmatch(r'[a-f0-9]{64}', digest) or digest != pins[url]:
            return gate('builds')
        builds[url] = digest
    last = read(lambda: table.evaluate(TABLE.replace('GROUP', '()=>""')))
    expected = legacy['tables'][0]
    if (not isinstance(first, dict) or not isinstance(last, dict)
            or any(sample.get(key) != expected[key] for sample in (first, last)
                   for key in ('headers', 'footer_spans'))):
        return gate('table')
    if page.url != legacy['route']:
        return gate('route')
    if read(lambda: _enabled_form_binding(form, tab, 'L7')) is not True:
        return gate('enabled_end')
    if not capture.bind_l7_structure(form, grid, table, tab, panel, phase='end', check_cancel=check_cancel):
        return gate('structure_end')
    if capture.observe_l7_lifetime(check_cancel=check_cancel) is None:
        return gate('lifetime')
    return {'kind': 'corporate-l7-stable-negative-v1', 'builds': builds,
            'route': legacy['route'], **environment, 'visibility_binding': 'current-induk-enabled-v1',
            'tables': [{**expected, 'owner_chain': list(L7_OWNER_CHAIN)}]}


def _observe_l2(page, form, tab, capture, digest, check_cancel):
    """Only exact offline owners/providers; references stay passively produced."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import (L2_BUILD_DIGESTS, L2_COMPONENTS, L2_GROUPS,
        L2_SHAREHOLDER_HEADERS, L2_SHAREHOLDER_SPANS, L2_AFFILIATE_HEADERS,
        L2_AFFILIATE_SPANS, MAIN_SOURCE, VENDOR_SOURCE)
    from coretax_json import CORPORATE_REFERENCE_REQUESTS
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    _check_cancel(check_cancel)
    # Legacy synthetic/held shapes keep v1 quarantine without extra source reads.
    if not callable(getattr(capture, 'observe_component_lifetime', None)) or form.locator('table').count() != 2:
        _check_cancel(check_cancel)
        return None
    if (any(form.locator('input[formcontrolname="' + name + '"]').count() != 1
            for name in ('TaxPeriodYear', 'CollectorTin'))
            or form.locator('ui-grid-offline-body .loading-container').count()):
        _check_cancel(check_cancel)
        return None
    _check_cancel(check_cancel)
    if (set(L2_BUILD_DIGESTS) != {CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in L2_BUILD_DIGESTS.values())
            or digest != L2_BUILD_DIGESTS[CIT_SOURCE_URL]
            or capture.observe_component_lifetime(check_cancel=check_cancel) is None):
        return None
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.isConnected && s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        return None
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if main_digest != L2_BUILD_DIGESTS[MAIN_SOURCE] or vendor_digest != L2_BUILD_DIGESTS[VENDOR_SOURCE]:
        return None
    tables = []
    for index, (headers, spans) in enumerate(((L2_SHAREHOLDER_HEADERS, L2_SHAREHOLDER_SPANS),
                                             (L2_AFFILIATE_HEADERS, L2_AFFILIATE_SPANS))):
        grid = form.locator(L2_COMPONENTS[index])
        if (grid.count() != 1 or not grid.is_visible() or grid.locator('ui-grid-offline').count() != 1
                or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1):
            return None
        table = grid.locator('table')
        chain = table.evaluate('''(table, selector) => {
            const form=table.closest('rshshr-citr-l2-form'), grid=table.closest(selector);
            const p=table.closest('p-table'), ui=table.closest('ui-grid-offline');
            if(!form || !grid || !p || !ui || p.closest('ui-grid-offline')!==ui ||
               ui.closest(selector)!==grid || grid.closest('rshshr-citr-l2-form')!==form ||
               p.closest(selector)!==grid)return false;
            for(let n=table.parentElement;n&&n!==form;n=n.parentElement)
                if(n.localName.endsWith('-form'))return false;
            return true;
        }''', L2_COMPONENTS[index])
        _check_cancel(check_cancel)
        structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L2')
        metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
        _check_cancel(check_cancel)
        if (chain is not True or structure != {'form': 'L2', 'component': L2_COMPONENTS[index],
                'groups': [L2_GROUPS[index]]} or metadata['headers'] != headers or metadata['footer_spans'] != spans):
            return None
        tables.append({'component': L2_COMPONENTS[index], 'source_structure': structure,
            'headers': metadata['headers'], 'footer_spans': metadata['footer_spans']})
    references = []
    l2_urls = [url for url, kinds in CORPORATE_REFERENCE_REQUESTS.items()
               if kinds and not set(kinds) - {'COUNTRY_CODE', 'RELATED_PERSON_TYPE'}]
    observations = _reacquire_reference_observations(page, capture, l2_urls, check_cancel)
    for url, kinds in CORPORATE_REFERENCE_REQUESTS.items():
        if not kinds or set(kinds) - {'COUNTRY_CODE', 'RELATED_PERSON_TYPE'}:
            continue
        sequences = [item['sequence'] for item in observations if item['url'] == url
                     and item['method'] == 'GET' and item.get('request_json') is None
                     and item.get('status') in (None, 200)]
        if sequences:
            references.append({'endpoint': url, 'method': 'GET', 'sequences': sequences})
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if (environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
            or capture.observe_component_lifetime(check_cancel=check_cancel) is None
            or not _enabled_form_binding(form, tab, 'L2')):
        return None
    _check_cancel(check_cancel)
    return {'kind': 'corporate-l2-owner-v2', 'builds': {CIT_SOURCE_URL: digest,
        MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest}, 'route': page.url,
        **environment, 'tables': tables, 'references': references}


def _observe_l11b_hydrated(page, form, tab, capture, digest, main_digest, check_cancel):
    """Optional eager-child submitted profile; structure only, no business reads."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import (L11B_HYDRATED_BUILD_DIGESTS, MAIN_SOURCE,
                                              VENDOR_SOURCE, l11b_tables)
    from coretax_masa_observer import TABLE, _REFERENCE_ORDER_BUILD_HASH
    pins = L11B_HYDRATED_BUILD_DIGESTS
    if (set(pins) != {CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value) for value in pins.values())
            or digest != pins[CIT_SOURCE_URL] or main_digest != pins[MAIN_SOURCE]):
        return None
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        return None
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if type(vendor_digest) is not str or vendor_digest != pins[VENDOR_SOURCE]:
        return None
    # All required grid sets, not merely whichever conditional grid was last
    # sampled. Both passes also retain original form identity and enabled owner.
    samples = []
    identity = form.element_handle()
    if identity is None:
        return None
    try:
        for _ in range(2):
            _check_cancel(check_cancel)
            if (identity.evaluate('(e) => e.isConnected') is not True
                    or not _enabled_form_binding(form, tab, 'L11-B')):
                return None
            present = [form.locator(f'rsh-citr-l11b-form-grid{index}').count() for index in (1, 2, 3)]
            if present not in ([1, 1, 1], [0, 0, 1]):
                return None
            expected = l11b_tables(present == [1, 1, 1])
            if form.locator('table').count() != len(expected):
                return None
            inspected = []
            for metadata in expected:
                selector = metadata['component']
                grid = form.locator(selector)
                if (not grid.is_visible() or grid.locator('table').count() != 1
                        or grid.locator('ui-grid-offline').count() != 1 or grid.locator('p-table').count() != 1):
                    return None
                table = grid.locator('table')
                owned = table.evaluate('''(table, selector) => {
                    const form=table.closest('rshshr-citr-l11b-form'), grid=table.closest(selector);
                    const ui=table.closest('ui-grid-offline'), owner=table.closest('p-table');
                    return !!form && !!grid && !!ui && !!owner &&
                        grid.closest('rshshr-citr-l11b-form')===form && ui.closest(selector)===grid &&
                        owner.closest('ui-grid-offline')===ui && owner.closest(selector)===grid &&
                        table.closest('rshshr-citr-l11b-form')===form;
                }''', selector)
                _check_cancel(check_cancel)
                if owned is not True:
                    return None
                structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L11-B')
                data = table.evaluate(TABLE.replace('GROUP', '()=>""'))
                _check_cancel(check_cancel)
                actual = {'component': selector, 'source_structure': structure,
                          'headers': data['headers'], 'footer_spans': data['footer_spans']}
                if actual != metadata:
                    return None
                inspected.append(actual)
            samples.append(inspected)
        if (samples[0] != samples[1] or identity.evaluate('(e) => e.isConnected') is not True
                or capture.observe_component_lifetime(check_cancel=check_cancel) is None):
            return None
        _check_cancel(check_cancel)
        return {'kind': 'corporate-l11b-hydrated-v2', 'builds': {
            CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest},
            'route': page.url, 'part_ii': len(samples[0]) == 3, 'tables': samples[0]}
    finally:
        identity.dispose()


def _observe_l1d(page, form, capture, digest, check_cancel):
    """Inspect only owned structure, loaded providers and fresh lifetime."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import L1D_BUILD_DIGESTS, L1D_OMISSION_LAYOUT, MAIN_SOURCE, VENDOR_SOURCE
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    if digest != L1D_BUILD_DIGESTS.get(CIT_SOURCE_URL):
        return None
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return None
    _check_cancel(check_cancel)
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        return None
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if (main_digest != L1D_BUILD_DIGESTS.get(MAIN_SOURCE)
            or vendor_digest != L1D_BUILD_DIGESTS.get(VENDOR_SOURCE)
            or form.locator('table').count() != 3):
        return None
    tables, body_layout = [], None
    for index in range(3):
        _check_cancel(check_cancel)
        selector = f'rsh-citr-l1d-grid{index + 1}'
        grid = form.locator(selector)
        if (grid.count() != 1 or not grid.is_visible()
                or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1
                or grid.locator('rshshr-citr-financial-statement-grid').count() != (1 if index == 0 else 0)):
            return None
        table = grid.locator('table')
        _check_cancel(check_cancel)
        chain = table.evaluate('''(table, {selector, financial}) => {
            const form=table.closest('rshshr-citr-l1d-form'), grid=table.closest(selector);
            const owner=table.closest('p-table'), wrapper=table.closest('rshshr-citr-financial-statement-grid');
            if(!form || !grid || grid.closest('rshshr-citr-l1d-form')!==form ||
               !owner || !grid.contains(owner) || owner.closest(selector)!==grid ||
               owner.closest('rshshr-citr-l1d-form')!==form)return false;
            if(!financial)return wrapper===null;
            return !!wrapper && wrapper.contains(owner) && owner.closest('rshshr-citr-financial-statement-grid')===wrapper &&
                wrapper.closest(selector)===grid && wrapper.closest('rshshr-citr-l1d-form')===form;
        }''', {'selector': selector, 'financial': index == 0})
        _check_cancel(check_cancel)
        if chain is not True:
            return None
        structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L1-D')
        if structure != {'form': 'L1-D', 'component': selector,
                         'groups': ['A. LAPORAN LABA RUGI' if index == 0 else 'B. LAPORAN POSISI KEUANGAN']}:
            return None
        metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
        _check_cancel(check_cancel)
        tables.append({'component': selector, 'source_structure': structure,
                       'headers': metadata['headers'], 'footer_spans': metadata['footer_spans']})
        if index == 0:
            # Structural proof only: never read body text or control values.
            if table.evaluate(_L1D_OMISSION_SHAPE) is True:
                body_layout = L1D_OMISSION_LAYOUT
            _check_cancel(check_cancel)
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return None
    if body_layout is not None:
        stable = form.locator('rsh-citr-l1d-grid1 table').evaluate(_L1D_OMISSION_SHAPE)
        _check_cancel(check_cancel)
        if stable is not True:
            return None
    return {'kind': 'corporate-l1d-v1', 'builds': {
        CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest},
        'route': page.url, **environment, 'tables': tables,
        **({'body_layout': body_layout} if body_layout is not None else {})}


def _observe_l8(page, form, capture, digest, check_cancel):
    """Bind the single L8 structure without reading amounts or business controls."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import L8_BUILD_DIGESTS, L8_HEADERS, _L8_GROUP, MAIN_SOURCE, VENDOR_SOURCE
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    if digest != L8_BUILD_DIGESTS.get(CIT_SOURCE_URL):
        capture.l8_refuse('l8_digest')
        return None
    if capture.observe_l8_lifetime(check_cancel=check_cancel) is None:
        return None
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        capture.l8_refuse('l8_providers')
        return None
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    grid = form.locator('rsh-citr-l8-form-grid1')
    if (main_digest != L8_BUILD_DIGESTS.get(MAIN_SOURCE)
            or vendor_digest != L8_BUILD_DIGESTS.get(VENDOR_SOURCE)
            or form.locator('table').count() != 1 or grid.count() != 1 or not grid.is_visible()
            or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1):
        capture.l8_refuse('l8_structure')
        return None
    table = grid.locator('table')
    structure = table.evaluate('''table => {
        const form=table.closest('rshshr-citr-l8-form'), grid=table.closest('rsh-citr-l8-form-grid1');
        const panel=table.closest('.p-tabview-panel'), owner=table.closest('p-table');
        if(!form||!grid||!panel||!owner||form.closest('.p-tabview-panel')!==panel||
           grid.closest('rshshr-citr-l8-form')!==form||!grid.contains(owner)||
           owner.closest('rsh-citr-l8-form-grid1')!==grid)return null;
        const groups=[];
        for(let node=table.parentElement;node&&node!==form;node=node.parentElement){
            if(node.localName.startsWith('rsh')&&node!==grid)return null;
            if(!['p-panel','p-accordiontab'].includes(node.localName))continue;
            const selector=node.localName==='p-panel'?'.p-panel-title':'.p-accordion-header-text';
            let headings=[...node.querySelectorAll(selector)].filter(e=>e.closest(node.localName)===node);
            if(!headings.length&&node.localName==='p-accordiontab')
                headings=[...node.querySelectorAll('.p-accordion-header a')].filter(e=>e.closest('p-accordiontab')===node);
            if(headings.length!==1)return null;
            groups.unshift((headings[0].textContent||'').replace(/\\s+/g,' ').trim());
        }
        return {form:'L8',component:'rsh-citr-l8-form-grid1',groups};
    }''')
    _check_cancel(check_cancel)
    if structure != {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1', 'groups': [_L8_GROUP]}:
        capture.l8_refuse('l8_grid_structure')
        return None
    metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if (metadata['headers'] != L8_HEADERS or metadata['footer_spans'] != [[1, 1, 1]]
            or capture.observe_l8_lifetime(check_cancel=check_cancel) is None):
        if capture.l8_refusal_reason() is None:
            capture.l8_refuse('l8_metadata')
        return None
    return {'kind': 'corporate-l8-v1', 'builds': {
        CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest},
        'route': page.url, **environment, 'tables': [{'component': 'rsh-citr-l8-form-grid1',
            'headers': metadata['headers'], 'footer_spans': metadata['footer_spans'],
            'source_structure': structure}]}


def _l3_extra_table_layout(form):
    # Count only already-rendered structure inside the verified selected form.
    # Categorization is diagnostic; none of these outcomes grants native JSON.
    return form.evaluate("""form => {
      const tables=[...form.querySelectorAll('table')];
      const a=[...form.querySelectorAll('rsh-citr-l3-grid1 ui-grid-offline p-table table')];
      const b=[...form.querySelectorAll('rshshr-citr-l3-grid2 ui-grid p-table table')];
      if(a.length!==1 || b.length!==1 || a[0]===b[0] ||
          a[0].closest('rshshr-citr-l3-form')!==form ||
          b[0].closest('rshshr-citr-l3-form')!==form)
        return 'reviewed_pair_unproved';
      const extra=tables.filter(t=>t!==a[0] && t!==b[0]);
      if(!extra.length) return 'reviewed_pair_unproved';
      return extra.every(t=>!t.getClientRects().length ||
          ['hidden','collapse'].includes(getComputedStyle(t).visibility))
          ? 'reviewed_pair_hidden_extra' : 'reviewed_pair_visible_extra';
    }""", timeout=1000)


def _l3_visible_extra_owner(form):
    # Diagnostic-only: never admit a third table into the native projection.
    return form.evaluate("""form => {
      const a=[...form.querySelectorAll('rsh-citr-l3-grid1 ui-grid-offline p-table table')];
      const b=[...form.querySelectorAll('rshshr-citr-l3-grid2 ui-grid p-table table')];
      if(a.length!==1 || b.length!==1 || a[0]===b[0])
        return 'reviewed_pair_unproved';
      const extra=[...form.querySelectorAll('table')].filter(t=>t!==a[0] &&
        t!==b[0] && !!t.getClientRects().length &&
        !['hidden','collapse'].includes(getComputedStyle(t).visibility));
      if(!extra.length) return 'no_visible_extra';
      const owners=new Set(extra.map(t=>{
        const outer=t.parentElement?.closest('table');
        if(outer===a[0] || outer===b[0]) return 'nested_in_reviewed_table';
        if(t.closest('rsh-citr-l3-grid1,rshshr-citr-l3-grid2'))
          return 'reviewed_grid_extra';
        return 'other_form_owner';
      }));
      return owners.size===1 ? [...owners][0] : 'mixed_owners';
    }""", timeout=1000)


def _l3_standalone_layout(form):
    """Prove the pinned header-only overseas controls, never their values."""
    from coretax_corporate_projection import _L3_LAYOUT_CAPTIONS
    return form.evaluate(r'''(form, caption_sets) => {
      const a=[...form.querySelectorAll('rsh-citr-l3-grid1')];
      const b=[...form.querySelectorAll('rshshr-citr-l3-grid2')];
      const tables=[...form.querySelectorAll('table')];
      if(a.length!==1 || b.length!==1 || tables.length!==3) return false;
      const first=a[0].querySelector('table'), last=b[0].querySelector('table');
      if(tables[0]!==first || tables[2]!==last) return false;
      const table=tables[1], owner=table.closest('p-table');
      const group=a[0].closest('p-panel'), parent=a[0].closest('form');
      if(!owner || !group || !parent || parent.parentElement!==form ||
         b[0].closest('form')!==parent || table.closest('form')!==parent ||
         table.closest('rshshr-citr-l3-form')!==form ||
         table.closest('p-panel')!==group || owner.parentElement!==a[0].parentElement ||
         owner.getAttribute('responsivelayout')!=='scroll' ||
         table.closest('ui-grid,ui-grid-offline,p-dialog') ||
         table.parentElement.closest('table') || !table.getClientRects().length)
        return false;
      const wrapper=table.closest('.p-datatable');
      if(!wrapper || wrapper.closest('p-table')!==owner ||
         !['scaled-datatable','p-datatable-sm','p-datatable-gridlines',
           'p-datatable-striped','p-datatable-responsiveness'].every(c=>wrapper.classList.contains(c)) ||
         owner.querySelectorAll('table').length!==1 || table.querySelectorAll('tbody tr,tfoot tr').length)
        return false;
      const rows=[...table.querySelectorAll(':scope > thead > tr')];
      const names=['RefundDeductionCreditOverseas','TotalIncomeTaxPaidOverseas'];
      if(rows.length!==2 || table.querySelectorAll('thead').length!==1 ||
         table.querySelectorAll('p-inputnumber').length!==2 ||
         table.querySelectorAll('input').length!==2) return false;
      const texts=rows.map(row=>{
        const cells=[...row.children];
        return cells.length===2 && cells[0].localName==='th'
          ? (cells[0].textContent||'').replace(/\\s+/g,' ').trim() : null;
      });
      const captions=caption_sets.find(set=>set.length===texts.length &&
        set.every((text,index)=>text===texts[index]));
      if(!captions) return false;
      return rows.every((row,i)=>{
        const cells=[...row.children];
        if(cells.length!==2 || cells.some(c=>c.localName!=='th') ||
           cells[0].colSpan!==10 || cells[1].colSpan!==1 ||
           cells.some(c=>c.rowSpan!==1) || cells[0].getAttribute('width')!=='1099' ||
           cells[1].getAttribute('width')!=='116' || cells[0].children.length ||
           (cells[0].textContent||'').replace(/\\s+/g,' ').trim()!==captions[i]) return false;
        const controls=cells[1].querySelectorAll(':scope > p-inputnumber');
        if(controls.length!==1 || cells[1].children.length!==1 ||
           controls[0].getAttribute('formcontrolname')!==names[i]) return false;
        const inputs=controls[0].querySelectorAll('input');
        return inputs.length===1 && inputs[0].getAttribute('id')===names[i];
      });
    }''', [list(pair) for pair in _L3_LAYOUT_CAPTIONS], timeout=1000) is True


def _reacquire_reference_observations(page, capture, urls, check_cancel):
    """Reacquire allowlisted reference catalogs the SPA served from cache.

    A later return in the same job observes no fresh reference GETs (the SPA
    caches the catalogs). Reacquire only the missing allowlisted ones with a
    bounded, cache-busting, same-origin GET on the DETAIL page. An
    AbortController cancels the outstanding fetches on timeout so a late
    response is never captured, and the body is read before the timer clears
    so the completion (not just the header response) is bounded. Only
    successful captured responses count, so a failure, timeout or cancellation
    leaves the catalog absent and the caller refuses. Cancellation is
    preserved; the provider/locale/route/lifetime proof is unchanged. The
    deadline is the module-owned _REFERENCE_REACQUIRE_TIMEOUT_MS.
    """
    from coretax_browser import _check_cancel
    def _observed(items, url):
        return any(item['url'] == url and item['method'] == 'GET'
                   and item.get('request_json') is None and item.get('status') in (None, 200)
                   for item in items)
    observations = capture.request_observations()
    missing = [url for url in dict.fromkeys(urls) if not _observed(observations, url)]
    if not missing:
        return observations
    _check_cancel(check_cancel)
    page.evaluate(
        '''([urls, timeoutMs]) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs);
            return Promise.all(urls.map(u =>
                fetch(u, {cache: 'reload', credentials: 'include',
                          signal: controller.signal})
                    .then(r => (r.ok ? r.text() : null))
                    .catch(() => null)))
              .then(() => clearTimeout(timer));
        }''',
        [missing, _REFERENCE_REACQUIRE_TIMEOUT_MS])
    _check_cancel(check_cancel)
    return capture.request_observations()


def _observe_l3(page, form, capture, digest, record, max_pages, check_cancel, *, reason_out=None):
    """Inspect source providers/structure and turn only the owned B paginator."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import L3_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE
    from coretax_json import CORPORATE_L3_REFERENCE_URLS, CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    def refuse(reason):
        # Fixed local reasons only; never record observed request/DOM values.
        if reason_out is not None:
            reason_out['reason'] = reason
        return None

    if digest != L3_BUILD_DIGESTS.get(CIT_SOURCE_URL):
        return refuse('cit_digest')
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return refuse('lifetime_start')
    _check_cancel(check_cancel)
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        return refuse('script_providers')
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if main_digest != L3_BUILD_DIGESTS.get(MAIN_SOURCE):
        return refuse('main_digest')
    if vendor_digest != L3_BUILD_DIGESTS.get(VENDOR_SOURCE):
        return refuse('vendor_digest')
    count = form.locator('table').count()
    standalone = count == 3 and _l3_standalone_layout(form)
    _check_cancel(check_cancel)
    if count != 2 and not standalone:
        if reason_out is not None:
            reason_out['table_shape'] = (
                'zero' if count == 0 else 'one' if count == 1 else 'more_than_two')
            if count > 2:
                _check_cancel(check_cancel)
                reason_out['extra_layout'] = _l3_extra_table_layout(form)
                _check_cancel(check_cancel)
                if reason_out['extra_layout'] == 'reviewed_pair_visible_extra':
                    reason_out['extra_owner'] = _l3_visible_extra_owner(form)
                    _check_cancel(check_cancel)
        return refuse('table_count')
    tables = []
    for phase in range(2):
        if (form.count() != 1 or not form.is_visible() or form.locator('table').count() != count
                or standalone and not _l3_standalone_layout(form)):
            return refuse('form_shape')
        _check_cancel(check_cancel)
        observed_tables = []
        for index, selector in enumerate(('rsh-citr-l3-grid1', 'rshshr-citr-l3-grid2')):
            _check_cancel(check_cancel)
            grid, ui = form.locator(selector), 'ui-grid-offline' if index == 0 else 'ui-grid'
            other = 'ui-grid' if index == 0 else 'ui-grid-offline'
            if (grid.count() != 1 or not grid.is_visible() or grid.locator(ui).count() != 1
                    or grid.locator(other).count() or grid.locator('p-table').count() != 1
                    or grid.locator('table').count() != 1):
                return refuse('grid_shape')
            table = grid.locator('table')
            chain = table.evaluate('''(table, {selector, ui}) => {
                const form=table.closest('rshshr-citr-l3-form'), grid=table.closest(selector);
                const owner=table.closest('p-table'), wrapper=table.closest(ui);
                return !!form && !!grid && grid.closest('rshshr-citr-l3-form')===form &&
                    !!owner && !!wrapper && grid.contains(wrapper) && wrapper.contains(owner) &&
                    owner.closest(ui)===wrapper && owner.closest(selector)===grid &&
                    wrapper.closest(selector)===grid && wrapper.closest('rshshr-citr-l3-form')===form;
            }''', {'selector': selector, 'ui': ui})
            _check_cancel(check_cancel)
            if chain is not True:
                return refuse('grid_ownership')
            structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L3')
            if structure != {'form': 'L3', 'component': selector, 'groups': [
                    'A. PENGHASILAN DARI LUAR NEGERI' if index == 0 else 'B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN']}:
                return refuse('table_structure')
            metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
            _check_cancel(check_cancel)
            observed_tables.append({'component': selector, 'source_structure': structure,
                           'headers': metadata['headers'], 'footer_spans': metadata['footer_spans']})
            if phase == 0 and index == 1 and not _turn_grid(page, grid.locator('p-table'), max_pages, check_cancel):
                return refuse('paginator')
        if phase == 0:
            tables = observed_tables
        elif observed_tables != tables:
            return refuse('stable_table_metadata')
    requests, seen, footer = [], set(), False
    observations = capture.request_observations()
    for item in observations:
        if item['method'] != 'POST' or item['url'] not in (CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL):
            continue
        request = item.get('request_json')
        if not isinstance(request, dict) or 'ReturnSheetRecordId' not in request:
            return refuse('request_shape')
        if request['ReturnSheetRecordId'] != record['record_id']:
            raise JsonSafetyError('Observed L3 request contradicts selected return')
        if item['url'] == CORPORATE_L3_FOOTER_URL:
            if request != {'ReturnSheetRecordId': record['record_id']}:
                return refuse('footer_request')
            footer = True
            continue
        if type(request.get('First')) is not int or request['First'] < 0:
            return refuse('grid_offset')
        key = json.dumps(request, sort_keys=True)
        if key not in seen:
            requests.append(request)
            seen.add(key)
    if not requests or not footer:
        return refuse('grid_or_footer_missing')
    references = []
    observations = _reacquire_reference_observations(
        page, capture, list(CORPORATE_L3_REFERENCE_URLS.values()), check_cancel)
    for url in CORPORATE_L3_REFERENCE_URLS.values():
        sequences = [item['sequence'] for item in observations
            if item['url'] == url and item['method'] == 'GET' and item.get('request_json') is None
            and item.get('status') in (None, 200)]
        if not sequences:
            return refuse('reference_request')
        references.append({'endpoint': url, 'method': 'GET', 'sequences': sequences})
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return refuse('lifetime_end')
    return {'responses': [{'name': 'L3/domestic', 'endpoint': CORPORATE_L3_GRID_URL,
                          'requests': sorted(requests, key=lambda request: request['First'])}],
        'dependencies': [{'endpoint': CORPORATE_L3_FOOTER_URL,
                          'request_json': {'ReturnSheetRecordId': record['record_id']}}],
        'projection': {'kind': 'corporate-l3-v1', 'builds': {CIT_SOURCE_URL: digest,
            MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest}, 'route': page.url,
              **environment, 'tables': tables, 'references': references,
              **({'standalone_layout': 'overseas-controls-v1'} if standalone else {})}}


def corporate_reference_bindings(capture, kinds, *, check_cancel=None):
    """Collect only original admitted singleton metadata and capture-owned pins."""
    from coretax_browser import _check_cancel
    from coretax_json import CORPORATE_REFERENCE_REQUESTS

    _check_cancel(check_cancel)
    urls = {types[0]: url for url, types in CORPORATE_REFERENCE_REQUESTS.items() if len(types) == 1}
    if (not isinstance(kinds, (tuple, list)) or not kinds or len(set(kinds)) != len(kinds)
            or any(kind not in urls for kind in kinds)):
        return None
    builds = capture.observe_corporate_reference_providers(check_cancel=check_cancel)
    if builds is None:
        return None
    observations = capture.request_observations()
    _check_cancel(check_cancel)
    references = []
    for kind in kinds:
        sequences = [item['sequence'] for item in observations
            if item['url'] == urls[kind] and item['method'] == 'GET'
            and 'request_json' in item and item['request_json'] is None]
        if not sequences:
            return None
        references.append({'endpoint': urls[kind], 'method': 'GET', 'sequences': sequences})
    return {'builds': builds, 'references': references}


def _observe_l11a(page, form, capture, digest, record, max_pages, check_cancel, *, reason_out=None):
    """Five structural owners and four owned paginators; no DOM business reads."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import (L11A_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE,
                                             _L11A_OWNERS, _L11A_GROUPS)
    from coretax_json import (CORPORATE_L11A_GRID_URLS, CORPORATE_L11A_REFERENCE_URLS,
                              CORPORATE_REFERENCE_REQUESTS)
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    def refuse(reason):
        if reason_out is not None:
            reason_out['reason'] = reason
        return None

    if digest != L11A_BUILD_DIGESTS.get(CIT_SOURCE_URL):
        return refuse('cit_digest')
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return refuse('lifetime_start')
    _check_cancel(check_cancel)
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        [CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE])
    _check_cancel(check_cancel)
    if providers is not True:
        return refuse('script_providers')
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if main_digest != L11A_BUILD_DIGESTS.get(MAIN_SOURCE):
        return refuse('main_digest')
    if vendor_digest != L11A_BUILD_DIGESTS.get(VENDOR_SOURCE):
        return refuse('vendor_digest')
    tables = []
    for phase in range(2):
        if form.count() != 1 or not form.is_visible() or form.locator('table').count() != 5:
            return refuse('table_count')
        observed_tables = []
        for index, selector in enumerate(_L11A_OWNERS):
            _check_cancel(check_cancel)
            grid, ui = form.locator(selector), 'ui-grid-offline' if index == 3 else 'ui-grid'
            other = 'ui-grid' if index == 3 else 'ui-grid-offline'
            if (grid.count() != 1 or not grid.is_visible() or grid.locator(ui).count() != 1
                    or grid.locator(other).count() or grid.locator('p-table').count() != 1
                    or grid.locator('table').count() != 1):
                return refuse('grid_ownership')
            table = grid.locator('table')
            chain = table.evaluate('''(table, {selector, ui}) => {
                const form=table.closest('rshshr-citr-l11a-form'), grid=table.closest(selector);
                const owner=table.closest('p-table'), wrapper=table.closest(ui);
                return !!form && !!grid && grid.closest('rshshr-citr-l11a-form')===form &&
                    !!owner && !!wrapper && grid.contains(wrapper) && wrapper.contains(owner) &&
                    owner.closest(ui)===wrapper && owner.closest(selector)===grid &&
                    wrapper.closest(selector)===grid && wrapper.closest('rshshr-citr-l11a-form')===form;
            }''', {'selector': selector, 'ui': ui})
            _check_cancel(check_cancel)
            if chain is not True:
                return refuse('grid_ownership')
            structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L11-A')
            if structure != {'form': 'L11-A', 'component': selector, 'groups': _L11A_GROUPS[index]}:
                return refuse('table_structure')
            metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
            _check_cancel(check_cancel)
            observed_tables.append({'component': selector, 'source_structure': structure,
                'headers': metadata['headers'], 'footer_spans': metadata['footer_spans']})
        if phase == 0:
            tables = observed_tables
            for index, selector in enumerate(_L11A_OWNERS):
                if index != 3 and not _turn_grid(page, form.locator(selector + ' p-table'), max_pages, check_cancel):
                    return refuse('paginator')
        elif observed_tables != tables:
            return refuse('stable_table_metadata')
    observations = capture.request_observations()
    responses = []
    for url in CORPORATE_L11A_GRID_URLS:
        requests, seen = [], set()
        for item in observations:
            if item['url'] != url or item['method'] != 'POST':
                continue
            request = item.get('request_json')
            if not isinstance(request, dict) or 'ReturnSheetRecordId' not in request:
                return refuse('request_shape')
            if request['ReturnSheetRecordId'] != record['record_id']:
                raise JsonSafetyError('Observed L11-A request contradicts selected return')
            if type(request.get('First')) is not int or request['First'] < 0:
                return refuse('grid_offset')
            key = json.dumps(request, sort_keys=True)
            if key not in seen:
                requests.append(request)
                seen.add(key)
        if not requests:
            return refuse('grid_request_missing')
        responses.append({'name': 'L11-A/' + url.rsplit('/', 1)[-1], 'endpoint': url,
                          'requests': sorted(requests, key=lambda request: request['First'])})
    references, kinds_seen = [], set()
    for url, kinds in CORPORATE_REFERENCE_REQUESTS.items():
        if any(kind not in CORPORATE_L11A_REFERENCE_URLS for kind in kinds):
            continue
        sequences = [item['sequence'] for item in observations
            if item['url'] == url and item['method'] == 'GET' and item.get('request_json') is None]
        if sequences:
            kinds_seen.update(kinds)
            references.append({'endpoint': url, 'method': 'GET', 'sequences': sequences})
    if kinds_seen != set(CORPORATE_L11A_REFERENCE_URLS):
        return refuse('reference_request_missing')
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return refuse('lifetime_end')
    return {'responses': responses,
        'projection': {'kind': 'corporate-l11a-v1', 'builds': {CIT_SOURCE_URL: digest,
            MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest}, 'route': page.url,
            **environment, 'tables': tables, 'references': references}}


def _l4_tables(form):
    """Bind both rendered L4 owners without reading body/footer values."""
    from coretax_corporate_projection import l4_tables
    from coretax_masa_observer import TABLE
    expected = l4_tables()
    if form.locator('table').count() != 2:
        return None
    result = []
    for item, host in zip(expected, ('ui-grid', 'ui-grid-offline')):
        grid = form.locator(item['component'])
        if (grid.count() != 1 or grid.locator(host).count() != 1
                or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1):
            return None
        table = grid.locator('table')
        if not table.evaluate('''(e, {component, host}) => {
            const grid=e.closest(component), wrapper=e.closest(host), p=e.closest('p-table');
            return e.isConnected && !!grid && !!wrapper && !!p &&
                p.closest(host)===wrapper && wrapper.closest(component)===grid &&
                e.closest('rshshr-citr-l4-form')===grid.closest('rshshr-citr-l4-form');
        }''', {'component': item['component'], 'host': host}):
            return None
        metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
        if (not isinstance(metadata, dict) or metadata.get('headers') != item['headers']
                or metadata.get('footer_spans') != item['footer_spans']):
            return None
        result.append({'component': item['component'], 'headers': metadata['headers'],
                       'footer_spans': metadata['footer_spans']})
    return result


def _l4_populated_projection(page, capture, digest, tables, check_cancel):
    """Optional stronger consumer; shared passive registry alone owns admission."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import (L4_CATALOG_KINDS, L4_POPULATED_BUILD_DIGESTS,
                                              MAIN_SOURCE, VENDOR_SOURCE)
    from coretax_json import CORPORATE_L4_REFERENCE_URLS
    urls = {CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE}
    pins = L4_POPULATED_BUILD_DIGESTS
    if (set(pins) != urls or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                              for value in pins.values()) or pins[CIT_SOURCE_URL] != digest):
        return None
    if not callable(getattr(capture, 'observe_corporate_reference_providers', None)):
        return None
    observations = capture.request_observations()
    if not all(any(item['url'] == url and item['method'] == 'GET'
                   and 'request_json' in item and item['request_json'] is None for item in observations)
               for url in CORPORATE_L4_REFERENCE_URLS.values()):
        return None  # No optional provider RPC for a cache-only/legacy visit.
    shared = corporate_reference_bindings(capture, L4_CATALOG_KINDS, check_cancel=check_cancel)
    _check_cancel(check_cancel)
    if shared is None or shared['builds'] != pins:
        return None
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}:
        return None
    # The enabled Induk-owned form is the authoritative selector owner; an
    # absent outer flag is proven by that binding, never by an outer copy.
    return {'kind': 'corporate-l4-populated-v2', 'builds': dict(shared['builds']), 'route': page.url,
            **environment, 'tables': tables, 'references': shared['references'],
            'visibility_binding': 'current-induk-enabled-v1'}

_L10A_STRUCTURE = r'''form => {
 const fs='rshshr-citr-l10a-form', gs='rshshr-citr-l10a-form-grid1';
 const panel=form.closest('.p-tabview-panel');
 if(!panel || panel.querySelectorAll(fs).length!==1 || !form.isConnected)return false;
 for(const name of ['PeriodYear','CollectorTin']){
   const inputs=form.querySelectorAll('input[formcontrolname="'+name+'"]');
   if(inputs.length!==1||inputs[0].getAttribute('type')!=='text'||
      inputs[0].closest(fs)!==form||inputs[0].closest(gs)||!inputs[0].closest('form'))return false;
 }
 const one=(root,selector)=>{const all=root.querySelectorAll(selector);return all.length===1?all[0]:null};
 const grid=one(form,gs), ui=grid&&one(grid,'ui-grid'), pt=ui&&one(ui,'p-table'), table=pt&&one(pt,'table');
 if(!grid||!ui||!pt||!table||form.querySelectorAll('table').length!==1||
    grid.closest(fs)!==form||ui.closest(gs)!==grid||pt.closest('ui-grid')!==ui||
    table.closest('p-table')!==pt||table.closest(fs)!==form)return false;
 for(let n=table.parentElement;n&&n!==form;n=n.parentElement)
   if(n.localName.endsWith('-form'))return false;
 return true;
}'''


def _l10a_table(form, tab):
    from coretax_masa_observer import TABLE
    if not _enabled_form_binding(form, tab, 'L10-A') or form.evaluate(_L10A_STRUCTURE) is not True:
        return None
    metadata = form.locator('rshshr-citr-l10a-form-grid1 table').evaluate(TABLE.replace('GROUP', '()=>""'))
    from coretax_corporate_projection import L10A_HEADERS
    if metadata['headers'] != L10A_HEADERS or metadata['footer_spans'] != []:
        return None
    return {'component': 'rshshr-citr-l10a-form-grid1', 'headers': metadata['headers'],
        'footer_spans': [], 'source_structure': {'form': 'L10-A', 'owner_chain': [
            'rshshr-citr-l10a-form', 'rshshr-citr-l10a-form-grid1', 'ui-grid', 'p-table', 'table'],
            'header_controls': ['PeriodYear', 'CollectorTin']}}


def _observe_l10a_populated(page, form, tab, capture, before, check_cancel):
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import L10A_LABELS, L10A_BUILD_DIGESTS
    _check_cancel(check_cancel)
    if before is None or not callable(getattr(capture, 'observe_corporate_reference_providers', None)):
        return None
    references = corporate_reference_bindings(capture, tuple(L10A_LABELS.values()), check_cancel=check_cancel)
    if references is None or references['builds'] != L10A_BUILD_DIGESTS:
        return None
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    after = _l10a_table(form, tab)
    _check_cancel(check_cancel)
    if (before != after or environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
            or capture.observe_component_lifetime(check_cancel=check_cancel) is None):
        return None
    return {'kind': 'corporate-l10a-populated-v1', **references, 'route': page.url,
            **environment, 'tables': [after],
            'visibility_binding': 'current-induk-enabled-v1'}


def _l4_footer_requests(observations, *, record_id, period):
    """Collect distinct proven L4 footer requests (None when absent).

    A caller reports unknown shapes as unavailable (None); identity or year
    contradictions are fatal, mirroring the grid page checks they track.
    """
    footer_url = ORIGIN + '/returnsheet/api/loadcit/l4-table-a-grid/footer'
    found, seen = [], set()
    for event in observations:
        if event['url'] != footer_url or event['method'] != 'POST':
            continue
        request = event['request_json']
        if not isinstance(request, dict) or 'ReturnSheetRecordId' not in request:
            return None
        if request['ReturnSheetRecordId'] != record_id:
            raise JsonSafetyError('Observed footer belongs to a different selected return')
        if not set(request) <= {'ReturnSheetRecordId', 'PeriodYear'}:
            return None
        if 'PeriodYear' in request:
            if period is None:
                return None
            if request['PeriodYear'] != period[-4:]:
                raise JsonSafetyError('Observed footer year contradicts selected period')
        key = json.dumps(request, sort_keys=True)
        if key not in seen:
            seen.add(key)
            found.append(request)
    return found or None


def _l9_tables(form, check_cancel):
    """Read only the exact twelve owners, captions, headers and footer spans."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import l9_grid_structure, L9_GRID_HEADERS, L9_GRID_SPANS
    from coretax_masa_observer import TABLE
    if form.locator('table').count() != 12:
        return None
    tables = []
    for selector, _, groups in GRID_ROLES['L9']:
        grids = form.locator(selector)
        if grids.count() != len(groups):
            return None
        for index in range(len(groups)):
            _check_cancel(check_cancel)
            grid = grids.nth(index)
            if (not grid.is_visible() or grid.locator('ui-grid').count() != 1
                    or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1):
                return None
            table = grid.locator('table')
            chain = table.evaluate('''(table, selector) => {
                const form=table.closest('rshshr-citr-l9-form'), grid=table.closest(selector);
                const ui=table.closest('ui-grid'), owner=table.closest('p-table');
                return !!form && !!grid && !!ui && !!owner &&
                    grid.closest('rshshr-citr-l9-form')===form &&
                    ui.closest(selector)===grid && ui.closest('rshshr-citr-l9-form')===form &&
                    owner.closest('ui-grid')===ui && ui.contains(owner) && grid.contains(owner);
            }''', selector)
            _check_cancel(check_cancel)
            if chain is not True:
                return None
            structure = table.evaluate(CORPORATE_STRUCTURE_JS, 'L9')
            expected = l9_grid_structure(len(tables))
            alternatives = [expected]
            if len(tables) in (4, 11):
                alternatives.append({**expected, 'groups': [expected['groups'][0], 'LAINNYA']})
            if structure not in alternatives:
                return None
            metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
            _check_cancel(check_cancel)
            if metadata['headers'] != L9_GRID_HEADERS or metadata['footer_spans'] != L9_GRID_SPANS:
                return None
            tables.append({'component': selector, 'source_structure': structure,
                'headers': metadata['headers'], 'footer_spans': metadata['footer_spans']})
    return tables


def _observe_l9(page, form, capture, digest, check_cancel):
    """Additive details proof; no transport registration or active catalog call."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import L9_DETAIL_BUILD_DIGESTS, L9_REFERENCE_KINDS, MAIN_SOURCE, VENDOR_SOURCE
    from coretax_json import CORPORATE_REFERENCE_REQUESTS
    from coretax_masa_observer import _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    from spt_desktop import diagnostics

    def _refuse(gate):
        # Fixed-enum diagnostic: name the exact predicate that dropped the
        # details proof so a live run can be diagnosed without payloads.
        diagnostics.record('corporate.l9_detail_gate', corporate_l9_detail_gate=gate)
        return None

    _check_cancel(check_cancel)
    # Missing shared producer support keeps the old recap-only fallback without
    # fetching a catalog, probing browser cache, or granting a new request class.
    admitted = {kinds[0] for kinds in CORPORATE_REFERENCE_REQUESTS.values() if len(kinds) == 1}
    if not set(L9_REFERENCE_KINDS) <= admitted:
        return _refuse('reference_kinds_not_admitted')
    pins = L9_DETAIL_BUILD_DIGESTS
    if (set(pins) != {CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value) for value in pins.values())
            or pins[CIT_SOURCE_URL] != digest):
        return _refuse('build_pins')
    references, observed_kinds = [], set()
    l9_urls = [endpoint for endpoint, kinds in CORPORATE_REFERENCE_REQUESTS.items()
               if len(kinds) == 1 and kinds[0] in L9_REFERENCE_KINDS]
    observations = _reacquire_reference_observations(page, capture, l9_urls, check_cancel)
    for endpoint, kinds in CORPORATE_REFERENCE_REQUESTS.items():
        if len(kinds) != 1 or kinds[0] not in L9_REFERENCE_KINDS:
            continue
        sequences = [event['sequence'] for event in observations
            if event['url'] == endpoint and event['method'] == 'GET' and event['request_json'] is None
            and event.get('status') in (None, 200)]
        if not sequences:
            continue
        if kinds[0] in observed_kinds:
            return _refuse('duplicate_reference_kind')
        observed_kinds.add(kinds[0])
        references.append({'endpoint': endpoint, 'method': 'GET', 'sequences': sequences})
    if observed_kinds != set(L9_REFERENCE_KINDS):
        return _refuse('reference_kinds_incomplete')
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return _refuse('component_lifetime')
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src===url) ||
        performance.getEntriesByType('resource').some(e => e.name===url))''', list(pins))
    _check_cancel(check_cancel)
    if providers is not True:
        return _refuse('providers')
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if main_digest != pins[MAIN_SOURCE] or vendor_digest != pins[VENDOR_SOURCE]:
        return _refuse('provider_digests')
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}:
        return _refuse('environment')
    tables = _l9_tables(form, check_cancel)
    if tables is None:
        return _refuse('tables')
    return {'kind': 'corporate-l9-details-v1', 'builds': dict(pins), 'route': page.url,
            **environment, 'tables': tables, 'references': references}


def _observe_induk_submitted(page, form, capture, digest, check_cancel):
    """Optional amount capability: source/provider/structure only, never values."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import (INDUK_SUBMITTED_BUILD_DIGESTS,
        INDUK_SUBMITTED_FIELDS, INDUK_INACTIVE_FIELDS, INDUK_INACTIVE_SELECTORS,
        MAIN_SOURCE, VENDOR_SOURCE)
    from coretax_masa_observer import _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    _check_cancel(check_cancel)
    lifetime = getattr(capture, 'observe_component_lifetime', None)
    pins = INDUK_SUBMITTED_BUILD_DIGESTS
    urls = (CIT_SOURCE_URL, MAIN_SOURCE, VENDOR_SOURCE)
    if (not callable(lifetime) or set(pins) != set(urls)
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for value in pins.values()) or digest != pins[CIT_SOURCE_URL]):
        return None
    controls = [name for _, name, _ in INDUK_SUBMITTED_FIELDS]
    structure = form.evaluate('''(form, controls) => {
        // induk-submitted-controls: read bindings/visibility only, never input values.
        if(form.localName!=='rshshr-citr-main-form'||!form.isConnected)return false;
        const bound=controls.every(name=>{
            const nodes=[...form.querySelectorAll('p-inputnumber')].filter(e=>
                e.getAttribute('formcontrolname')===name);
            if(nodes.length!==1||nodes[0].id!==name||
                nodes[0].closest('rshshr-citr-main-form')!==form||
                nodes[0].getAttribute('mode')!=='decimal'||!nodes[0].getClientRects().length)return false;
            const inputs=nodes[0].querySelectorAll('input');
            return inputs.length===1&&inputs[0].disabled===true&&
                (name!=='TotalApprovalInstallment'||inputs[0].readOnly===true);
        });
        const radios=[...form.querySelectorAll('p-radiobutton')].filter(e=>
            e.getAttribute('formcontrolname')==='IsApprovalInstallment');
        return bound&&radios.length===2&&radios.every(e=>{
            const inputs=e.querySelectorAll('input[type=radio]');
            return e.closest('rshshr-citr-main-form')===form&&inputs.length===1&&inputs[0].disabled===true;
        });
    }''', controls)
    _check_cancel(check_cancel)
    if structure is not True or lifetime(check_cancel=check_cancel) is None:
        return None
    providers = page.evaluate('''urls => urls.every(url =>
        [...document.scripts].some(s => s.src === url) ||
        performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
        list(urls))
    _check_cancel(check_cancel)
    if providers is not True:
        return None
    main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
    _check_cancel(check_cancel)
    vendor_digest = page.evaluate(_REFERENCE_ORDER_BUILD_HASH, VENDOR_SOURCE)
    _check_cancel(check_cancel)
    if main_digest != pins[MAIN_SOURCE] or vendor_digest != pins[VENDOR_SOURCE]:
        return None
    environment = page.evaluate('''() => ({locale:navigator.language,
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})''')
    _check_cancel(check_cancel)
    if (environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
            or lifetime(check_cancel=check_cancel) is None):
        return None
    proof = {'kind': 'corporate-induk-submitted-v2', 'builds': dict(pins),
             'route': page.url, **environment, 'controls': controls}
    # Additional v3 permission is optional. Observe disabled ownership, never
    # business input values; missing/enabled controls retain the v2 boundary.
    extra = form.evaluate('''(form, expected) => {
        const {selectors, amounts} = expected;
        const bound=amounts.every(name=>{
            const nodes=[...form.querySelectorAll('p-inputnumber')].filter(e=>
                e.getAttribute('formcontrolname')===name);
            if(nodes.length!==1||nodes[0].id!==name||
               nodes[0].closest('rshshr-citr-main-form')!==form||
               nodes[0].getAttribute('mode')!=='decimal'||!nodes[0].getClientRects().length)return false;
            const inputs=nodes[0].querySelectorAll('input');
            return inputs.length===1&&inputs[0].disabled===true;
        });
        return bound&&selectors.every(name=>{
            const radios=[...form.querySelectorAll('p-radiobutton')].filter(e=>
                e.getAttribute('formcontrolname')===name);
            return radios.length===2&&radios.every(e=>{
                const inputs=e.querySelectorAll('input[type=radio]');
                return e.closest('rshshr-citr-main-form')===form&&
                    inputs.length===1&&inputs[0].disabled===true;
            });
        });
    }''', {'selectors': list(INDUK_INACTIVE_SELECTORS),
           'amounts': [name for _, name, _ in INDUK_INACTIVE_FIELDS]})
    _check_cancel(check_cancel)
    if extra is True and lifetime(check_cancel=check_cancel) is not None:
        proof['kind'] = 'corporate-induk-submitted-v3'
        proof['controls'] = controls + [name for _, name, _ in INDUK_INACTIVE_FIELDS]
    return proof
def _observe_l10b(page, form, tab, panel, capture, check_cancel):
    """No display controls: prove the original enabled source owner instead."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import (CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE,
                                              L10B_KIND, _l10b_pins)
    from coretax_masa_observer import _REFERENCE_ORDER_BUILD_HASH
    if any(not callable(getattr(capture, name, None)) for name in
           ('observe_component_lifetime', 'bind_l10b_structure', 'observe_l10b_lifetime')):
        return None
    _check_cancel(check_cancel)
    if (capture.observe_component_lifetime(check_cancel=check_cancel) is None
            or not _enabled_form_binding(form, tab, 'L10-B')
            or not capture.bind_l10b_structure(form, tab, panel, phase='start', check_cancel=check_cancel)):
        return None
    route, builds = page.url, {}
    for url in (CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE):
        builds[url] = page.evaluate(_REFERENCE_ORDER_BUILD_HASH.replace('4*1024*1024', '5*1024*1024'), url)
        _check_cancel(check_cancel)
    if not _l10b_pins(builds):
        return None
    if (page.url != route or not _enabled_form_binding(form, tab, 'L10-B')
            or not capture.bind_l10b_structure(form, tab, panel, phase='end', check_cancel=check_cancel)
            or capture.observe_l10b_lifetime(check_cancel=check_cancel) is None):
        return None
    _check_cancel(check_cancel)
    # The independently rechecked enabled L10-B owner is the selector authority;
    # an absent outer flag is proven by that binding, never by an outer copy.
    return {'kind': L10B_KIND, 'builds': builds, 'route': route,
            'visibility_binding': 'current-induk-enabled-v1'}
def _observe_l10d_originals(page, form, tab, capture, digest, check_cancel, *, panel=None):
    """Optional current-owner offer, expressly not a final-selection capability."""
    from coretax_browser import _check_cancel
    from coretax_corporate_l10d import PROVIDERS, KIND, approved_builds
    from coretax_masa_observer import _REFERENCE_ORDER_BUILD_HASH
    pins = load_build_pins()
    expected = {url: pins.get(url) for url in PROVIDERS}
    if (not approved_builds(expected) or digest != expected[CIT_SOURCE_URL]
            or not callable(getattr(capture, 'observe_component_lifetime', None))):
        return None
    _check_cancel(check_cancel)
    if (not _enabled_form_binding(form, tab, 'L10-D')
            or capture.observe_component_lifetime(check_cancel=check_cancel) is None):
        return None
    bind_history = getattr(capture, 'bind_l10d_structure', None)
    history_started = panel is not None and callable(bind_history) and bind_history(
        form, tab, panel, phase='start', check_cancel=check_cancel)
    builds = {}
    for url in PROVIDERS:
        # MAIN exceeds 4 MiB. Keep its existing reviewed 5 MiB reader bound,
        # while retaining script-provider and hash checks in the same RPC.
        script = (_REFERENCE_ORDER_BUILD_HASH.replace('4*1024*1024', '5*1024*1024')
                  if url == PROVIDERS[1] else _REFERENCE_ORDER_BUILD_HASH)
        builds[url] = page.evaluate(script, url)
        _check_cancel(check_cancel)
    if not approved_builds(builds):
        return None
    enabled = _enabled_form_binding(form, tab, 'L10-D')
    _check_cancel(check_cancel)
    lifetime = capture.observe_component_lifetime(check_cancel=check_cancel)
    _check_cancel(check_cancel)
    if not enabled or lifetime is None:
        return None
    if history_started:
        bind_history(form, tab, panel, phase='end', check_cancel=check_cancel)
    # The enabled L10-D owner was rechecked twice above; an absent outer flag is
    # therefore proven by that binding, never by an outer copy.
    return {'kind': KIND, 'builds': builds, 'route': page.url,
            'owner_binding': 'observed-enabled-after-induk-v1',
            'visibility_binding': 'current-induk-enabled-v1'}


def observe_forms(page, record, scope, capture, *, approved_digest, max_pages=1000, check_cancel=None):
    from coretax_browser import _check_cancel, verify_detail_url, list_taxpayer_id, CaptureCancelled
    from coretax_json import _check_corporate_route, _corporate_selected
    from spt_desktop import diagnostics
    stage = 'build'
    ordinal_safe = None
    # Privacy-safe per-stage timings for the observe-performance follow-up.
    # Records stage name, form ordinal, and duration only — never values,
    # URLs, digests, or page state. Emitted exactly once on success or
    # refusal so even a slow failing stage keeps its measured time.
    _segments = []
    _segment_start = time.monotonic()
    _emitted = False

    def _advance(new_stage):
        nonlocal stage, _segment_start
        _segments.append((stage, (time.monotonic() - _segment_start) * 1000,
                          ordinal_safe))
        stage, _segment_start = new_stage, time.monotonic()

    def _emit_timings():
        # Exactly-once: close the running segment, then flush every measured
        # one. A refusal sees the failing stage's elapsed time; a second
        # call is a no-op so unavailable/error paths can't duplicate rows.
        nonlocal _emitted
        if _emitted:
            return
        _segments.append((stage, (time.monotonic() - _segment_start) * 1000,
                          ordinal_safe))
        _emitted = True
        for seg_stage, duration_ms, seg_ordinal in _segments:
            fields = {'corporate_observer_stage': seg_stage,
                      'duration_ms': duration_ms}
            if seg_ordinal is not None:
                fields['form_ordinal'] = seg_ordinal
            diagnostics.record('corporate.observe_timing', **fields)

    def unavailable(error=None, *, reason=None, l3_reason=None, l3_table_shape=None,
                    l3_extra_layout=None, l3_extra_owner=None, l11a_reason=None,
                    missing_forms=None):
        # A finite stage and an observed ordinal, never tab text, values,
        # URL, source body or exception message. Does not grant JSON admission.
        # Emit already-measured stage segments so even a late refusal keeps
        # the bounded, value-free performance trail.
        _emit_timings()
        if reason is None:
            # A bare refusal still names its stage-derived class, so no corporate
            # gate collapses into an unexplained whole-record DOM fallback.
            reason = {'build': 'build_unfamiliar', 'tabs': 'tabs_missing',
                      'tab': 'tab_unrecognized', 'panel': 'panel_unavailable',
                      'form': 'form_unavailable', 'grid': 'grid_structure',
                      'induk': 'induk_order'}.get(stage, 'observation_error')
        diagnostics.record('corporate.observe_unavailable', level='WARNING', corporate_observer_stage=stage,
                           form_ordinal=ordinal_safe, corporate_refusal_reason=reason,
                           corporate_l3_reason=l3_reason,
                           corporate_l3_table_shape=l3_table_shape,
                           corporate_l3_extra_layout=l3_extra_layout,
                           corporate_l3_extra_owner=l3_extra_owner,
                           corporate_l11a_reason=(l11a_reason or 'observation_error') if stage == 'l11a' else None,
                           corporate_missing_forms=missing_forms,
                           error=error)
        return None
    _check_cancel(check_cancel)
    verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
    selected = _corporate_selected(record, scope)
    _check_corporate_route(page.url, selected)
    try:
        digest = page.evaluate(_BUILD_HASH, CIT_SOURCE_URL)
        _check_cancel(check_cancel)
        # Both digests must be positive 64-hex SHAs; None == None must
        # never admit a build (missing pin + missing asset).
        if (not isinstance(digest, str) or not isinstance(approved_digest, str)
                or len(digest) != 64 or len(approved_digest) != 64
                or any(c not in '0123456789abcdef' for c in digest + approved_digest)
                or digest != approved_digest):
            # A redeploy is the common cause, so try to re-measure the pinned
            # assets from this authenticated page before giving up. This runs
            # when the loaded digest is missing as well as when it mismatches:
            # a renamed chunk leaves nothing to compare, and the verified
            # assets are still recorded for the next run. Admission still
            # requires the re-measured CIT asset to equal a positive 64-hex
            # digest this page loaded, and structural validation below remains
            # the real gate on the build.
            refreshed = _auto_refresh_build_pins(page, check_cancel,
                                                 expected_digest=digest)
            if refreshed is None:
                # D: the digest is a tripwire, not the gate. A build nobody
                # reviewed still reaches the structural probe below, which is
                # the real contract check; if that probe passes, the bindings
                # this run consumes are proven by observation. Name the drift
                # loudly (fixed enum only, never the digest, URL or bytes) so a
                # live run is diagnosable, and let the structure decide.
                diagnostics.record('build.contract_drift', level='WARNING',
                                   build_source='corporate')
            else:
                # Admitted on a re-measured build. Say so loudly: the reviewed
                # bundle no longer matches and only the structural checks below
                # stand between this build and the spreadsheet.
                diagnostics.record('build.auto_admitted', level='WARNING',
                                   build_source='corporate')
        _advance('tabs')
        view, tabs = _tabs(page)
        if not tabs.count():
            return unavailable(reason='tabs_missing')
        forms, names = [], set()
        for ordinal in range(tabs.count()):
            _check_cancel(check_cancel)
            _advance('tab')
            ordinal_safe = ordinal
            tab = tabs.nth(ordinal)
            if tab.evaluate('(e)=>e.closest("li").classList.contains("p-disabled")||e.getAttribute("aria-disabled")==="true"'):
                # A disabled FORMS panel still binds its JSON root path: the
                # adapter admits it only when the source value is exactly
                # null/absent (inert empty form), never for stored objects.
                disabled_name = tab.inner_text().strip()
                if disabled_name not in FORMS or disabled_name in names:
                    return unavailable()
                names.add(disabled_name)
                forms.append({'name': disabled_name,
                              'paths': [[FORMS[disabled_name][1]]],
                              'disabled': True,
                              'grids': [], 'responses': [], 'dependencies': []})
                continue
            name = tab.inner_text().strip()
            if name not in FORMS or name in names:
                return unavailable()
            names.add(name)
            _advance('panel')
            panel = _native_panel(page, view, tab, name, record, check_cancel)
            if panel is None:
                return unavailable(reason='panel_unavailable')
            _check_corporate_route(page.url, selected)
            selector, root = FORMS[name]
            _advance('form')
            form = panel.locator(selector)
            if form.count() != 1 or not form.is_visible():
                return unavailable(reason='form_unavailable')
            binding = {'name':name, 'paths':[[root]], 'grids':[]}
            l10a_before = None
            if name == 'Induk':
                binding['primary'] = {'endpoint':ORIGIN+'/returnsheet/api/prefillreturnsheet/corporate-income',
                    'request_json':{'RecordId':record['record_id'], 'OnManualClick':False}}
                # ``digest`` already passed the positive 64-hex pin equality
                # above, so the proof carries exactly that admitted digest.
                # The legacy proof needs only literal text; the optional amount
                # proof below owns its separate source/environment requirements.
                binding['projection'] = {'kind': 'corporate-induk-v1',
                    'builds': {CIT_SOURCE_URL: digest}, 'route': page.url}
                submitted = _observe_induk_submitted(page, form, capture, digest, check_cancel)
                if submitted is not None:
                    binding['projection'] = submitted
            if name == 'L4':
                # Only the reconciled empty two-block subset can project until
                # both runtime catalogs have independent original-byte custody.
                tables = _l4_tables(form)
                _check_cancel(check_cancel)
                if tables is None:
                    return unavailable()
                binding['projection'] = {'kind': 'corporate-l4-v1',
                    'builds': {CIT_SOURCE_URL: digest}, 'route': page.url, 'tables': tables}

            if name == 'L10-A':
                # Preserve empty-v1 independently. Upgrade only after exact
                # owned table checks and original catalog/provider custody.
                fields = record.get('source_fields', {})
                route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
                    str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                        fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
                if page.url == route:
                    binding['projection'] = {'kind': 'corporate-l10a-empty-v1',
                        'builds': {CIT_SOURCE_URL: digest}, 'route': page.url}
                    if ('Induk' in names and fields.get('TaxTypeCode') == 'ICT_RCIT'
                            and callable(getattr(capture, 'observe_corporate_reference_providers', None))):
                        l10a_before = _l10a_table(form, tab)
                        _check_cancel(check_cancel)


            if name == 'L6':
                # Same admitted pin; the sheet is a literal scalar form with no
                # grid, paginator or reference request of its own.
                binding['projection'] = {'kind': 'corporate-l6-v1',
                    'builds': {CIT_SOURCE_URL: digest}, 'route': page.url}
            if name == 'L2':
                projection = (_observe_l2(page, form, tab, capture, digest, check_cancel)
                              if 'Induk' in names else None)
                # A failed stronger proof never grants new permission. The old
                # v1 whole-owner quarantine still refuses populated bodies.
                binding['projection'] = projection or {'kind': 'corporate-l2-v1',
                    'builds': {CIT_SOURCE_URL: digest}, 'route': page.url}
            if name == 'L9':
                # Observer-approved bytes are not automatically a reviewed
                # numerical projector build (synthetic/legacy callers differ).
                from coretax_corporate_projection import BUILD_DIGESTS
                if BUILD_DIGESTS.get(CIT_SOURCE_URL) == digest:
                    locale = page.evaluate('() => navigator.language')
                    _check_cancel(check_cancel)
                    # The reviewed projector only admits the id-ID corporate
                    # locale. Any other locale keeps L9 an unprojected dump
                    # instead of claiming a projection it cannot verify.
                    if locale == 'id-ID':
                        binding['projection'] = {'kind': 'corporate-l9-v1', 'locale': locale,
                            'builds': {CIT_SOURCE_URL: digest}, 'route': page.url}
                        if 'Induk' in names:
                            detailed = _observe_l9(page, form, capture, digest, check_cancel)
                            if detailed is not None and _enabled_form_binding(form, tab, name):
                                binding['projection'] = detailed
            if name == 'L11-B':
                from coretax_corporate_projection import BUILD_DIGESTS, MAIN_SOURCE
                from coretax_masa_observer import _PPN_MAIN_BUILD_HASH
                # The unconditional offline grid uses the reviewed main-bundle
                # Number renderer. No business values or new endpoint reads.
                main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
                _check_cancel(check_cancel)
                if (set(BUILD_DIGESTS) != {CIT_SOURCE_URL, MAIN_SOURCE}
                        or any(type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value)
                               for value in (digest, main_digest, *BUILD_DIGESTS.values()))
                        or {CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest} != BUILD_DIGESTS):
                    return unavailable()
                binding['projection'] = {'kind': 'corporate-l11b-v1',
                    'builds': {CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest}, 'route': page.url}
                lifetime = getattr(capture, 'observe_component_lifetime', None)
                if callable(lifetime) and lifetime(check_cancel=check_cancel) is not None:
                    if 'Induk' not in names:
                        return unavailable()
                    strong = _observe_l11b_hydrated(page, form, tab, capture, digest, main_digest, check_cancel)
                    if strong is None:
                        return unavailable()
                    binding['projection'] = strong
            if name == 'L10-B':
                if 'Induk' not in names:
                    return unavailable()
                proof = _observe_l10b(page, form, tab, panel, capture, check_cancel)
                _check_cancel(check_cancel)
                _check_corporate_route(page.url, selected)
                if proof is None:
                    return unavailable()
                binding['projection'] = proof
            if name == 'L10-D' and 'Induk' in names:
                # Preserve legacy evidence-leaf behavior when this optional
                # offer is unavailable. The unchanged dump gate still refuses
                # native output, whether or not originals were retained.
                original_offer = _observe_l10d_originals(page, form, tab, capture, digest, check_cancel, panel=panel)
                if original_offer is not None:
                    binding['original_custody'] = original_offer
            if name == 'L3':
                _advance('l3')
                if 'Induk' not in names:
                    return unavailable(l3_reason='induk_order')
                l3_diagnostic = {}
                inspected = _observe_l3(page, form, capture, digest, record, max_pages,
                                        check_cancel, reason_out=l3_diagnostic)
                if inspected is None:
                    return unavailable(l3_reason=l3_diagnostic.get('reason'),
                                       l3_table_shape=l3_diagnostic.get('table_shape'),
                                       l3_extra_layout=l3_diagnostic.get('extra_layout'),
                                       l3_extra_owner=l3_diagnostic.get('extra_owner'))
                binding.update(inspected)
            if name == 'L11-A':
                _advance('l11a')
                if 'Induk' not in names:
                    return unavailable(l11a_reason='induk_order')
                l11a_diagnostic = {}
                inspected = _observe_l11a(page, form, capture, digest, record, max_pages, check_cancel,
                                          reason_out=l11a_diagnostic)
                if inspected is None:
                    return unavailable(l11a_reason=l11a_diagnostic.get('reason'))
                binding.update(inspected)
            if name in ('L3', 'L11-A'):
                _check_cancel(check_cancel)
                enabled = _enabled_form_binding(form, tab, name)
                _check_cancel(check_cancel)
                _check_corporate_route(page.url, selected)
                if not enabled:
                    return unavailable(l3_reason='visibility_changed', l11a_reason='visibility_changed')
                binding['projection']['visibility_binding'] = 'current-induk-enabled-v1'
            if name == 'L1-D':
                _advance('l1d')
                if 'Induk' not in names:
                    return unavailable()
                _check_cancel(check_cancel)
                if not _enabled_form_binding(form, tab, name):
                    return unavailable()
                projection = _observe_l1d(page, form, capture, digest, check_cancel)
                _check_cancel(check_cancel)
                _check_corporate_route(page.url, selected)
                if projection is None or not _enabled_form_binding(form, tab, name):
                    return unavailable()
                projection['visibility_binding'] = 'current-induk-enabled-v1'
                binding['projection'] = projection
            if name == 'L8':
                _advance('l8')
                if 'Induk' not in names:
                    return unavailable(reason='induk_order')
                projection = _observe_l8(page, form, capture, digest, check_cancel)
                if projection is None:
                    return unavailable(reason=capture.l8_refusal_reason() or 'observation_error')
                binding['projection'] = projection
            if name == 'L7':
                _advance('l7')
                from coretax_corporate_projection import BUILD_DIGESTS, MAIN_SOURCE
                from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH
                if 'Induk' not in names or BUILD_DIGESTS.get(CIT_SOURCE_URL) != digest:
                    return unavailable()
                main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
                _check_cancel(check_cancel)
                if main_digest != BUILD_DIGESTS.get(MAIN_SOURCE):
                    return unavailable()
                grid = form.locator('rsh-citr-l7-grid1')
                if (grid.count() != 1 or grid.locator('p-table').count() != 1
                        or grid.locator('table').count() != 1 or form.locator('table').count() != 1):
                    return unavailable()
                metadata = grid.locator('table').evaluate(TABLE.replace('GROUP', '()=>""'))
                locale = page.evaluate('() => navigator.language')
                binding['projection'] = {'kind': 'corporate-l7-v1', 'builds': {
                    CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest}, 'route': page.url, 'locale': locale,
                    'tables': [{'component': 'rsh-citr-l7-grid1', 'headers': metadata['headers'],
                                'footer_spans': metadata['footer_spans']}]}
                strong = _observe_l7_negative(page, form, grid, tab, panel, capture,
                                               binding['projection'], check_cancel)
                if strong is not None:
                    binding['raw_negative_projection'] = strong
            if name == 'L11-C':
                _advance('l11c')
                from coretax_corporate_projection import L11C_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE
                from coretax_json import CORPORATE_COUNTRY_REFERENCE_URL
                from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH
                if 'Induk' not in names or L11C_BUILD_DIGESTS.get(CIT_SOURCE_URL) != digest:
                    return unavailable()
                main_digest = page.evaluate(_PPN_MAIN_BUILD_HASH, MAIN_SOURCE)
                _check_cancel(check_cancel)
                vendor_digest = page.evaluate(_BUILD_HASH, VENDOR_SOURCE)
                _check_cancel(check_cancel)
                if (main_digest != L11C_BUILD_DIGESTS.get(MAIN_SOURCE)
                        or vendor_digest != L11C_BUILD_DIGESTS.get(VENDOR_SOURCE)):
                    return unavailable()
                grid = form.locator('rshshr-citr-l11c-form-grid1')
                if (grid.count() != 1 or grid.locator('ui-grid-offline').count() != 1
                        or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1
                        or form.locator('table').count() != 1):
                    return unavailable()
                metadata = grid.locator('table').evaluate(TABLE.replace('GROUP', '()=>""'))
                environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
                references = []
                sequences = [e['sequence'] for e in capture.request_observations()
                    if e['url'] == CORPORATE_COUNTRY_REFERENCE_URL and e['method'] == 'GET'
                    and e['request_json'] is None]
                if sequences:
                    references.append({'endpoint': CORPORATE_COUNTRY_REFERENCE_URL,
                                       'method': 'GET', 'sequences': sequences})
                binding['projection'] = {'kind': 'corporate-l11c-v1', 'builds': {
                    CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest},
                    'route': page.url, **environment, 'references': references,
                    'tables': [{'component': 'rshshr-citr-l11c-form-grid1', 'headers': metadata['headers'],
                                'footer_spans': metadata['footer_spans']}]}
            if name == 'L10-C' and 'Induk' in names:
                projection = _observe_l10c_projection(page, form, tab, panel, capture, check_cancel)
                if projection is not None:
                    binding['projection'] = projection
            _advance('grid')
            for grid_selector, suffix, groups in GRID_ROLES.get(name, ()):
                grids = form.locator(grid_selector)
                if grids.count() != len(groups):
                    return unavailable()
                for index, group in enumerate(groups):
                    table = grids.nth(index).locator('p-table')
                    if table.count() != 1 or not _turn_grid(page, table, max_pages, check_cancel):
                        return unavailable()
                    endpoint = ORIGIN+'/returnsheet/api/loadcit/'+suffix
                    pages, seen = [], set()
                    for event in capture.request_observations():
                        request = event['request_json']
                        if event['url'] != endpoint or event['method'] != 'POST' or not isinstance(request,dict):
                            continue
                        if 'ReturnSheetRecordId' not in request:
                            return unavailable()
                        if request['ReturnSheetRecordId'] != record['record_id']:
                            raise JsonSafetyError('Observed grid belongs to a different selected return')
                        if group is not None and request.get('GroupType') != group:
                            continue
                        if name == 'L4':
                            if 'PeriodYear' not in request:
                                return unavailable()
                            period = record.get('source_fields', {}).get('TaxPeriodCode')
                            # DOM listing fallback has no native period binding.
                            # Caller request/response checks still reject conflicts
                            # before allowing whole-DOM fallback; do not invent one.
                            if period is None:
                                return unavailable()
                            if request['PeriodYear'] != period[-4:]:
                                raise JsonSafetyError('Observed grid year contradicts selected period')
                        first, rows = request.get('First'), request.get('Rows')
                        if type(first) is not int or first < 0 or type(rows) is not int or rows <= 0:
                            return unavailable()
                        key = json.dumps(request,sort_keys=True)
                        if key not in seen:
                            seen.add(key)
                            pages.append({'request_json':request,'offset':first})
                    if not pages:
                        return unavailable()
                    label = name+'/'+suffix+(('/'+group) if group else '')
                    binding['grids'].append({'name':label,'endpoint':endpoint,
                        'pages':sorted(pages,key=lambda item:item['offset'])})
                    if name == 'L4':
                        footer_requests = _l4_footer_requests(
                            capture.request_observations(), record_id=record['record_id'],
                            period=record.get('source_fields', {}).get('TaxPeriodCode'))
                        if not footer_requests:
                            return unavailable()
                        binding.setdefault('dependencies', []).extend(
                            {'endpoint': endpoint + '/footer', 'request_json': request}
                            for request in footer_requests)
            if name == 'L4':
                final_tables = _l4_tables(form)
                _check_cancel(check_cancel)
                if final_tables != binding['projection']['tables']:
                    return unavailable()
                # No new transport/capability when shared catalogs are absent:
                # legacy empty-only remains available, populated keeps fallback.
                if 'Induk' in names:
                    enabled = _enabled_form_binding(form, tab, name)
                    _check_cancel(check_cancel)
                    if enabled:
                        populated = _l4_populated_projection(page, capture, digest, final_tables, check_cancel)
                        _check_cancel(check_cancel)
                        if populated is not None:
                            enabled_end = _enabled_form_binding(form, tab, name)
                            _check_cancel(check_cancel)
                            latest_tables = _l4_tables(form)
                            _check_cancel(check_cancel)
                            _check_corporate_route(page.url, selected)
                            if not enabled_end or latest_tables != final_tables:
                                return unavailable()
                            binding['projection'] = populated

            if name == 'L10-A' and l10a_before is not None:
                strong = _observe_l10a_populated(page, form, tab, capture, l10a_before, check_cancel)
                _check_cancel(check_cancel)
                _check_corporate_route(page.url, selected)
                if strong is not None:
                    binding['projection'] = strong
            if name == 'L9' and binding.get('projection', {}).get('kind') == 'corporate-l9-details-v1':
                _check_cancel(check_cancel)
                if (not _enabled_form_binding(form, tab, name)
                        or _l9_tables(form, check_cancel) != binding['projection']['tables']
                        or capture.observe_component_lifetime(check_cancel=check_cancel) is None):
                    return unavailable()
                _check_cancel(check_cancel)
                _check_corporate_route(page.url, selected)
            forms.append(binding)
        _emit_timings()
        if 'Induk' in names:
            # The shipped, hash-pinned build exposes a tab only for the forms
            # the return actually carries data for. L1-B, L8 and the
            # data-conditional sheets below are rendered only when the return
            # has data for them (confirmed absent from CurrentFormData on a
            # live return whose prefill omits their root keys), so their
            # absence is legitimate and must not force a whole-record DOM
            # fallback. L10-A/L10-B/L10-C join that set: a live Amendment
            # return carries no L10-A/B/C data and renders no such tabs.
            # Every other reviewed form must be visible: an absent required
            # tab with an omitted JSON root would not produce an uncovered
            # evidence row, so downstream evidence matching alone cannot
            # prove completeness.
            data_conditional = {'L1-B', 'L8', 'L4', 'L7', 'L10-A', 'L10-B',
                                'L10-C', 'L10-D', 'L11-A', 'L11-C'}
            missing = set(FORMS) - data_conditional - names
            if digest == CIT_SOURCE_SHA256 and missing:
                return unavailable(reason='incomplete_coverage',
                                   missing_forms=','.join(sorted(missing)))
            # Only L1-B and L8 are reviewed as legitimately absent with an
            # inert path-only binding. Their bindings remain strictly
            # null/missing-inert.
            for absent in ('L1-B', 'L8'):
                if absent not in names:
                    names.add(absent)
                    forms.append({'name': absent,
                                  'paths': [[FORMS[absent][1]]],
                                  'disabled': True,
                                  'grids': [], 'responses': [], 'dependencies': []})
            return forms
        stage = 'induk'
        return unavailable()
    except (JsonSafetyError, CaptureCancelled):
        raise
    except Exception as error:
        _check_cancel(check_cancel)
        return unavailable(error)


def capture_financial(page, *, record, folder, check_cancel=None):
    from coretax_browser import _check_cancel, wait_idle
    from coretax_attachments import download_financial_attachments
    _check_cancel(check_cancel)
    _, tabs = _tabs(page)
    candidates = [tabs.nth(i) for i in range(tabs.count()) if tabs.nth(i).inner_text().strip()=='Induk']
    if len(candidates)!=1:
        return {'attachments':[], 'capture_complete':False,
            'errors':[{'object':'Induk/Laporan Keuangan','message':'No unique inspected corporate Induk'}]}
    candidates[0].click()
    wait_idle(page)
    attachments = download_financial_attachments(page,record,folder,check_cancel=check_cancel)
    _check_cancel(check_cancel)
    errors = [{'object':'Induk/Laporan Keuangan','message':'Financial PDF control is unsupported or incomplete'}
              for item in attachments if item['status']!='COMPLETE']
    return {'attachments':attachments,'capture_complete':bool(attachments) and not errors,'errors':errors}
