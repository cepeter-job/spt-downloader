"""Read-only Masa structure and request bindings; never reads DOM tax values."""
import json
import re

from coretax_json import ORIGIN, JsonSafetyError
from coretax_corporate import _BUILD_HASH, _tabs, _turn_grid
from coretax_masa_json import check_masa_request_identities

MAIN_SOURCE = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
TAX_SOURCES = {
    'PPN': ORIGIN + '/returnsheets/id-ID/640.36c042afd2381189.js',
    'PPh Unifikasi': ORIGIN + '/returnsheets/id-ID/693.4de61c6eb2000c7e.js',
}
BUILD_DIGESTS = {
    MAIN_SOURCE: '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
    TAX_SOURCES['PPN']: '4a7e33826b6d0395afb23372fb6b4a9d4be6abaab0ec25fa743c897d0e654aef',
    TAX_SOURCES['PPh Unifikasi']: '2694fdda5c23b7d5f0eefe0cf0a0c55caa0fe29acc590363f34684ed90188fe0',
}
# Component names come from the reviewed public build, not field-name guessing.
FORMS = {
    'PPN': {
        'INDUK': (None, ()),
        'A-1': ('rshshr-nvat-la1-form', (('rshshr-nvat-la1-grid', 'la1'),)),
        'A-2': ('rshshr-nvat-la2-form', (('rshshr-nvat-la2-grid', 'la2'),)),
        'B-1': ('rshshr-nvat-lb1-form', (('rshshr-nvat-lb1-grid', 'lb1'),)),
        'B-2': ('rshshr-nvat-lb2-form', (('rshshr-nvat-lb2-grid', 'lb2'),)),
        'B-3': ('rshshr-nvat-lb3-form', (('rshshr-nvat-lb3-grid', 'lb3'),)),
        'C': ('rshshr-nvat-lc-form', (('rshshr-nvat-lc-grid', 'lc'),)),
    },
    'PPh Unifikasi': {
        'INDUK': ('rshshr-spt-unifikasi', ()),
        'DAFTAR-I': ('rshshr-list-i', (('rshshr-list-i-grid-a', 'list-i-bpu'),
                                    ('rshshr-list-i-grid-b', 'list-i-bpnr'))),
        'DAFTAR-II': ('rshshr-list-ii', (('rshshr-list-ii-grid-a', 'list-ii-sp'),
                                      ('rshshr-list-ii-grid-b', 'list-ii-cy'))),
        'LAMPIRAN-I': ('rshshr-attachment-i', (('rshshr-attachment-i-grid', 'attachment-i'),)),
    },
}

FIELDS = r"""root => {
 const group=GROUP, visible=e=>!!e.getClientRects().length;
 const owner=root.closest('.p-tabview-panel');
 const labelFor=e=>{
   const input=e.matches('input,select,textarea')?e:e.querySelector('input,select,textarea');
   for(const candidate of [e,input].filter(Boolean)){
     const label=candidate.id?root.querySelector('label[for="'+CSS.escape(candidate.id)+'"]'):null;
     if(label)return label.textContent.trim();
   }
   for(let node=e,n=0;node&&node!==root&&n<7;node=node.parentElement,n++){
     const labels=[...node.querySelectorAll('label')].filter(visible);
     if(labels.length)return labels.map(l=>l.innerText.trim()).filter(Boolean).join(' / ');
   }
   return e.getAttribute('aria-label')||e.getAttribute('formcontrolname')||e.name||e.id||'';
 };
 const columnFor=e=>{
   if(!e.closest('p-inputnumber'))return '';
   const cell=e.closest('.col-md-3');
   if(!cell||!cell.parentElement.matches('.row'))return '';
   const grid=cell.parentElement, columns=[...grid.children], amount=grid.parentElement, row=amount.parentElement;
   if(columns.length!==4||!columns.every(c=>c.matches('.col-md-3')&&visible(c))||
      !amount.matches('.col-md-5')||!row.matches('.row')||!row.parentElement.matches('.p-accordion-content'))return '';
   for(let prior=row.previousElementSibling;prior;prior=prior.previousElementSibling){
     if(!prior.matches('.row')||!visible(prior))continue;
     const header=prior.querySelector(':scope > .col-md-5 > .row');
     if(!header||header.querySelector('input,textarea,select'))continue;
     const cells=[...header.children];
     if(cells.length!==4||!cells.every(c=>c.matches('.col-md-3')&&visible(c)))continue;
     const labels=cells.map(c=>(c.innerText||'').trim());
     if(labels.some(Boolean))return labels[columns.indexOf(cell)];
   }
   return '';
 };
 const candidates=[...root.querySelectorAll('[formcontrolname],input,textarea,select')];
 const seen=new Set(), fields=[];
 for(const child of candidates){
   if(child.closest('table,[hidden],[aria-hidden="true"]')||child.closest('.p-tabview-panel')!==owner)continue;
   if(child.matches('input[type=password],input[type=hidden]'))continue;
   const control=child.closest('[formcontrolname]')||child;
   if(seen.has(control)||!visible(control))continue;
   seen.add(control);
   const field=control.getAttribute('formcontrolname')||control.getAttribute('name')||control.id||'';
   const label=labelFor(control);
   const labels=[...control.parentElement.querySelectorAll(':scope > label')]
     .filter(l=>visible(l)&&l.innerText.trim()!==label&&!l.htmlFor);
   fields.push({field,label,group:group(control),column_label:labels.length===1?labels[0].innerText.trim():columnFor(control),tag:control.tagName});
 }
 return fields;
}"""

TABLE = r"""table => {
 const group=GROUP;
 const rows=table.tHead?[...table.tHead.rows].filter(r=>![...r.cells].some(c=>c.querySelector('p-columnfilter,input,select'))):[];
 const matrix=[];
 rows.forEach((tr,ri)=>{
   matrix[ri]||=[];let ci=0;
   for(const cell of tr.cells){
     if(cell.colSpan>64||cell.rowSpan>16)throw Error('Unsupported header span');
     while(matrix[ri][ci]!==undefined)ci++;
     const label=(cell.textContent||'').replace(/\s+/g,' ').trim();
     for(let r=ri;r<ri+cell.rowSpan;r++){
       matrix[r]||=[];
       for(let c=ci;c<ci+cell.colSpan;c++)matrix[r][c]=label;
     }
     ci+=cell.colSpan;
   }
 });
 const width=Math.max(0,...matrix.map(r=>r.length));
 const headers=Array.from({length:width},(_,i)=>[...new Set(matrix.map(r=>r[i]).filter(Boolean))].join(' / '));
 return {headers,group:group(table),footer_spans:table.tFoot?[...table.tFoot.rows].map(r=>[...r.cells].map(c=>c.colSpan)):[]};
}"""


def _observations(capture, record, scope):
    events = capture.request_observations()
    check_masa_request_identities(events, record, scope)
    if any(event.get('status') in (401, 403) for event in events):
        raise JsonSafetyError('Masa HTTP authorization was rejected')
    return events


def _requests(events, endpoint, record_id, *, grid=False):
    # Keep every sequence for repeated requests. The adapter must compare their
    # response snapshots, not silently choose whichever reply arrived last.
    matches = {}
    for event in events:
        if event['url'] != endpoint:
            continue
        request = event.get('request_json')
        identity = 'ReturnSheetRecordId' if grid else 'RecordId'
        if (event.get('method') != 'POST' or not isinstance(request, dict)
                or request.get(identity) != record_id
                or type(event.get('status')) is not int or not 200 <= event['status'] < 300
                or type(event.get('sequence')) is not int or event['sequence'] <= 0):
            raise ValueError('Incomplete Masa request binding')
        if grid and (request.get('Filters', []) != []
                     or type(request.get('First')) is not int or request['First'] < 0
                     or type(request.get('Rows')) is not int or not 0 < request['Rows'] <= 1000):
            raise ValueError('Unsupported Masa grid scope')
        key = json.dumps(request, sort_keys=True)
        match = matches.setdefault(key, {'request_json': request, 'sequences': []})
        if event['sequence'] not in match['sequences']:
            match['sequences'].append(event['sequence'])
    if not matches:
        raise ValueError('Missing observed Masa request')
    return list(matches.values())


def _pages(events, endpoint, record_id, total):
    pages = _requests(events, endpoint, record_id, grid=True)
    pages.sort(key=lambda item: item['request_json']['First'])
    expected, query = 0, None
    for page in pages:
        request = page['request_json']
        current = {k: v for k, v in request.items() if k not in ('First', 'Rows')}
        if query is not None and current != query:
            raise ValueError('Masa query changed during traversal')
        if request['First'] != expected or expected >= total and expected != 0:
            raise ValueError('Masa observed pages overlap or contain a gap')
        query = current
        page['offset'] = request['First']
        expected += request['Rows']
    if expected < total:
        raise ValueError('Incomplete Masa observed pagination')
    return pages


def observe_masa_forms(page, record, scope, capture, *, max_pages=1000, check_cancel=None):
    """Bind known tabs/controls/tables to observed requests, not source values.

    Successful observation is not native eligibility: the adapter must still
    verify packet custody, source columns, reference data and every projection.
    """
    from coretax_browser import GROUP_JS, _check_cancel, list_taxpayer_id, verify_detail_url, wait_idle
    _check_cancel(check_cancel)
    _observations(capture, record, scope)
    try:
        tax = record['meta'].get('Jenis Pajak')
        if tax not in FORMS or type(max_pages) is not int or max_pages <= 0:
            return None
        verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
        builds = {}
        for url in (MAIN_SOURCE, TAX_SOURCES[tax]):
            _check_cancel(check_cancel)
            digest = page.evaluate(_BUILD_HASH, url)
            if digest != BUILD_DIGESTS[url]:
                return None
            builds[url] = digest
        view, tabs = _tabs(page)
        names = [tabs.nth(i).inner_text().strip() for i in range(tabs.count())]
        if len(names) != len(set(names)) or set(names) != set(FORMS[tax]):
            return None
        environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
        forms = []
        for ordinal, name in enumerate(names):
            _check_cancel(check_cancel)
            tab = tabs.nth(ordinal)
            if tab.evaluate('(e)=>e.closest("li").classList.contains("p-disabled")||e.getAttribute("aria-disabled")==="true"'):
                return None
            panel_id = tab.get_attribute('aria-controls')
            if not panel_id or tab.get_attribute('href') not in (None, '', '#', '#' + panel_id):
                return None
            panel = view.locator(':scope > .p-tabview-panels > .p-tabview-panel[id=' + json.dumps(panel_id) + ']')
            if panel.count() != 1:
                return None
            tab.click()
            wait_idle(page)
            verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
            panel.wait_for(state='visible', timeout=30000)
            selector, roles = FORMS[tax][name]
            form = panel.locator(selector) if selector else panel
            if form.count() != 1 or not form.is_visible():
                return None
            fields = form.evaluate(FIELDS.replace('GROUP', GROUP_JS))
            if any(not field['field'] or not field['label'] for field in fields):
                return None
            binding = {'name': name, 'fields': fields, 'tables': [], 'builds': dict(builds), **environment}
            if tax == 'PPh Unifikasi' and name == 'INDUK':
                tree = form.locator('rshshr-spt-unifikasi-grid p-treetable table:visible')
                if tree.count() != 1:
                    return None
                binding['tables'].append({'name': 'income-taxes', **tree.evaluate(TABLE.replace('GROUP', GROUP_JS))})
            if form.locator('table:visible').count() != len(roles) + len(binding['tables']):
                return None
            for grid_selector, suffix in roles:
                table = form.locator(grid_selector + ' p-table')
                if table.count() != 1 or not _turn_grid(page, table, max_pages, check_cancel):
                    return None
                verify_detail_url(page.url, list_taxpayer_id(record['list_url']), record['record_id'])
                physical = table.locator('table:visible')
                marker = table.locator('.p-paginator-current')
                if physical.count() != 1 or marker.count() != 1:
                    return None
                match = re.search(r'(?:of|dari)\s+([0-9]+)(?![0-9.,])', marker.inner_text(), re.I)
                if not match:
                    return None
                total = int(match[1])
                endpoint = ORIGIN + '/returnsheet/api/' + ('loadndvat/' if tax == 'PPN' else 'loadwtr/') + suffix + '-grid'
                pages = _pages(_observations(capture, record, scope), endpoint, record['record_id'], total)
                metadata = physical.evaluate(TABLE.replace('GROUP', GROUP_JS))
                if not metadata['headers'] or not all(metadata['headers']):
                    return None
                binding['tables'].append({'name': suffix, **metadata, 'endpoint': endpoint,
                                          'pages': pages, 'source_total': total})
            if name == 'INDUK':
                endpoint = ORIGIN + '/returnsheet/api/prefillreturnsheet/' + ('nvat' if tax == 'PPN' else 'withholding-tax')
                binding['primary'] = {'endpoint': endpoint, 'requests': _requests(
                    _observations(capture, record, scope), endpoint, record['record_id'])}
            forms.append(binding)
        return forms
    except JsonSafetyError:
        raise
    except Exception:
        _check_cancel(check_cancel)
        return None
    finally:
        # Unknown structure/build cannot turn an observed contradiction into
        # ordinary fallback. The dispatch also checks again after final drain.
        _observations(capture, record, scope)
