"""Read-only Masa structure and request bindings; never reads DOM tax values."""
import json
import re

from coretax_json import ORIGIN, JsonSafetyError
from coretax_corporate import _BUILD_HASH, _tabs, _turn_grid
from coretax_masa_json import check_masa_request_identities

from coretax_masa_bindings import MAIN_SOURCE, TAX_SOURCES, BUILD_DIGESTS, FORMS

# The reviewed PPN main bundle exceeds 4 MiB. Keep the larger budget isolated
# from other tax types and chunks; the loaded-source and digest gates still apply.
_PPN_MAIN_BUILD_HASH = r'''async url => {
 const loaded=[...document.scripts].some(s=>s.src===url) ||
   performance.getEntriesByType('resource').some(e=>e.name===url);
 if(!loaded)return null;
 const response=await fetch(url,{credentials:'same-origin',redirect:'error',cache:'no-store'});
 if(!response.ok || !/javascript/i.test(response.headers.get('content-type')||''))return null;
 const bytes=await response.arrayBuffer();
 if(bytes.byteLength>5*1024*1024)return null;
 return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
   .map(x=>x.toString(16).padStart(2,'0')).join('');
}'''

FIELDS = r"""(root, context={}) => {
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
 // Public customFormControl bindings do not appear as DOM formcontrolname.
 // Match the reviewed host and its own static label, never generated input IDs.
 const customField=control=>{
   let binding=null;
   if(context.tax==='PPh Unifikasi'&&['INDUK','DAFTAR-I','DAFTAR-II','LAMPIRAN-I'].includes(context.form))
     binding={field:'TaxPeriodCode',label:'Masa Pajak',role:'Tax Period'};
   else if(context.tax==='PPN'&&context.form==='INDUK')
     binding={field:'Model',label:'Normal/Pembetulan',role:'Model *'};
   const row=control.closest('.form-group.row');
   if(!binding||!row||row.querySelectorAll('ui-dropdown').length!==1)return null;
   const labels=[...row.querySelectorAll(':scope > label')].filter(visible);
   if(labels.length!==1||labels[0].textContent.trim()!==binding.label||
      labels[0].getAttribute('ariaLabel')!==binding.role)return null;
   return {field:binding.field,label:binding.label,group:group(control),column_label:'',tag:control.tagName};
 };
 const ppnInduk=context.tax==='PPN'&&context.form==='INDUK';
 const candidates=[...root.querySelectorAll('ui-dropdown,p-dropdown,p-multiselect,p-radiobutton,[formcontrolname],input,textarea,select'+(ppnInduk?',p-checkbox':''))];
 const seen=new Set(), fields=[];
 for(const child of candidates){
   if(child.closest('table,[hidden],[aria-hidden="true"]')||child.closest('.p-tabview-panel')!==owner)continue;
   if(child.matches('input[type=password],input[type=hidden]'))continue;
   const calendar=ppnInduk?child.closest('p-calendar'):null;
   const checkbox=ppnInduk?child.closest('p-checkbox'):null;
   const control=calendar||checkbox||child.closest('ui-dropdown')||child.closest('[formcontrolname]')||
     child.closest('p-dropdown,p-multiselect,p-radiobutton')||child;
   if(seen.has(control)||!visible(control))continue;
   seen.add(control);
   if(control.matches('ui-dropdown')){
     const metadata=customField(control);
     if(!metadata)return null;
     fields.push(metadata);
     continue;
   }
   if(checkbox){
     // Public Ja/Wa use [formControl], so no DOM formcontrolname exists.
     // This identifies structure only; the checkbox state stays in source JSON.
     const row=checkbox.parentElement;
     const labels=[...row.querySelectorAll(':scope > label')].filter(visible);
     const inputs=checkbox.querySelectorAll('input');
     if(row.querySelectorAll('p-checkbox').length!==1||labels.length!==1||
        labels[0].textContent.trim()!=='Ganti SPT sebelumnya'||
        labels[0].getAttribute('ariaLabel')!=='Replace Previous Tax Return'||
        group(checkbox)!=='III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR'||
        checkbox.hasAttribute('formcontrolname')||checkbox.hasAttribute('name')||
        inputs.length!==1||!inputs[0].matches('input[type=checkbox]'))return null;
     fields.push({field:'ReplacementPrevious',label:'Ganti SPT sebelumnya',
       group:group(checkbox),column_label:'',tag:checkbox.tagName});
     continue;
   }
   if(calendar){
     const row=calendar.closest('.form-group.row');
     const labels=row?[...row.querySelectorAll(':scope > label')].filter(visible):[];
     if(!row||row.querySelectorAll('p-calendar').length!==1||labels.length!==1)return null;
     const label=labels[0].textContent.trim(),role=labels[0].getAttribute('ariaLabel')||'';
     let field='';
     if(label==='Tanggal Penandatanganan SPT'&&role==='')field='DateOfTaxReturnSigning';
     if(label==='Batas Waktu Penyampaian SPT'&&role==='Deadline Submission')field='DeadlineSubmission';
     if(!field)return null;
     fields.push({field,label,group:group(control),column_label:'',tag:control.tagName});
     continue;
   }
   if(control.matches('p-dropdown,p-multiselect')){
     const paginator=control.closest('.p-paginator');
     if(control.matches('p-dropdown')&&context.tax==='PPN'&&
        ['A-1','A-2','B-1','B-2','B-3','C'].includes(context.form)&&
        control.closest('p-paginator')&&control.closest('p-table')&&paginator&&
        paginator.querySelectorAll('.p-paginator-current').length===1)continue;
     return null;
   }
   const field=control.getAttribute('formcontrolname')||control.getAttribute('name')||control.id||'';
   const label=labelFor(control);
   const labels=[...control.parentElement.querySelectorAll(':scope > label')]
     .filter(l=>visible(l)&&l.innerText.trim()!==label&&!l.htmlFor);
   const metadata={field,label,group:group(control),column_label:labels.length===1?labels[0].innerText.trim():columnFor(control),tag:control.tagName};
   if(control.matches('p-radiobutton,input[type=radio]')){
     if(context.form!=='INDUK'||!['PPN','PPh Unifikasi'].includes(context.tax))return null;
     // Literal option attributes are reviewed UI structure, not selected values.
     // Never read the nested input's value or checked state.
     const option=control.getAttribute('value');
     let choices=null;
     if(field==='DeclarationBy')choices={'0':context.tax==='PPN'?'PKP':'Wajib Pajak','1':'Kuasa Wajib Pajak'};
     if(field==='AskedTo'&&context.tax==='PPN')choices={
       CARRY_FORWARD:'1. dikompensasikan',FAST_REFUND:'2. dikembalikan melalui pengembalian pendahuluan',
       FORWARD_REFUND:'3. dikembalikan melalui pemeriksaan'};
     if(!choices)return null;
     if(!Object.hasOwn(choices,option)||label!==choices[option])return null;
     metadata.option=option;
   }
   fields.push(metadata);
 }
 return fields;
}"""

PPN_LABEL_TABLE = r"""table => {
 const column=table.parentElement;
 if(table.closest('p-table,[role="grid"]')||table.tHead||table.tFoot||table.querySelector('th')||
    !column.matches('.col-md-3,.col-md-5,.col-md-7,.col-md-9')||
    !column.parentElement.matches('.row')||table.rows.length!==1)return false;
 const cells=[...table.rows[0].cells];
 if(cells.length<1||cells.length>3||cells.some(c=>c.tagName!=='TD'))return false;
 return !table.querySelector('input:not([type="checkbox"]),textarea,select,p-inputnumber,p-dropdown,p-multiselect,p-radiobutton,table');
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


def _requests(events, endpoint, record_id, *, grid=False, identity=None):
    # Keep every sequence for repeated requests. The adapter must compare their
    # response snapshots, not silently choose whichever reply arrived last.
    identity = identity or ('ReturnSheetRecordId' if grid else 'RecordId')
    matches = {}
    for event in events:
        if event['url'] != endpoint:
            continue
        request = event.get('request_json')
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
            build_hash = _PPN_MAIN_BUILD_HASH if tax == 'PPN' and url == MAIN_SOURCE else _BUILD_HASH
            digest = page.evaluate(build_hash, url)
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
            target = '[id=' + json.dumps(panel_id) + ']'
            # aria-controls must identify one element, including when a nested
            # view contains a duplicate ID. Nested tabs themselves are allowed.
            if view.locator(target).count() != 1:
                return None
            panel = view.locator(
                ':scope > .p-tabview-panels > .p-tabview-panel' + target + ', '
                ':scope > .p-tabview-panels > p-tabpanel > .p-tabview-panel' + target)
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
            fields = form.evaluate(FIELDS.replace('GROUP', GROUP_JS), {'tax': tax, 'form': name})
            if fields is None or any(not field['field'] or not field['label'] for field in fields):
                return None
            binding = {'name': name, 'fields': fields, 'tables': [], 'builds': dict(builds), **environment}
            if tax == 'PPh Unifikasi' and name == 'INDUK':
                tree = form.locator('rshshr-spt-unifikasi-grid p-treetable table:visible')
                if tree.count() != 1:
                    return None
                binding['tables'].append({'name': 'income-taxes', **tree.evaluate(TABLE.replace('GROUP', GROUP_JS))})
            visible_tables = form.locator('table:visible')
            layout_count = 0
            if tax == 'PPN' and name == 'INDUK':
                # The pinned Induk uses one-row Bootstrap label tables. These
                # are not source grids; other table shapes remain unsupported.
                layout_count = sum(bool(visible_tables.nth(index).evaluate(PPN_LABEL_TABLE))
                                   for index in range(visible_tables.count()))
            if visible_tables.count() - layout_count != len(roles) + len(binding['tables']):
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
                table_binding = {'name': suffix, **metadata, 'endpoint': endpoint,
                                 'pages': pages, 'source_total': total}
                if tax == 'PPN' and suffix == 'lc':
                    # C initializes a separate footer request whose callback
                    # overrides both C and Induk totals. A grid is not its source.
                    footer_endpoint = endpoint + '/footer'
                    requests = _requests(_observations(capture, record, scope),
                        footer_endpoint, record['record_id'], identity='ReturnSheetRecordId')
                    if any(item['request_json'].get('IsNormalVAT') is not True for item in requests):
                        return None
                    table_binding['footer_source'] = {'endpoint': footer_endpoint, 'requests': requests}
                binding['tables'].append(table_binding)
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
