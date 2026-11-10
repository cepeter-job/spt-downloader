"""Readonly corporate UI bindings pinned to reviewed public build bytes."""
import json
import time
from coretax_build_pins import load_build_pins
from coretax_json import ORIGIN, JsonSafetyError

CIT_SOURCE_URL = ORIGIN + '/returnsheets/id-ID/525.32c49782948fc5ef.js'
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
    from coretax_browser import _check_cancel, _click_table_paginator, wait_idle
    if type(max_pages) is not int or max_pages <= 0:
        return False
    previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
    next_selector = '.p-paginator-next:not([disabled]):not(.p-disabled)'
    marker = table.locator('.p-paginator-current')
    owner = table.element_handle()
    if owner is None:
        return False

    def advance(control, state):
        if control.count() != 1:
            return False
        handle = control.element_handle()
        try:
            _click_table_paginator(handle, owner, check_cancel)
        except RuntimeError:
            return False
        finally:
            handle.dispose()
        deadline = time.monotonic() + 30
        while marker.inner_text() == state:
            _check_cancel(check_cancel)
            if time.monotonic() >= deadline:
                return False
            page.wait_for_timeout(100)
        wait_idle(page)
        return True

    try:
        if marker.count() != 1:
            return False
        resets = set()
        for _ in range(max_pages):
            _check_cancel(check_cancel)
            previous = table.locator(previous_selector)
            if not previous.count():
                break
            state = marker.inner_text()
            if state in resets or not advance(previous, state):
                return False
            resets.add(state)
        if table.locator(previous_selector).count():
            return False
        seen = set()
        for ordinal in range(max_pages):
            _check_cancel(check_cancel)
            state = marker.inner_text()
            if state in seen:
                return False
            seen.add(state)
            next_button = table.locator(next_selector)
            if not next_button.count():
                return True
            if ordinal + 1 >= max_pages or not advance(next_button, state):
                return False
        return False
    finally:
        owner.dispose()


def _observe_l1d(page, form, capture, digest, check_cancel):
    """Inspect only owned structure, loaded providers and fresh lifetime."""
    from coretax_browser import _check_cancel, CORPORATE_STRUCTURE_JS
    from coretax_corporate_projection import L1D_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE
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
    tables = []
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
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if capture.observe_component_lifetime(check_cancel=check_cancel) is None:
        return None
    return {'kind': 'corporate-l1d-v1', 'builds': {
        CIT_SOURCE_URL: digest, MAIN_SOURCE: main_digest, VENDOR_SOURCE: vendor_digest},
        'route': page.url, **environment, 'tables': tables}


def _observe_l8(page, form, capture, digest, check_cancel):
    """Bind the single L8 structure without reading amounts or business controls."""
    from coretax_browser import _check_cancel
    from coretax_corporate_projection import L8_BUILD_DIGESTS, L8_HEADERS, _L8_GROUP, MAIN_SOURCE, VENDOR_SOURCE
    from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH
    if digest != L8_BUILD_DIGESTS.get(CIT_SOURCE_URL):
        return None
    if capture.observe_l8_lifetime(check_cancel=check_cancel) is None:
        return None
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
    grid = form.locator('rsh-citr-l8-form-grid1')
    if (main_digest != L8_BUILD_DIGESTS.get(MAIN_SOURCE)
            or vendor_digest != L8_BUILD_DIGESTS.get(VENDOR_SOURCE)
            or form.locator('table').count() != 1 or grid.count() != 1 or not grid.is_visible()
            or grid.locator('p-table').count() != 1 or grid.locator('table').count() != 1):
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
        return None
    metadata = table.evaluate(TABLE.replace('GROUP', '()=>""'))
    environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
    _check_cancel(check_cancel)
    if (metadata['headers'] != L8_HEADERS or metadata['footer_spans'] != [[1, 1, 1]]
            or capture.observe_l8_lifetime(check_cancel=check_cancel) is None):
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
    from coretax_corporate_projection import _L3_CAPTIONS
    return form.evaluate(r'''(form, captions) => {
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
      return rows.every((row,i)=>{
        const cells=[...row.children];
        if(cells.length!==2 || cells.some(c=>c.localName!=='th') ||
           cells[0].colSpan!==10 || cells[1].colSpan!==1 ||
           cells.some(c=>c.rowSpan!==1) || cells[0].getAttribute('width')!=='1099' ||
           cells[1].getAttribute('width')!=='116' || cells[0].children.length ||
           (cells[0].textContent||'').replace(/\s+/g,' ').trim()!==captions[i]) return false;
        const controls=cells[1].querySelectorAll(':scope > p-inputnumber');
        if(controls.length!==1 || cells[1].children.length!==1 ||
           controls[0].getAttribute('formcontrolname')!==names[i]) return false;
        const inputs=controls[0].querySelectorAll('input');
        return inputs.length===1 && inputs[0].getAttribute('id')===names[i];
      });
    }''', list(_L3_CAPTIONS), timeout=1000) is True


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
    for url in CORPORATE_L3_REFERENCE_URLS.values():
        sequences = [item['sequence'] for item in observations
            if item['url'] == url and item['method'] == 'GET' and item.get('request_json') is None]
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


def observe_forms(page, record, scope, capture, *, approved_digest, max_pages=1000, check_cancel=None):
    from coretax_browser import _check_cancel, verify_detail_url, list_taxpayer_id
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

    def unavailable(error=None, *, l3_reason=None, l3_table_shape=None,
                    l3_extra_layout=None, l3_extra_owner=None, l11a_reason=None):
        # A finite stage and an observed ordinal, never tab text, values,
        # URL, source body or exception message. Does not grant JSON admission.
        # Emit already-measured stage segments so even a late refusal keeps
        # the bounded, value-free performance trail.
        _emit_timings()
        diagnostics.record('corporate.observe_unavailable', level='WARNING',
                           corporate_observer_stage=stage, form_ordinal=ordinal_safe,
                           corporate_l3_reason=l3_reason,
                           corporate_l3_table_shape=l3_table_shape,
                           corporate_l3_extra_layout=l3_extra_layout,
                           corporate_l3_extra_owner=l3_extra_owner,
                           corporate_l11a_reason=(l11a_reason or 'observation_error') if stage == 'l11a' else None,
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
            return unavailable()
        _advance('tabs')
        view, tabs = _tabs(page)
        if not tabs.count():
            return unavailable()
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
                return unavailable()
            _check_corporate_route(page.url, selected)
            selector, root = FORMS[name]
            _advance('form')
            form = panel.locator(selector)
            if form.count() != 1 or not form.is_visible():
                return unavailable()
            binding = {'name':name, 'paths':[[root]], 'grids':[]}
            if name == 'Induk':
                binding['primary'] = {'endpoint':ORIGIN+'/returnsheet/api/prefillreturnsheet/corporate-income',
                    'request_json':{'RecordId':record['record_id'], 'OnManualClick':False}}
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
                    return unavailable()
                projection = _observe_l8(page, form, capture, digest, check_cancel)
                if projection is None:
                    return unavailable()
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
            forms.append(binding)
        _emit_timings()
        if 'Induk' in names:
            # The shipped, hash-pinned 525 build has a CDP-reviewed 15-tab
            # inventory: all FORMS other than L1-B and L8 must be visible.
            # An absent required tab with an omitted JSON root would not
            # produce an uncovered evidence row, so downstream evidence
            # matching alone cannot prove completeness. Refuse this exact
            # reviewed build when its native tab inventory is incomplete.
            # Other asset builds need their own reviewed inventory before
            # their approved pin can adopt this completeness contract.
            if digest == CIT_SOURCE_SHA256 and (
                    set(FORMS) - {'L1-B', 'L8'} - names):
                return unavailable()
            # Only L1-B and L8 are reviewed as legitimately absent.
            # Their path-only bindings remain strictly null/missing-inert.
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
    except JsonSafetyError:
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
