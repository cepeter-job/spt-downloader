"""Readonly corporate UI bindings pinned to reviewed public build bytes."""
import json
import time
from coretax_json import ORIGIN, JsonSafetyError

CIT_SOURCE_URL = ORIGIN + '/returnsheets/id-ID/525.ec1edffbb4a91d20.js'
CIT_SOURCE_SHA256 = 'fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d'
FORMS = {
 'Induk': ('rshshr-citr-main-form', 'MainFormData'),
 'L1-B': ('rshshr-citr-l1b-form', 'L1bFormData'),
 'L2': ('rshshr-citr-l2-form', 'ListOfOwnership'),
 'L4': ('rshshr-citr-l4-form', 'ListOfIncomeSubjectToFinalTaxAndNonTaxableObject'),
 'L6': ('rshshr-citr-l6-form', 'FiscalYearIncomeTax'),
 'L9': ('rshshr-citr-l9-form', 'RecapitulationFiscalDepreciationAmortization'),
 'L10-A': ('rshshr-citr-l10a-form', 'DeclarationTransactionRelatedParties'),
 'L10-B': ('rshshr-citr-l10b-form', 'L10bFormData'),
 'L10-C': ('rshshr-citr-l10c-form', 'L10cFormData'),
 'L10-D': ('rshshr-citr-l10d-form', 'L10dFormData'),
 'L11-B': ('rshshr-citr-l11b-form', 'L11BFormData'),
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


def _turn_grid(page, table, max_pages, check_cancel):
    from coretax_browser import _check_cancel, wait_idle
    previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
    for _ in range(max_pages):
        _check_cancel(check_cancel)
        previous = table.locator(previous_selector)
        if not previous.count():
            break
        previous.click()
        wait_idle(page)
    if table.locator(previous_selector).count():
        return False
    seen = set()
    for _ in range(max_pages):
        _check_cancel(check_cancel)
        marker = table.locator('.p-paginator-current')
        if marker.count() != 1:
            return False
        state = marker.inner_text()
        if state in seen:
            return False
        seen.add(state)
        next_button = table.locator('.p-paginator-next:not([disabled]):not(.p-disabled)')
        if not next_button.count():
            return True
        next_button.click()
        deadline = time.monotonic() + 30
        while marker.inner_text() == state:
            _check_cancel(check_cancel)
            if time.monotonic() >= deadline:
                return False
            page.wait_for_timeout(100)
        wait_idle(page)
    return False


def observe_forms(page, record, scope, capture, *, approved_digest, max_pages=1000, check_cancel=None):
    from coretax_browser import _check_cancel, wait_idle, verify_detail_url, list_taxpayer_id
    _check_cancel(check_cancel)
    verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
    try:
        digest = page.evaluate(_BUILD_HASH, CIT_SOURCE_URL)
        _check_cancel(check_cancel)
        if digest != approved_digest:
            return None
        view, tabs = _tabs(page)
        if not tabs.count():
            return None
        forms, names = [], set()
        for ordinal in range(tabs.count()):
            _check_cancel(check_cancel)
            tab = tabs.nth(ordinal)
            if tab.evaluate('(e)=>e.closest("li").classList.contains("p-disabled")||e.getAttribute("aria-disabled")==="true"'):
                continue
            name = tab.inner_text().strip()
            if name not in FORMS or name in names:
                return None
            names.add(name)
            tab.click()
            wait_idle(page)
            panel_id = tab.get_attribute('aria-controls')
            if not panel_id:
                return None
            panel = view.locator('[id=' + json.dumps(panel_id) + ']')
            panel.wait_for(state='visible', timeout=30000)
            selector, root = FORMS[name]
            form = panel.locator(selector)
            if form.count() != 1 or not form.is_visible():
                return None
            binding = {'name':name, 'paths':[[root]], 'grids':[]}
            if name == 'Induk':
                binding['primary'] = {'endpoint':ORIGIN+'/returnsheet/api/prefillreturnsheet/corporate-income',
                    'request_json':{'RecordId':record['record_id'], 'OnManualClick':False}}
            for grid_selector, suffix, groups in GRID_ROLES.get(name, ()):
                grids = form.locator(grid_selector)
                if grids.count() != len(groups):
                    return None
                for index, group in enumerate(groups):
                    table = grids.nth(index).locator('p-table')
                    if table.count() != 1 or not _turn_grid(page, table, max_pages, check_cancel):
                        return None
                    endpoint = ORIGIN+'/returnsheet/api/loadcit/'+suffix
                    pages, seen = [], set()
                    for event in capture.request_observations():
                        request = event['request_json']
                        if event['url'] != endpoint or event['method'] != 'POST' or not isinstance(request,dict):
                            continue
                        if 'ReturnSheetRecordId' not in request:
                            return None
                        if request['ReturnSheetRecordId'] != record['record_id']:
                            raise JsonSafetyError('Observed grid belongs to a different selected return')
                        if group is not None and request.get('GroupType') != group:
                            continue
                        if name == 'L4':
                            if 'PeriodYear' not in request:
                                return None
                            period = record.get('source_fields', {}).get('TaxPeriodCode')
                            # DOM listing fallback has no native period binding.
                            # Caller request/response checks still reject conflicts
                            # before allowing whole-DOM fallback; do not invent one.
                            if period is None:
                                return None
                            if request['PeriodYear'] != period[-4:]:
                                raise JsonSafetyError('Observed grid year contradicts selected period')
                        first, rows = request.get('First'), request.get('Rows')
                        if type(first) is not int or first < 0 or type(rows) is not int or rows <= 0:
                            return None
                        key = json.dumps(request,sort_keys=True)
                        if key not in seen:
                            seen.add(key)
                            pages.append({'request_json':request,'offset':first})
                    if not pages:
                        return None
                    label = name+'/'+suffix+(('/'+group) if group else '')
                    binding['grids'].append({'name':label,'endpoint':endpoint,
                        'pages':sorted(pages,key=lambda item:item['offset'])})
            forms.append(binding)
        return forms if 'Induk' in names else None
    except JsonSafetyError:
        raise
    except Exception:
        _check_cancel(check_cancel)
        return None


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
