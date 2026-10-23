"""Ambil data UI Coretax secara read-only melalui akses yang diizinkan.

Modul ini tidak memasukkan password, mengambil token, atau menjalankan aksi
penulisan. Login desktop ditangani terpisah oleh spt_desktop.auth.
"""
from spt_desktop import diagnostics
import time
import re
import json
import os
from contextlib import ExitStack, nullcontext
from uuid import uuid4
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from coretax_exporter import in_scope, validate_scope, deduplicate_inventory
from coretax_json import (JsonSafetyError, LOOKUP_HEADERS, SUBMITTED_ENDPOINT,
                          adapt_inventory_page, validate_inventory_rows)
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError
from coretax_json import validate_detail_source
from coretax_corporate import CIT_SOURCE_SHA256
from coretax_inventory import (InventoryFilterRoute, plan_year_filters, read_period_catalog,
                               validate_partition_response, prove_period_equivalence)

CELL_JS = r'''(cell) => {
 const clone=cell.cloneNode(true);
 clone.querySelectorAll('.p-column-title,button,script,style,.p-hidden-accessible').forEach(e=>e.remove());
 clone.querySelectorAll('input,textarea,select').forEach(e=>e.remove());
 let text=(clone.textContent||'').replace(/\s+/g,' ').trim();
 const vals=[...cell.querySelectorAll('input:not([type=password]):not([type=hidden]),textarea,select')]
 .filter(e=>e.getAttribute('role')!=='combobox' && !e.closest('.p-hidden-accessible') && (!(e.type==='radio'||e.type==='checkbox')||e.checked))
 .map(e=>(e.type==='checkbox'||e.type==='radio') ? String(e.checked) : (e.tagName==='SELECT' ? e.selectedOptions[0]?.textContent||e.value : e.value));
 return [text,...vals.filter(v=>v!=='' && v!==text)].filter(Boolean).join(' | ');
}'''

GROUP_JS = r'''(element) => {
 const visible=e=>!!e.getClientRects().length;
 const headings='h1,h2,h3,h4,h5,h6,[role="heading"],legend,.p-accordion-header-text,.p-panel-title';
 // Stop at another table: its heading cannot label this table/group.
 for(let current=element;current && !current.matches('.p-tabview-panel');current=current.parentElement){
  for(let sibling=current.previousElementSibling;sibling;sibling=sibling.previousElementSibling){
   if(sibling.matches('table')||sibling.querySelector('table')) break;
   const found=[...(sibling.matches(headings)?[sibling]:[]),...sibling.querySelectorAll(headings)].filter(visible);
   if(found.length===1) return (found[0].innerText||'').trim();
   if(found.length>1) return '';
  }
  if(current.matches('section,fieldset')) break;
 }
 return '';
}'''

CORPORATE_STRUCTURE_JS = r'''(table, name) => {
 const panel=table.closest('.p-tabview-panel');
 const form=table.closest('rshshr-citr-l1d-form,rshshr-citr-l9-form');
 if(!panel || !form || form.closest('.p-tabview-panel')!==panel) return null;
 const expectedForm=name==='L1-D'?'rshshr-citr-l1d-form':name==='L9'?'rshshr-citr-l9-form':'';
 if(form.localName!==expectedForm) return null;
 const roles={
  'rsh-citr-l1d-grid1':['L1-D','A. LAPORAN LABA RUGI'],
  'rsh-citr-l1d-grid2':['L1-D','B. LAPORAN POSISI KEUANGAN'],
  'rsh-citr-l1d-grid3':['L1-D','B. LAPORAN POSISI KEUANGAN'],
  'rshshr-citr-l9-form-grid1':['L9','HARTA BERWUJUD'],
  'rshshr-citr-l9-form-grid2':['L9','BANGUNAN'],
  'rshshr-citr-l9-form-grid3':['L9','HARTA TIDAK BERWUJUD']
 };
 const components=[],groups=[];
 for(let node=table.parentElement;node && node!==form;node=node.parentElement){
  if(roles[node.localName]) components.push(node.localName);
  if(!['p-panel','p-accordiontab'].includes(node.localName)) continue;
  let selector=node.localName==='p-panel'?'.p-panel-title':'.p-accordion-header-text';
  let headings=[...node.querySelectorAll(selector)].filter(e=>e.closest(node.localName)===node);
  if(!headings.length && node.localName==='p-accordiontab')
   headings=[...node.querySelectorAll('.p-accordion-header a')].filter(e=>e.closest('p-accordiontab')===node);
  if(headings.length!==1) return null;
  groups.unshift((headings[0].textContent||'').replace(/\s+/g,' ').trim());
 }
 if(components.length!==1) return null;
 const component=components[0], role=roles[component];
 if(role[0]!==name || groups[0]!==role[1]) return null;
 if(name==='L1-D' && groups.length!==1) return null;
 if(name==='L9'){
  const inner=component.endsWith('grid2')?['PERMANEN','TIDAK PERMANEN']:
   ['KELOMPOK 1','KELOMPOK 2','KELOMPOK 3','KELOMPOK 4','LAINNYA','KELOMPOK LAINNYA'];
  if(groups.length!==2 || !inner.includes(groups[1])) return null;
 }
 return {form:name,component,groups};
}'''


TABLE_JS = r'''(table) => {
 const value=CELL;
 const group=GROUP;
 const hrows=table.tHead ? [...table.tHead.rows].filter(r=>![...r.cells].some(c=>c.querySelector('p-columnfilter,input,select'))) : [];
 const matrix=[];
 hrows.forEach((tr,ri)=>{
  matrix[ri] ||= []; let ci=0;
  [...tr.cells].forEach(c=>{
   while(matrix[ri][ci]!==undefined)ci++;
   for(let r=ri;r<ri+(c.rowSpan||1);r++){
    matrix[r] ||= [];
    for(let x=ci;x<ci+(c.colSpan||1);x++)matrix[r][x]=value(c);
   }
   ci+=c.colSpan||1;
  });
 });
 const width=Math.max(0,...matrix.map(r=>r.length));
 const headers=Array.from({length:width},(_,i)=>[...new Set(matrix.map(r=>r[i]).filter(Boolean))].join(' / ')||`Kolom ${i+1}`);
 const bodyRows=[...table.tBodies].flatMap(b=>[...b.rows]).filter(r=>!r.classList.contains('p-datatable-emptymessage'))
 .filter(r=>!(r.cells.length===1 && r.cells[0].colSpan>1 && /tidak ada data|no records|no data/i.test(r.textContent)));
 const rows=bodyRows.map(r=>[...r.cells].map(value));
 const foot=table.tFoot ? [...table.tFoot.rows].map(r=>[...r.cells].map(value)) : [];
 const footer_spans=table.tFoot ? [...table.tFoot.rows].map(r=>[...r.cells].map(c=>c.colSpan||1)) : [];
 const caption=table.caption && table.caption.getClientRects().length ? table.caption.innerText.trim() : '';
 const result={headers,rows,footer:foot,footer_spans,group:caption||group(table)};
 const panel=table.closest('.p-tabview-panel'), form=table.closest('rshshr-citr-l8-form');
 const grid=table.closest('rsh-citr-l8-form-grid1');
 if(panel && form && grid && form.closest('.p-tabview-panel')===panel &&
    grid.closest('rshshr-citr-l8-form')===form &&
    panel.querySelectorAll('rshshr-citr-l8-form').length===1 &&
    form.querySelectorAll('rsh-citr-l8-form-grid1').length===1 &&
    form.querySelectorAll('table').length===1){
   // Raw cells and their positions come from the same owned-table snapshot.
   result.source_structure={form:'L8',component:'rsh-citr-l8-form-grid1',groups:[result.group]};
   result.body_spans=bodyRows.map(r=>[...r.cells].map(c=>c.colSpan));
   result.body_rowspans=bodyRows.map(r=>[...r.cells].map(c=>c.rowSpan));
 }
 return result;
}'''.replace('CELL', CELL_JS).replace('GROUP', GROUP_JS)

FIELDS_JS = r'''(root) => {
 const group=GROUP;
 const owner=root.closest('.p-tabview-panel');
 const visible=e=>!!e.getClientRects().length;
 const fields=[];
 const labelFor=e=>{
  let explicit=e.id ? root.querySelector('label[for="'+CSS.escape(e.id)+'"]') : null;
  if(explicit)return explicit.textContent.trim();
  let node=e;
  for(let n=0;n<7&&node&&node!==root;n++,node=node.parentElement){
   const labels=[...node.querySelectorAll('label')].filter(l=>visible(l));
   if(labels.length)return labels.map(l=>l.innerText.trim()).filter(Boolean).join(' / ');
  }
  return e.getAttribute('aria-label')||e.getAttribute('formcontrolname')||e.name||e.id||'Unnamed field';
 };
 const gridColumn=e=>{
  if(!e.closest('p-inputnumber'))return '';
  const cell=e.closest('.col-md-3');
  if(!cell || !cell.parentElement.matches('.row'))return '';
  const grid=cell.parentElement, columns=[...grid.children];
  if(columns.length!==4 || !columns.every(c=>c.matches('.col-md-3')&&visible(c)))return '';
  const amount=grid.parentElement, row=amount.parentElement;
  if(!amount.matches('.col-md-5') || !row.matches('.row') || !row.parentElement.matches('.p-accordion-content'))return '';
  // Match the explicit, same-container Bootstrap header grid, not the order
  // of populated inputs: omitted amount cells must retain their column.
  for(let prior=row.previousElementSibling;prior;prior=prior.previousElementSibling){
   if(!prior.matches('.row') || !visible(prior))continue;
   const header=prior.querySelector(':scope > .col-md-5 > .row');
   if(!header || header.querySelector('input,textarea,select'))continue;
   const cells=[...header.children];
   if(cells.length!==4 || !cells.every(c=>c.matches('.col-md-3')&&visible(c)))continue;
   const labels=cells.map(c=>(c.innerText||'').trim());
   if(labels.some(Boolean))return labels[columns.indexOf(cell)];
  }
  return '';
 };
 const context=e=>{
  const label=labelFor(e);
  const labels=[...e.parentElement.querySelectorAll(':scope > label')]
   .filter(l=>visible(l)&&l.innerText.trim()!==label&&!l.htmlFor);
  const result={};
  const heading=group(e);
  if(heading)result.group=heading;
  if(labels.length===1)result.column_label=labels[0].innerText.trim();
  else if(!labels.length){
   const column=gridColumn(e);
   if(column)result.column_label=column;
  }
  return result;
 };
 const include=e=>e.closest('.p-tabview-panel')===owner && !e.closest('table') && !e.closest('[hidden],[aria-hidden="true"]');
 [...root.querySelectorAll('input:not([type=password]):not([type=hidden]),textarea,select')].filter(include).forEach(e=>{
  if(e.getAttribute('role')==='combobox')return;
  if(e.type==='radio'||e.type==='checkbox'){
   const control=e.closest('p-radiobutton,p-checkbox')||e;
   if(!visible(control))return;
   if(e.type==='radio'&&!e.checked&&e.getAttribute('aria-checked')!=='true')return;
   // PrimeNG may keep the AskedTo binding on the wrapper, not its input.
   const askedTo=e.type==='radio'&&control.getAttribute('formcontrolname')==='AskedTo';
   const field=e.name||e.getAttribute('formcontrolname')||(askedTo?'AskedTo':e.id);
   fields.push({...context(e),label:labelFor(e),field,value:e.type==='checkbox'?String(e.checked):e.value});
  }else if(visible(e))fields.push({...context(e),label:labelFor(e),field:e.getAttribute('formcontrolname')||e.name||e.id,value:e.tagName==='SELECT'?[...e.selectedOptions].map(o=>o.textContent).join(', '):e.value});
 });
 [...root.querySelectorAll('p-dropdown,p-multiselect')].filter(include).filter(visible).forEach(e=>{
  fields.push({...context(e),label:labelFor(e),field:e.getAttribute('formcontrolname')||e.id,value:e.querySelector('.p-dropdown-label,.p-multiselect-label')?.textContent.trim()||''});
 });
 return fields;
}'''.replace('GROUP', GROUP_JS)

STATE_JS = "(e)=>JSON.stringify({p:[...e.querySelectorAll('.p-paginator-page.p-highlight')].map(x=>x.textContent.trim()),rows:[...e.querySelectorAll('tbody tr')].map(x=>x.innerText)})"


class CaptureCancelled(KeyboardInterrupt):
    """Lewati penanganan Exception per SPT agar Stop tetap menghasilkan PARTIAL."""


def _check_cancel(check_cancel):
    if check_cancel:
        check_cancel()


def wait_idle(page):
    page.locator('.p-datatable-loading-overlay:visible,.p-blockui:visible').first.wait_for(state='hidden', timeout=45000)
    page.wait_for_timeout(180)


def maximize_page_size(page, container):
    """Choose the largest inspected size up to 100; report an actual change."""
    total = container.query_selector('.p-paginator-current')
    if total and re.search(r'(?:dari|of)\s+0\s', total.inner_text(), re.I):
        return False
    trigger = container.query_selector('.p-paginator .p-dropdown-trigger')
    if not trigger:
        return False
    trigger.evaluate('(e)=>e.click()')
    options = page.locator('.p-dropdown-items li:visible')
    options.first.wait_for(state='visible', timeout=5000)
    numeric = [(int(text.strip()), i) for i, text in enumerate(options.all_inner_texts()) if text.strip().isdigit() and int(text.strip()) <= 100]
    if numeric:
        maximum, index = max(numeric)
        current = container.query_selector('.p-paginator-rpp-options .p-dropdown-label')
        if current and current.inner_text().strip() == str(maximum):
            # Re-selecting the same option can trigger another server load.
            page.keyboard.press('Escape')
            return False
        options.nth(index).evaluate('(e)=>e.click()')
        wait_idle(page)
        return True
    else:
        page.keyboard.press('Escape')
    return False


def _click_table_paginator(control, container, check_cancel):
    _check_cancel(check_cancel)
    # Only inspected read-only pagination may bypass pointer interception by
    # sticky headers. Hidden/disabled/detached or foreign controls still fail closed.
    clicked = control.evaluate("""(e, owner) => {
        const actual = e.closest('p-table') || e.closest('.p-datatable') || e.parentElement;
        const style = getComputedStyle(e);
        if (!e.isConnected || actual !== owner || !e.matches(
            '.p-paginator-first,.p-paginator-prev,.p-paginator-next') ||
            e.matches(':disabled,[disabled],.p-disabled') ||
            e.closest('[aria-disabled="true"]') || !e.getClientRects().length ||
            style.visibility === 'hidden' || style.visibility === 'collapse') return false;
        e.click();
        return true;
    }""", container)
    if clicked is not True:
        raise RuntimeError('Unavailable or unsupported pagination control')


def capture_table(page, table, ordinal, max_pages, check_cancel=None):
    """Baca seluruh halaman tabel dan rekonsiliasi jumlah baris sebelum footer."""
    _check_cancel(check_cancel)
    handle = table.element_handle()
    container_handle = handle.evaluate_handle("e=>e.closest('p-table')||e.closest('.p-datatable')||e.parentElement")
    maximize_page_size(page, container_handle)
    first = container_handle.query_selector('.p-paginator-first:not([disabled]):not(.p-disabled)')
    if first:
        _click_table_paginator(first, container_handle, check_cancel)
        wait_idle(page)
    # Sebagian tabel menyimpan halaman terakhir dan hanya menyediakan Prev.
    previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
    for _ in range(max_pages):
        _check_cancel(check_cancel)
        previous = container_handle.query_selector(previous_selector)
        if not previous:
            break
        state = container_handle.evaluate(STATE_JS)
        _click_table_paginator(previous, container_handle, check_cancel)
        wait_idle(page)
        if container_handle.evaluate(STATE_JS) == state:
            raise RuntimeError('Table pagination did not return to the first page')
    if container_handle.query_selector(previous_selector):
        raise RuntimeError(f'Table reset page limit {max_pages} reached')
    result = table.evaluate(TABLE_JS)
    result.update(name=f'Tabel {ordinal}', pages=1, complete=True)
    next_selector = '.p-paginator-next:not([disabled]):not(.p-disabled)'
    seen = set()
    while container_handle.query_selector(next_selector):
        _check_cancel(check_cancel)
        if result['pages'] >= max_pages:
            result['complete'] = False
            result['warning'] = f'Table page limit {max_pages} reached'
            break
        state = container_handle.evaluate(STATE_JS)
        if state in seen:
            result['complete'] = False
            result['warning'] = 'Repeated table pagination state'
            break
        seen.add(state)
        _click_table_paginator(container_handle.query_selector(next_selector), container_handle, check_cancel)
        deadline = time.monotonic() + 30
        while container_handle.evaluate(STATE_JS) == state:
            _check_cancel(check_cancel)
            if time.monotonic() >= deadline:
                result['complete'] = False
                result['warning'] = 'Table pagination did not advance'
                break
            page.wait_for_timeout(120)
        if not result['complete']:
            break
        wait_idle(page)
        if container_handle.evaluate(STATE_JS) in seen:
            result['complete'] = False
            result['warning'] = 'Repeated table pagination state'
            break
        data = table.evaluate(TABLE_JS)
        result['rows'].extend(data['rows'])
        if 'body_spans' in result:
            if (any(data.get(key) != result.get(key) for key in ('source_structure', 'headers', 'group'))
                    or not isinstance(data.get('body_spans'), list)
                    or not isinstance(data.get('body_rowspans'), list)):
                result['complete'] = False
                result['warning'] = 'Table structural identity changed during pagination'
            else:
                result['body_spans'].extend(data['body_spans'])
                result['body_rowspans'].extend(data['body_rowspans'])
        result['footer'] = data.get('footer', [])
        result['footer_spans'] = data.get('footer_spans', [])
        result['pages'] += 1
        if not result['complete']:
            break
    # Cocokkan baris isi dengan jumlah yang dinyatakan aplikasi bila tersedia.
    total_element = container_handle.query_selector('.p-paginator-current')
    if total_element:
        match = re.search(r'(?:dari|of)\s+([0-9.,]+)', total_element.inner_text(), re.I)
        if match:
            result['source_total'] = int(re.sub(r'[^0-9]', '', match.group(1)))
            if len(result['rows']) != result['source_total']:
                result['complete'] = False
                result['warning'] = f"Source count {result['source_total']} != captured rows {len(result['rows'])}"
    # Total sumber sering ada di tfoot; masukkan sekali setelah paginasi selesai.
    result['body_row_count'] = len(result['rows'])
    result['rows'].extend(result.get('footer', []))
    container_handle.dispose()
    return result


def _list_paginator(container, selector):
    button = container.query_selector(selector)
    if button is None:
        return None
    enabled = button.evaluate("""(e, owner) => {
        const actual=e.closest('p-table')||e.closest('.p-datatable')||e.parentElement;
        return e.isConnected && actual===owner && !!e.getClientRects().length &&
            !e.closest(':disabled,[disabled],.p-disabled,[aria-disabled="true"],[hidden],[aria-hidden="true"]') &&
            !['hidden','collapse'].includes(getComputedStyle(e).visibility);
    }""", container)
    if enabled is not True:
        button.dispose()
        return None
    return button


DETAIL_READY_TIMEOUT = 30
DETAIL_PANEL_TIMEOUT = 30
_PPN_FORMS = {'INDUK', 'A1', 'A2', 'B1', 'B2', 'B3', 'C'}


PANEL_TIMEOUT_JS = r"""(view, panelId) => {
    const doc = view.ownerDocument;
    const controlled = Boolean(panelId);
    const result = {panel_controlled: controlled,
        tab_views: doc.querySelectorAll('.main-content .p-tabview').length};
    let matches;
    if (controlled) {
        const selector = '#' + CSS.escape(panelId);
        matches = view.querySelectorAll(selector);
        result.document_panel_matches = doc.querySelectorAll(selector).length;
    } else {
        matches = view.querySelectorAll(':scope > .p-tabview-panels > .p-tabview-panel:not([hidden]), :scope > .p-tabview-panels > p-tabpanel > .p-tabview-panel:not([hidden])');
    }
    matches = [...matches].filter(panel => panel.closest('.p-tabview') === view);
    result.panel_matches = matches.length;
    const tabs = [...view.querySelectorAll('.p-tabview-nav a')].filter(tab =>
        tab.closest('.p-tabview') === view && (controlled ?
            tab.getAttribute('aria-controls') === panelId : tab.getAttribute('aria-selected') === 'true'));
    const selected = tabs.length === 1 ? tabs[0].getAttribute('aria-selected') : null;
    result.tab_state = selected === 'true' ? 'selected' : selected === 'false' ? 'unselected' : 'unknown';
    if (!matches.length) {
        result.panel_state = controlled && result.document_panel_matches ? 'outside_view' : 'missing';
    } else if (matches.length > 1) {
        result.panel_state = 'ambiguous';
    } else {
        const style = getComputedStyle(matches[0]);
        const box = matches[0].getBoundingClientRect();
        result.panel_state = !['hidden', 'collapse'].includes(style.visibility) &&
            box.width > 0 && box.height > 0 ? 'visible' : 'hidden';
    }
    return result;
}"""


def _record_panel_timeout(view, panel_id, duration_ms):
    # A snapshot is evidence after exhaustion, never permission to capture a
    # hidden/foreign panel. Keep the original timeout even if this read fails.
    fields = {'panel_state': 'unavailable', 'panel_controlled': bool(panel_id)}
    try:
        snapshot = view.evaluate(PANEL_TIMEOUT_JS, panel_id, timeout=1000)
        if type(snapshot) is dict:
            fields.update({key: snapshot[key] for key in (
                'panel_state', 'tab_state', 'panel_matches', 'document_panel_matches', 'tab_views'
            ) if key in snapshot})
    except Exception as exc:
        fields.update(probe_failure='evaluation_error', error=exc)
    diagnostics.record('capture.panel_timeout', level='WARNING',
                       duration_ms=duration_ms, **fields)


def _wait_tab_panel(view, tab, caption, check_cancel, *, initial_panel_id=None):
    """Follow a changing control binding without extending the panel budget."""
    started = time.monotonic()
    deadline = started + DETAIL_PANEL_TIMEOUT
    panel_id = initial_panel_id
    controlled = initial_panel_id is not None

    def read_timeout():
        # A busy Induk can take more than 100 ms to resolve a locator. Give
        # each read a bounded slice of the SAME deadline, with Stop between
        # reads; never pass zero (which disables Playwright's timeout).
        _check_cancel(check_cancel)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PlaywrightTimeoutError('Timeout waiting for tab panel: readiness deadline exhausted')
        return min(1000, max(1, int(remaining * 1000)))

    while True:
        _check_cancel(check_cancel)
        try:
            if tab.inner_text(timeout=read_timeout()).strip() != caption:
                raise RuntimeError('Tab identity changed while waiting for its panel')
            current_id = tab.get_attribute('aria-controls', timeout=read_timeout())
            if controlled and not current_id:
                # A rebinding gap must never authorize the previous form.
                raise PlaywrightTimeoutError('Controlled tab has no current panel binding')
            panel_id = current_id
            if panel_id:
                controlled = True
                panel = view.locator('[id=' + repr(panel_id) + ']')
            else:
                panel = view.locator(':scope > .p-tabview-panels > .p-tabview-panel:not([hidden]):visible, :scope > .p-tabview-panels > p-tabpanel > .p-tabview-panel:not([hidden]):visible')
            panel.wait_for(state='visible', timeout=read_timeout())
            _check_cancel(check_cancel)
            owner = view.element_handle(timeout=read_timeout())
            try:
                belongs = '(e, owner) => e.isConnected && owner.isConnected && e.closest(".p-tabview") === owner'
                if not panel.evaluate(belongs, owner, timeout=read_timeout()):
                    raise PlaywrightTimeoutError('Controlled panel is outside its owning tab view')
                # nth() is live: validate its caption, owner and binding together
                # after readiness so a reordered tab cannot relabel this panel.
                if not tab.evaluate('''(e, expected) => e.isConnected && expected.owner.isConnected &&
                        e.closest('.p-tabview') === expected.owner &&
                        e.innerText.trim() === expected.caption &&
                        e.getAttribute('aria-controls') === expected.panel_id''',
                        {'owner': owner, 'caption': caption, 'panel_id': panel_id}, timeout=read_timeout()):
                    raise PlaywrightTimeoutError('Tab identity or panel binding did not stabilize')
            finally:
                owner.dispose()
            read_timeout()  # A successful final read must not outlive the budget.
            return panel
        except PlaywrightTimeoutError:
            if time.monotonic() >= deadline:
                _check_cancel(check_cancel)
                _record_panel_timeout(view, panel_id, (time.monotonic() - started) * 1000)
                raise


def _ppn_catalog_ready(page, check_cancel=None):
    # Tab visibility is value-free readiness evidence. Initial Angular shells
    # can expose default zero fields before the return's appendices appear.
    deadline = time.monotonic() + DETAIL_READY_TIMEOUT
    while True:
        _check_cancel(check_cancel)
        view = page.locator('.main-content .p-tabview').first
        if view.count():
            names = view.evaluate(r"""view => [...view.querySelectorAll('.p-tabview-nav a[role=tab]')]
                .filter(e=>e.closest('.p-tabview')===view && e.getClientRects().length &&
                    !e.closest('[disabled],.p-disabled,[aria-disabled="true"],[hidden],[aria-hidden="true"]'))
                .map(e=>(e.textContent||'').trim().toUpperCase().replace(/[-\s]/g,''))""")
            if len(names) == len(_PPN_FORMS) and set(names) == _PPN_FORMS:
                return True
        if time.monotonic() >= deadline:
            return False
        page.wait_for_timeout(100)


@diagnostics.traced('detail')
def capture_detail(page, max_pages=1000, check_cancel=None, *, record=None, folder=None):
    """Baca panel, field, dan tabel yang didukung; layout tak dikenal tetap parsial."""
    _check_cancel(check_cancel)
    with diagnostics.measure('panel_ready', form_ordinal=1):
        page.locator('.main-content').wait_for(timeout=45000)
        wait_idle(page)
    root = page.locator('.main-content').first
    sections = []
    errors = []
    attachments = []
    financial_required = record is not None and record['meta'].get('Jenis Pajak') == 'PPh Badan'
    financial_attempted = False
    ppn = record is not None and record['meta'].get('Jenis Pajak') == 'PPN'
    if ppn and not _ppn_catalog_ready(page, check_cancel):
        errors.append({'object': 'SPT detail', 'message': 'PPN form catalog is not ready or incomplete'})

    def capture_panel(panel, name):
        nonlocal financial_attempted
        # Accordion hanya membuka isi; jangan klik tombol aksi yang belum dikenali.
        with diagnostics.measure('accordion_expand', form_ordinal=len(sections) + 1):
            expanders = panel.locator('.p-accordion-header a[aria-expanded=false]').element_handles()
            try:
                for expander in expanders:
                    _check_cancel(check_cancel)
                    expander.evaluate('(e)=>e.click()')
            finally:
                for expander in expanders:
                    expander.dispose()
            wait_idle(page)
        if panel.locator('.p-accordion-header a[aria-expanded=false]').count():
            errors.append({'object': name, 'message': 'Some accordion sections remain collapsed; their content could not be fully captured'})
        with diagnostics.measure('panel_extract', form_ordinal=len(sections) + 1):
            section = {'name': name, 'fields': panel.evaluate(FIELDS_JS), 'text': panel.inner_text(), 'tables': []}
        tables = panel.locator('table')
        for i in range(tables.count()):
            _check_cancel(check_cancel)
            table = tables.nth(i)
            if not table.is_visible():
                continue
            belongs = table.evaluate('(e)=>e.closest(\".p-tabview-panel\")?.id||\"\"')
            owner = panel.evaluate('(e)=>e.closest(\".p-tabview-panel\")?.id||\"\"')
            if belongs != owner:
                continue
            try:
                with diagnostics.measure('table', form_ordinal=len(sections) + 1, table_ordinal=i + 1) as timing:
                    captured = capture_table(page, table, i + 1, max_pages, check_cancel=check_cancel)
                    timing.update(body_rows=captured.get('body_row_count'), pages=captured.get('pages'),
                                  status='COMPLETE' if captured['complete'] else 'PARTIAL')
                if financial_required and name in ('L1-D', 'L9'):
                    structure = table.evaluate(CORPORATE_STRUCTURE_JS, name)
                    if structure:
                        captured['source_structure'] = structure
                section['tables'].append(captured)
                if not captured['complete']:
                    errors.append({'object': name, 'message': captured['warning']})
            except Exception as exc:
                diagnostics.record('capture.partial', level='WARNING', error=exc)
                errors.append({'object': f'{name}/table {i+1}', 'message': str(exc).split('\n')[0]})
        sections.append(section)
        # Another form hides Induk; read its inspected href before traversal advances.
        if financial_required and not financial_attempted and name.rsplit(' / ', 1)[-1] == 'Induk':
            from coretax_attachments import download_financial_attachments
            financial_attempted = True
            captured_attachments = download_financial_attachments(page, record, folder, check_cancel=check_cancel)
            _check_cancel(check_cancel)
            attachments.extend(captured_attachments)
            for attachment in captured_attachments:
                if attachment['status'] != 'COMPLETE':
                    errors.append({'object': name + '/' + attachment['label'],
                                   'message': 'Financial PDF control is unsupported or download incomplete'})
        nested = panel.locator('.p-tabview')
        if nested.count():
            visit_view(nested.first, name + ' / ')

    def visit_view(view, prefix=''):
        tabs = view.locator(':scope > .p-tabview-nav-container > .p-tabview-nav-content > .p-tabview-nav > li > a[role=tab]')
        if not tabs.count():
            tabs = view.locator(':scope > .p-tabview-nav > li > a[role=tab]')
        # Pembungkus navigasi PrimeNG berbeda; batasi fallback pada view ini.
        if not tabs.count():
            tabs = view.locator('.p-tabview-nav > li > a[role=tab]')
        count = tabs.count()
        if not count:
            raise RuntimeError('No supported tab controls found')
        for i in range(count):
            _check_cancel(check_cancel)
            name = prefix + 'Tab ' + str(i + 1)
            try:
                tab = tabs.nth(i)
                if tab.evaluate('(e)=>e.closest(\"li\").classList.contains(\"p-disabled\")||e.getAttribute(\"aria-disabled\")===\"true\"'):
                    continue
                caption = tab.inner_text().strip()
                name = prefix + caption
                with diagnostics.measure('panel_ready', form_ordinal=len(sections) + 1):
                    tab.evaluate('(e)=>e.click()')
                    wait_idle(page)
                    panel = _wait_tab_panel(view, tab, caption, check_cancel)
                _check_cancel(check_cancel)
                capture_panel(panel, name)
            except Exception as exc:
                diagnostics.record('capture.partial', level='WARNING', error=exc)
                errors.append({'object': name, 'message': str(exc).split('\n')[0]})

    view = root.locator('.p-tabview').first
    try:
        if view.count():
            visit_view(view)
        else:
            capture_panel(root, 'Halaman SPT')
    except Exception as exc:
        diagnostics.record('capture.partial', level='WARNING', error=exc)
        errors.append({'object': 'SPT detail', 'message': str(exc).split('\n')[0]})
    if financial_required and not financial_attempted:
        attachments.append({'label': 'Laporan Keuangan', 'relative_path': None,
                            'status': 'PARTIAL', 'bytes': 0, 'hash': None})
        errors.append({'object': 'Induk/Laporan Keuangan',
                       'message': 'No inspected corporate Induk found; financial PDF capture unsupported'})
    if ppn:
        captured_forms = [re.sub(r'[-\s]', '', s['name'].upper()) for s in sections]
        if len(captured_forms) != len(_PPN_FORMS) or set(captured_forms) != _PPN_FORMS:
            errors.append({'object': 'SPT detail', 'message': 'PPN form traversal is incomplete'})
    meaningful = any(s['fields'] or s['tables'] for s in sections)
    if not meaningful:
        errors.append({'object': 'SPT detail', 'message': 'No structured fields or tables captured; unsupported detail layout'})
    return {'sections': sections, 'capture_complete': meaningful and not errors,
            'errors': errors, 'attachments': attachments}


ORIGIN = 'https://coretax.intranet.pajak.go.id'
SEARCH_URL = ORIGIN + '/returnsheets/id-ID/taxpayer-search'


def trusted_origin(url):
    """Periksa origin HTTPS lengkap sebelum menerima navigasi atau respons."""
    if not isinstance(url, str) or url != url.strip() or '\\' in url or any(ord(c) < 32 for c in url):
        return False
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and parsed.hostname == urlparse(ORIGIN).hostname
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


def list_taxpayer_id(url):
    if not trusted_origin(url):
        raise RuntimeError('Return list is outside the authorized Coretax HTTPS origin')
    match = re.fullmatch(r'/returnsheets/id-ID/[^/]*returnsheets/([^/]+)/?', urlparse(url).path)
    if not match:
        raise RuntimeError('Unsupported return-list URL; taxpayer provenance cannot be verified')
    return match.group(1)


def verify_detail_url(url, taxpayer_id, record_id=None):
    """Tautkan URL detail dengan wajib pajak dan identitas SPT dari inventaris."""
    if not trusted_origin(url) or not urlparse(url).path.startswith('/returnsheets/'):
        raise RuntimeError('View redirected outside the authorized Coretax return pages; login may have expired')
    segments = urlparse(url).path.split('/')
    if taxpayer_id not in segments:
        raise RuntimeError('Return URL does not identify the selected taxpayer; provenance cannot be verified')
    if record_id is not None and record_id not in segments:
        raise RuntimeError('Return URL does not identify the selected SPT record; provenance cannot be verified')


class ListObserver:
    """Keep one owned response/byte buffer and a monotonic freshness marker."""
    def __init__(self, page, check_cancel=None):
        self.page = page
        self.check_cancel = check_cancel
        self.sequence = 0
        self.latest = None
        self.request_filter = None
        page.on('response', self.on_response)

    def on_response(self, response):
        request = response.request
        if (not trusted_origin(response.url) or not urlparse(response.url).path.startswith('/returnsheet/api/returnsheets')
                or request.resource_type not in ('xhr', 'fetch')):
            return
        if 'json' not in response.headers.get('content-type', '').lower():
            return
        try:
            frame = getattr(request, 'frame', None)
            main_frame = getattr(self.page, 'main_frame', None)
            if frame is not None and main_frame is not None and frame != main_frame:
                return
            posted = getattr(request, 'post_data_json', None)
            if request.method != 'POST' or not isinstance(posted, dict):
                return
            taxpayer = posted.get('TaxpayerAggregateIdentifier')
            first, size = posted.get('First'), posted.get('Rows')
            # Identity-only auxiliary reads share the list endpoint and envelope,
            # but cannot describe the visible grid or satisfy a fresh-page wait.
            if (not isinstance(taxpayer, str) or not taxpayer
                    or type(first) is not int or first < 0
                    or type(size) is not int or size < 1 or first % size
                    or not isinstance(posted.get('Filters'), list)):
                return
            body_reader = getattr(response, 'body', None)
            body = body_reader() if callable(body_reader) else None
            data = json.loads(body) if isinstance(body, bytes) else response.json()
            if not isinstance(data, dict):
                return
            payload = data.get('Payload', data.get('payload', {}))
            if not isinstance(payload, dict):
                return
            rows, total = payload.get('Data'), payload.get('TotalRecords')
            if rows is None and type(total) is int and total == 0:
                rows = []
            if not (isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
                    and type(total) is int and total >= 0):
                return
            binding = None
            if isinstance(body, bytes) and urlparse(response.url).path == SUBMITTED_ENDPOINT:
                rewrite = None
                if self.request_filter is not None:
                    posted, rewrite = self.request_filter.effective_binding(request)
                keys = ('TaxpayerAggregateIdentifier', 'First', 'Rows', 'Filters',
                        'isArchieved', 'LanguageId', 'SortField', 'SortOrder')
                binding = {
                    'response_url': response.url, 'method': getattr(request, 'method', None),
                    'http_status': response.status, 'frame_url': getattr(frame, 'url', None),
                    'request': {key: posted[key] for key in keys if key in posted} if isinstance(posted, dict) else None,
                }
                if rewrite is not None:
                    binding['filter_rewrite'] = rewrite
            self.sequence += 1
            self.latest = {'total': total, 'rows': rows, 'body': body, 'binding': binding,
                           'sequence': self.sequence, 'first': posted['First'], 'page_size': posted['Rows'],
                           'successful': 200 <= response.status < 300
                           and data.get('IsSuccessful', data.get('isSuccessful')) is True}
        except Exception as exc:
            if self.request_filter is not None and isinstance(exc, JsonSafetyError):
                self.request_filter.error = exc
            # An unreadable response cannot replace the last verified event.
            # wait(after) still requires a newer usable event or fails closed.
            pass

    def wait(self, after, timeout=45):
        deadline = time.monotonic() + timeout
        while self.sequence <= after:
            _check_cancel(self.check_cancel)
            if self.request_filter is not None and self.request_filter.error:
                raise self.request_filter.error
            if time.monotonic() >= deadline:
                raise RuntimeError('No verifiable return-list response. Login expired, access denied, or list API layout changed.')
            self.page.wait_for_timeout(100)
        _check_cancel(self.check_cancel)
        wait_idle(self.page)
        if self.request_filter is not None and self.request_filter.error:
            raise self.request_filter.error
        result = self.latest
        if not result['successful']:
            raise RuntimeError('Coretax reported an unsuccessful return-list request')
        return {**result, 'after_sequence': after}

    def close(self):
        self.page.remove_listener('response', self.on_response)
        self.latest = None


REFERENCE_ROWS_JS = r'''(table) => {
 const value=CELL;
 const headerRows=table.tHead ? [...table.tHead.rows].filter(r=>![...r.cells].some(c=>c.querySelector('p-columnfilter,input,select'))) : [];
 if(headerRows.length!==1 || [...headerRows[0].cells].some(c=>c.colSpan!==1||c.rowSpan!==1))return {supported:false};
 const headers=[...headerRows[0].cells].map(value);
 const wanted=['Jenis Pajak','Jenis Surat Pemberitahuan Pajak','Masa Pajak','Status SPT','Kanal','Model SPT'];
 if(wanted.some(h=>headers.filter(v=>v===h).length!==1))return {supported:false};
 const rows=[...table.tBodies].flatMap(b=>[...b.rows]).filter(r=>!r.classList.contains('p-datatable-emptymessage'))
 .filter(r=>!(r.cells.length===1&&r.cells[0].colSpan>1&&/tidak ada data|no records|no data/i.test(r.textContent)));
 return {supported:true,rows:rows.map(row=>Object.fromEntries(wanted.map(h=>[h,value(row.cells[headers.indexOf(h)])])))};
}'''.replace('CELL', CELL_JS)


def _inventory_context(response, source, taxpayer_id, npwp, year, basis, page_number):
    """Bind a response for the same pure safety probe in readiness and capture."""
    if not isinstance(response.get('binding'), dict):
        raise JsonSafetyError('Submitted response lacks verified request/frame/source binding')
    return {
        **response['binding'], 'npwp': npwp, 'year': year, 'year_basis': basis,
        'taxpayer_id': taxpayer_id, 'source_url': source['url'], 'source_status': source['label'],
        'page': page_number, 'sequence': response['sequence'], 'after_sequence': response['after_sequence'],
        'date_format': 'dd-MM-yyyy', 'timezone': None, 'lookup_labels': {},
    }


def _inventory_metadata(page, table, response, source, taxpayer_id, npwp, year, basis,
                        page_number, folder, source_number, check_cancel):
    """Adapt a bound submitted page; read only reference captions, not its grid."""
    _check_cancel(check_cancel)
    validate_inventory_rows(response['rows'], taxpayer_id)
    submitted = urlparse(source['url']).path.startswith('/returnsheets/id-ID/submitted-returnsheets/')
    if not submitted:
        return {'eligible': False, 'reason': 'unobserved_status_schema', 'rows': []}
    if not isinstance(response.get('body'), bytes):
        return {'eligible': False, 'reason': 'unavailable_original_response_bytes', 'rows': []}
    context = _inventory_context(response, source, taxpayer_id, npwp, year, basis, page_number)
    # Safety is evaluated before even the narrow reference read or fallback.
    probe = adapt_inventory_page(response['body'], context)
    raw_folder = folder / 'listing-responses'
    raw_folder.mkdir(exist_ok=True)
    raw_name = f'{source_number:04d}-{page_number:04d}-{response["sequence"]:08d}.json'
    with (raw_folder / raw_name).open('xb') as handle:
        handle.write(response['body'])
    _check_cancel(check_cancel)
    if not response['rows']:
        return probe
    # Only annual corporate codes have an observed native metadata contract.
    if any(row.get('TaxTypeCode') != 'ICT_RCIT' or row.get('ReturnSheetTypeCode') != 'ICT_RCITR'
           for row in response['rows']):
        return {'eligible': False, 'reason': 'unobserved_tax_metadata_schema', 'rows': []}
    references = table.evaluate(REFERENCE_ROWS_JS)
    if not references.get('supported'):
        return {'eligible': False, 'reason': 'unsupported_reference_layout', 'rows': []}
    if len(references['rows']) != len(response['rows']):
        raise JsonSafetyError('Reference DOM rows contradict source count')
    labels = {field: {} for field in LOOKUP_HEADERS}
    verified_labels = {'TaxTypeCode': ('ICT_RCIT', 'PPh Badan'),
                       'ReturnSheetTypeCode': ('ICT_RCITR', 'SPT PPh Badan Rupiah'),
                       'ReturnSheetStatusCode': ('SUBMITTED', 'Dilaporkan'),
                       'ChannelCode': ('TAXPAYER_PORTAL', 'Portal Wajib Pajak')}
    for api_row, captions in zip(response['rows'], references['rows']):
        _check_cancel(check_cancel)
        if 'ReturnSheetModel' in api_row and captions['Model SPT'] != api_row['ReturnSheetModel']:
            raise JsonSafetyError('Reference row order/model differs from source identity')
        period = api_row.get('TaxPeriodCode')
        if not isinstance(period, str) or not re.fullmatch(r'0112\d{4}', period):
            return {'eligible': False, 'reason': 'unobserved_period_schema', 'rows': []}
        if captions['Masa Pajak'] != 'Januari - Desember ' + period[-4:]:
            raise JsonSafetyError('Period reference caption contradicts source code')
        for field, header in LOOKUP_HEADERS.items():
            code = api_row.get(field)
            caption = captions[header]
            if not isinstance(code, str) or not caption:
                return {'eligible': False, 'reason': 'unsupported_reference_code', 'rows': []}
            if field in verified_labels and code == verified_labels[field][0] and caption != verified_labels[field][1]:
                return {'eligible': False, 'reason': 'unsupported_reference_locale', 'rows': []}
            if code in labels[field] and labels[field][code] != caption:
                raise JsonSafetyError('Conflicting captions for a source reference code')
            labels[field][code] = caption
    context['lookup_labels'] = labels
    context['timezone'] = page.evaluate('() => Intl.DateTimeFormat().resolvedOptions().timeZone')
    _check_cancel(check_cancel)
    result = adapt_inventory_page(response['body'], context)
    for row in result['rows']:
        row['source_identity']['body_file'] = 'listing-responses/' + raw_name
        row['source_identity']['rendering'] = {'date_format': context['date_format'], 'timezone': context['timezone'],
                                             'reference_source': 'bound-current-grid-reference-cells'}
    return result


SEARCH_RESULT_TIMEOUT_MS = 45000


class TaxpayerSearchTimeout(PlaywrightTimeoutError):
    """Owned desktop hint built only from fixed reasons, never exception text."""
    _HINTS = {
        'unavailable': 'Pengamatan jaringan tidak tersedia.',
        'http_401': 'Teramati HTTP 401 pada aktivitas browser selama pencarian.',
        'http_403': 'Teramati HTTP 403 pada aktivitas browser selama pencarian.',
        'http_429': 'Teramati HTTP 429 pada aktivitas browser selama pencarian.',
        'http_5xx': 'Teramati respons HTTP 5xx pada aktivitas browser selama pencarian.',
        'transport': 'Teramati kegagalan transport jaringan selama pencarian.',
        'no_traffic': 'Tidak ada XHR/fetch baru dalam scope pengamatan yang teramati.',
        'unverified': 'Aktivitas browser teramati, tetapi hasil belum terverifikasi.',
    }

    def __init__(self, reason='unverified', *, limited=False):
        self._reason = reason if type(reason) is str and reason in self._HINTS else 'unverified'
        self._limited = limited if type(limited) is bool else False
        super().__init__(self.public_message)

    @property
    def public_message(self):
        hint = self._HINTS[self._reason]
        if self._limited:
            hint += ' Pengamatan terbatas.'
        return ('Pencarian NPWP belum menghasilkan satu baris yang terverifikasi. ' + hint +
                ' Periksa pesan portal; pengamatan ini belum menentukan penyebab kegagalan.')


class _SearchDiagnostics:
    """Bounded passive metadata; never read request headers/body or response text."""
    def __init__(self, page):
        self.page = page
        self.started = time.monotonic()
        self.observation = 'complete'
        self.active = True
        self.tracked = {}
        self.listeners = []
        self.counts = dict.fromkeys(('search_requests', 'search_responses', 'search_failed',
            'search_http_1xx', 'search_http_2xx', 'search_http_3xx', 'search_http_4xx',
            'search_http_5xx', 'search_http_401', 'search_http_403', 'search_http_429'), 0)

    def __enter__(self):
        for event, handler in (('request', self._request), ('response', self._response),
                               ('requestfailed', self._failed)):
            try:
                self.page.on(event, handler)
                self.listeners.append((event, handler))
            except Exception:
                self.observation = 'unavailable'
        return self

    def _request(self, request):
        if not self.active:
            return
        try:
            if (request.resource_type not in ('xhr', 'fetch')
                    or request.frame != self.page.main_frame
                    or not trusted_origin(request.url)
                    or not trusted_origin(self.page.url)
                    or urlparse(self.page.url).path != urlparse(SEARCH_URL).path):
                return
            key = id(request)
            if key in self.tracked:
                return
            if len(self.tracked) >= 128:
                if self.observation != 'unavailable':
                    self.observation = 'limited'
                return
            # Retain only bounded handles/flags for event identity, never copies
            # of their private request material. Clear them on every exit.
            self.tracked[key] = [request, 0]
            self.counts['search_requests'] += 1
        except Exception:
            self.observation = 'unavailable'

    def _response(self, response):
        if not self.active:
            return
        try:
            request = response.request
            entry = self.tracked.get(id(request))
            if entry is None or entry[0] is not request or entry[1] & 1:
                return
            status = response.status
            if type(status) is not int or not 100 <= status <= 599:
                self.observation = 'unavailable'
                return
            entry[1] |= 1
            self.counts['search_responses'] += 1
            self.counts[f'search_http_{status // 100}xx'] += 1
            if status in (401, 403, 429):
                self.counts[f'search_http_{status}'] += 1
        except Exception:
            self.observation = 'unavailable'

    def _failed(self, request):
        if not self.active:
            return
        try:
            entry = self.tracked.get(id(request))
            if entry is not None and entry[0] is request and not entry[1] & 2:
                entry[1] |= 2
                self.counts['search_failed'] += 1
        except Exception:
            self.observation = 'unavailable'

    def timeout_error(self):
        if self.observation == 'unavailable':
            reason = 'unavailable'
        else:
            # Prefer the most actionable hint; the event retains every count.
            code = next((code for code in (429, 403, 401) if self.counts[f'search_http_{code}']), None)
            if code is not None:
                reason = f'http_{code}'
            elif self.counts['search_http_5xx']:
                reason = 'http_5xx'
            elif self.counts['search_failed']:
                reason = 'transport'
            elif not self.counts['search_requests']:
                reason = 'no_traffic'
            else:
                reason = 'unverified'
        return TaxpayerSearchTimeout(reason, limited=self.observation == 'limited')

    def __exit__(self, exc_type, exc, traceback):
        self.active = False
        duration = (time.monotonic() - self.started) * 1000
        for event, handler in self.listeners:
            try:
                self.page.remove_listener(event, handler)
            except Exception:
                self.observation = 'unavailable'
        cancelled = exc_type is not None and not issubclass(exc_type, Exception)
        result = ('cancelled' if cancelled else 'matched' if exc_type is None else
                  'timeout' if isinstance(exc, PlaywrightTimeoutError) else 'error')
        table = 'unavailable'
        try:
            if not cancelled:
                try:
                    observed_table = self.page.locator('.main-content').first.evaluate('''root => {
                        const tables = root.getElementsByTagName('table');
                        if (!tables.length) return 'missing';
                        if (tables.length > 32) return 'unavailable';
                        let visible = false;
                        for (const t of tables) {
                            const style = getComputedStyle(t);
                            if (!t.getClientRects().length || style.visibility === 'hidden' || style.visibility === 'collapse') continue;
                            visible = true;
                            if (t.querySelector('tbody tr')) return 'rows_present';
                        }
                        return visible ? 'empty' : 'hidden';
                    }''', timeout=100)
                    if type(observed_table) is str and observed_table in {'missing', 'hidden', 'empty', 'rows_present', 'unavailable'}:
                        table = observed_table
                except Exception:
                    pass
            fields = self.counts if self.observation != 'unavailable' else {}
            diagnostics.record('search.result', level='INFO' if result == 'matched' else 'WARNING',
                               search_result=result, search_observation=self.observation,
                               search_table=table, duration_ms=duration, **fields)
        finally:
            self.tracked.clear()
        return False


def _find_taxpayer_row(page, npwp, check_cancel):
    page.locator('#ObjectPermitNumber').wait_for(state='visible', timeout=45000)
    page.locator('#ObjectPermitNumber').fill(npwp)
    with _SearchDiagnostics(page) as probe:
        _check_cancel(check_cancel)
        page.locator('#ObjectPermitNumber').press('Enter')
        deadline = time.monotonic() + SEARCH_RESULT_TIMEOUT_MS / 1000
        row = page.locator('table tbody tr').filter(has_text=npwp)
        while True:
            _check_cancel(check_cancel)
            remaining = (deadline - time.monotonic()) * 1000
            if remaining <= 0:
                raise probe.timeout_error() from None
            try:
                row.first.wait_for(state='visible', timeout=min(100, remaining))
                break
            except PlaywrightTimeoutError:
                continue
        _check_cancel(check_cancel)
        wait_idle(page)
        _check_cancel(check_cancel)
        if row.count() != 1:
            raise RuntimeError('NPWP search was ambiguous; refusing to select a different taxpayer')
        cells = [s.strip() for s in row.locator('td').all_inner_texts()]
        exact = next((i for i, s in enumerate(cells) if s == npwp), None)
        if exact is None:
            raise RuntimeError('NPWP search returned no exact NPWP match; input is not normalized')
        taxpayer_name = cells[exact + 1] if exact + 1 < len(cells) else ''
        return row, taxpayer_name


def _verify_inventory_source(page, source, taxpayer_id):
    if (list_taxpayer_id(page.url) != taxpayer_id
            or urlparse(page.url).path != urlparse(source['url']).path
            or urlparse(page.url).query != urlparse(source['url']).query):
        raise RuntimeError('Submitted navigation changed the selected list or taxpayer; refusing capture')


def _open_inventory_source(page, source, taxpayer_id, observer):
    before = observer.sequence
    try:
        page.goto(source['url'], wait_until='domcontentloaded', timeout=60000)
    except PlaywrightError as exc:
        _check_cancel(observer.check_cancel)
        raise RuntimeError('Submitted navigation failed; refusing inventory capture') from exc
    _verify_inventory_source(page, source, taxpayer_id)
    response = observer.wait(before)
    _verify_inventory_source(page, source, taxpayer_id)
    return response


@diagnostics.traced('inventory')
def collect_inventory(page, npwp, year, basis, folder, max_pages=1000, on_progress=None, check_cancel=None):
    """Temukan NPWP persis, simpan batch daftar, lalu rekonsiliasi inventaris."""
    _check_cancel(check_cancel)
    npwp, year = validate_scope(npwp, year)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    batch_path = folder / 'inventory-batches.jsonl'
    if batch_path.exists():
        raise FileExistsError(f'Use a new output directory; checkpoint already exists: {batch_path}')
    batch_path.touch()
    page.goto(SEARCH_URL, wait_until='domcontentloaded', timeout=60000)
    if not trusted_origin(page.url) or urlparse(page.url).path != urlparse(SEARCH_URL).path:
        raise RuntimeError('Taxpayer search redirected outside the authorized search page; sign in again')
    row, taxpayer_name = _find_taxpayer_row(page, npwp, check_cancel)
    observer = ListObserver(page, check_cancel=check_cancel)
    errors, audit, sources = [], [], []
    try:
        before = observer.sequence
        row.get_by_role('button', name='Pilih', exact=True).evaluate('(e)=>e.click()')
        observer.wait(before)
        taxpayer_id = list_taxpayer_id(page.url)
        links = page.locator('a[href]').evaluate_all('(els)=>els.map(e=>({href:e.getAttribute(\"href\"),label:e.innerText.trim()}))')
        for link in links:
            _check_cancel(check_cancel)
            # Fragment variants are one document, not independent status grids.
            url = urldefrag(urljoin(page.url, link['href'])).url
            try:
                linked_taxpayer = list_taxpayer_id(url)
            except RuntimeError:
                continue
            if (linked_taxpayer == taxpayer_id and link['label'] == 'SPT Dilaporkan'
                    and urlparse(url).path.rstrip('/') == '/returnsheets/id-ID/submitted-returnsheets/' + taxpayer_id):
                if url not in [s['url'] for s in sources]:
                    sources.append({'url': url, 'label': link['label']})
        if len(sources) != 1:
            raise RuntimeError('No unique inspected submitted SPT list; refusing inventory capture')
        retry_missing_catalog = False
        try:
            diagnostics.record('catalog.checkpoint', catalog_stage='planning')
            catalog = read_period_catalog(page) if basis == 'period' else None
            _check_cancel(check_cancel)
            filter_plan = plan_year_filters(catalog, year, basis)
            retry_missing_catalog = basis == 'period' and catalog is None
        except Exception:
            _check_cancel(check_cancel)
            filter_plan = {'eligible': False, 'filters': [], 'reason': 'period_catalog_unavailable'}
        planned_sources = []
        for source in sources:
            submitted = (urlparse(source['url']).path.startswith('/returnsheets/id-ID/submitted-returnsheets/')
                         and source['label'] == 'SPT Dilaporkan')
            if submitted and filter_plan['eligible']:
                for condition in filter_plan['filters']:
                    planned_sources.append({**source, 'list_filter': condition,
                                            'list_catalog_sha256': filter_plan['catalog_sha256'],
                                            'list_catalog_binding_sha256': filter_plan['catalog_binding_sha256'],
                                            'filter_mode': 'period-year-candidates'})
            else:
                planned_sources.append({**source, 'filter_mode': 'unfiltered',
                                        'filter_reason': filter_plan.get('reason', 'unobserved_status_filter')
                                        if submitted else 'unobserved_status_filter'})
        sources = planned_sources
        for source_index, source in enumerate(sources):
            _check_cancel(check_cancel)
            ready_response = None
            submitted = (urlparse(source['url']).path.startswith('/returnsheets/id-ID/submitted-returnsheets/')
                         and source['label'] == 'SPT Dilaporkan')
            if retry_missing_catalog and submitted:
                # The submitted page can populate a cache absent on landing.
                # Observe it before saving rows; reuse this page on fallback.
                retry_missing_catalog = False
                ready_response = _open_inventory_source(page, source, taxpayer_id, observer)
                _check_cancel(check_cancel)
                # Even a page discarded for a recovered filter must prove its
                # original request/row ownership before any further navigation.
                ready_page = ready_response['first'] // ready_response['page_size'] + 1
                adapt_inventory_page(ready_response['body'], _inventory_context(
                    ready_response, source, taxpayer_id, npwp, year, basis, ready_page))
                diagnostics.record('catalog.checkpoint', catalog_stage='readiness')
                try:
                    catalog = read_period_catalog(page)
                    _check_cancel(check_cancel)
                    if catalog is None:
                        # One bounded grace period, with Stop checks between
                        # short waits. Never refresh cache or request metadata.
                        for _ in range(5):
                            _check_cancel(check_cancel)
                            page.wait_for_timeout(100)
                        _check_cancel(check_cancel)
                        catalog = read_period_catalog(page)
                        _check_cancel(check_cancel)
                    filter_plan = plan_year_filters(catalog, year, basis)
                except Exception:
                    _check_cancel(check_cancel)
                    diagnostics.record('catalog.validation', catalog_reason='evaluation_error')
                    filter_plan = {'eligible': False, 'filters': [], 'reason': 'period_catalog_unavailable'}
                _check_cancel(check_cancel)
                _verify_inventory_source(page, source, taxpayer_id)
                if filter_plan['eligible']:
                    ready_response = None
                    source = dict(source)
                    source.pop('filter_reason', None)
                    partitions = [
                        {**source, 'list_filter': condition,
                         'list_catalog_sha256': filter_plan['catalog_sha256'],
                         'list_catalog_binding_sha256': filter_plan['catalog_binding_sha256'],
                         'filter_mode': 'period-year-candidates'}
                        for condition in filter_plan['filters']
                    ]
                    # Replace only the pending item. enumerate visits subsequent
                    # partitions normally; progress and saved sources stay exact.
                    sources[source_index:source_index + 1] = partitions
                    source = sources[source_index]
                else:
                    source['filter_reason'] = filter_plan['reason']
            label = source['label']
            print(f"Inventory: {label}", flush=True)
            entry = {'status': label, 'total': None, 'scanned': 0, 'selected': 0, 'result': 'PARTIAL', 'note': source['url']}
            for field in ('list_filter', 'list_catalog_sha256', 'list_catalog_binding_sha256',
                          'filter_mode', 'filter_reason'):
                if field in source:
                    entry[field] = source[field]
            audit.append(entry)
            source_routes = ExitStack()
            try:
                condition = source.get('list_filter')
                if condition is not None:
                    observer.request_filter = source_routes.enter_context(
                        InventoryFilterRoute(page, taxpayer_id, condition, check_cancel=check_cancel))
                response = (ready_response if ready_response is not None else
                            _open_inventory_source(page, source, taxpayer_id, observer))
                entry['total'] = response['total']
                table = page.locator('.main-content table').first
                table.wait_for(state='visible', timeout=30000)
                container = table.element_handle().evaluate_handle('e=>e.closest(\"p-table\")||e.parentElement')
                if entry['total']:
                    before = observer.sequence
                    if maximize_page_size(page, container):
                        response = observer.wait(before)
                # Daftar tetap menyediakan Prev walaupun First tersembunyi.
                previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
                for _ in range(max_pages):
                    _check_cancel(check_cancel)
                    previous = _list_paginator(container, previous_selector)
                    if not previous:
                        break
                    before = observer.sequence
                    _click_table_paginator(previous, container, check_cancel)
                    response = observer.wait(before)
                if _list_paginator(container, previous_selector):
                    raise RuntimeError(f'List reset page limit {max_pages} reached')
                if response['first'] != 0:
                    raise RuntimeError('List reset did not verify the first page')
                seen_ids = set()
                for page_index in range(max_pages):
                    _check_cancel(check_cancel)
                    if response['total'] != entry['total']:
                        raise RuntimeError('Source list changed during capture; rerun with a new output folder')
                    if condition is not None:
                        validate_partition_response(response, condition)
                    adapted = _inventory_metadata(page, table, response, source, taxpayer_id,
                                                   npwp, year, basis, page_index + 1, folder,
                                                   len(audit), check_cancel)
                    entry['requested_source'] = 'json-first'
                    if adapted['eligible']:
                        page_rows = adapted['rows']
                        entry['used_source'] = 'json' if entry.get('used_source', 'json') == 'json' else 'mixed-pages'
                    else:
                        _check_cancel(check_cancel)
                        grid = table.evaluate(TABLE_JS)
                        if len(grid['rows']) != len(response['rows']):
                            raise RuntimeError('Return-list DOM row count does not match the UI response')
                        identifiers = validate_inventory_rows(response['rows'], taxpayer_id)
                        page_rows = [{'record_id': identifier, 'meta': dict(zip(grid['headers'], values))}
                                     for identifier, values in zip(identifiers, grid['rows'])]
                        entry['used_source'] = 'dom-fallback' if entry.get('used_source', 'dom-fallback') == 'dom-fallback' else 'mixed-pages'
                        entry['fallback_reason'] = adapted['reason']
                    entry.setdefault('metadata_pages', []).append({
                        'page': page_index + 1, 'used_source': 'json' if adapted['eligible'] else 'dom-fallback',
                        'reason': adapted['reason'], 'sequence': response['sequence'],
                    })
                    if condition is not None:
                        entry['metadata_pages'][-1]['filter_rewrite'] = response['binding']['filter_rewrite']
                    entry['scanned'] += len(page_rows)
                    if on_progress:
                        on_progress({'completed': len(audit)-1, 'total': len(sources), 'scanned': entry['scanned']})
                    batch = []
                    for position, page_row in enumerate(page_rows):
                        _check_cancel(check_cancel)
                        identifier = page_row['record_id']
                        if identifier in seen_ids:
                            raise RuntimeError('Repeated SPT identifier; pagination cannot be certified')
                        seen_ids.add(identifier)
                        meta = page_row['meta']
                        try:
                            selected = in_scope(meta, year, basis)
                        except ValueError as exc:
                            errors.append({'object': label + '/' + identifier, 'message': str(exc)})
                            continue
                        if selected:
                            record = {'key': urlparse(source['url']).path + '/' + identifier,
                                      'record_id': identifier, 'meta': meta, 'source_status': label,
                                      'list_url': source['url'], 'list_page': page_index + 1, 'row_position': position,
                                      'list_page_size': response['page_size'],
                                      'capture_complete': False, 'sections': []}
                            if condition is not None:
                                record['list_filter'] = condition
                                record['list_catalog_sha256'] = source['list_catalog_sha256']
                                record['list_catalog_binding_sha256'] = source['list_catalog_binding_sha256']
                                record['list_page_size'] = response['binding']['request']['Rows']
                            for field in ('source_identity', 'source_fields'):
                                if field in page_row:
                                    record[field] = page_row[field]
                            batch.append(record)
                    entry['selected'] += len(batch)
                    with batch_path.open('a', encoding='utf-8') as handle:
                        for record in batch:
                            _check_cancel(check_cancel)
                            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
                    next_button = _list_paginator(container, '.p-paginator-next:not([disabled]):not(.p-disabled)')
                    if not next_button:
                        break
                    if page_index + 1 == max_pages:
                        raise RuntimeError(f'List page limit {max_pages} reached')
                    before = observer.sequence
                    _click_table_paginator(next_button, container, check_cancel)
                    response = observer.wait(before)
                    if response['total'] != entry['total']:
                        raise RuntimeError('Source list changed during capture; rerun with a new output folder')
                if entry['scanned'] != entry['total']:
                    raise RuntimeError(f"Source total {entry['total']} != scanned {entry['scanned']}")
                if condition is not None:
                    diagnostics.record('catalog.checkpoint', catalog_stage='recheck')
                    current_plan = plan_year_filters(read_period_catalog(page), year, basis)
                    if (not current_plan['eligible'] or
                            current_plan.get('catalog_binding_sha256') != source['list_catalog_binding_sha256']):
                        raise JsonSafetyError('Period catalog changed during filtered inventory')
                entry['result'] = 'RECONCILED'
                container.dispose()
            except CaptureCancelled:
                raise
            except Exception as exc:
                diagnostics.record('capture.partial', level='WARNING', error=exc)
                errors.append({'object': label, 'message': str(exc).split('\n')[0]})
                print(f"Inventory partial: {label}: {str(exc).splitlines()[0]}", flush=True)
            finally:
                observer.request_filter = None
                source_routes.close()
            (folder / ('inventory-' + str(len(audit)) + '.json')).write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding='utf-8')
            if on_progress:
                on_progress({'completed': len(audit), 'total': len(sources), 'scanned': entry['scanned']})
    finally:
        observer.close()
    # Agregasikan batch tersimpan; bukti jumlah berasal dari data, bukan pesan log.
    records = [json.loads(line) for line in batch_path.read_text(encoding='utf-8').splitlines() if line]
    keys = [r['key'] for r in records]
    if len(keys) != len(set(keys)) or len(records) != sum(e['selected'] for e in audit):
        raise RuntimeError('Checkpoint reconciliation failed: duplicate identifiers or selected-count mismatch')
    period_catalog = None
    periods_by_id = {}
    period_conflict = False
    for record in records:
        value = record['meta'].get('Masa Pajak', '')
        previous = periods_by_id.setdefault(record['record_id'], value)
        if previous != value:
            period_conflict = True
    if period_conflict:
        # Observe only the already loaded cache; do not refresh source pages or
        # reinterpret literal metadata when independent evidence is unavailable.
        _check_cancel(check_cancel)
        diagnostics.record('catalog.checkpoint', catalog_stage='reconciliation')
        try:
            period_catalog = read_period_catalog(page)
        except Exception:
            diagnostics.record('catalog.validation', catalog_reason='evaluation_error')
        _check_cancel(check_cancel)
    unique = deduplicate_inventory(records, period_catalog=period_catalog, year=year)
    _check_cancel(check_cancel)
    if any('period_equivalence' in record for record in unique):
        # Private job evidence is exclusive: never overwrite an earlier snapshot.
        with (folder / 'period-catalog-reconciliation.json').open('x', encoding='utf-8') as handle:
            json.dump(period_catalog, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        _check_cancel(check_cancel)
    if len(unique) != len(records):
        audit.append({'status': 'Deduplicatie / Deduplikasi', 'total': len(records), 'scanned': len(unique), 'selected': len(unique),
                      'result': 'RECONCILED', 'note': 'Same RecordId appears in multiple status lists. Retained once; all source occurrences preserved. Distinct amendments retain distinct identifiers.'})
    result = {'npwp': npwp, 'year': year, 'year_basis': basis, 'taxpayer_name': taxpayer_name,
              'records': unique, 'audit': audit, 'errors': errors, 'sources': sources,
              'scope_description': 'Hanya SPT Dilaporkan dalam tahun pilihan; seluruh jenis dan pembetulan yang teramati pada daftar tersebut.',
              'inventory_complete': bool(sources) and not errors and all(e['result'] == 'RECONCILED' for e in audit)}
    (folder / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    # Observe late cache availability before the selection deadline starts.
    # This never replans filters or changes the already reconciled inventory.
    if basis == 'period':
        _check_cancel(check_cancel)
        diagnostics.record('catalog.checkpoint', catalog_stage='after_inventory')
        try:
            plan_year_filters(read_period_catalog(page), year, basis)
        except CaptureCancelled:
            raise
        except Exception:
            diagnostics.record('catalog.validation', catalog_reason='evaluation_error')
        _check_cancel(check_cancel)
    return result


def open_return_readonly(page, row, taxpayer_id, record_id=None, *, json_capture=None):
    """Buka satu kontrol View yang dikenali dan verifikasi asal detailnya."""
    # Hanya tombol View persis yang telah diamati; jangan menebak aksi baris lain.
    view = row.locator('button[id=ViewButton]')
    if view.count() != 1:
        raise RuntimeError('No unique supported View control; refusing to click other row actions')
    opened = []
    callback = lambda tab: opened.append(tab)
    previous_url = page.url
    page.on('popup', callback)
    verified = False
    try:
        view.click()
        deadline = time.monotonic() + 20
        while not opened and page.url == previous_url:
            if time.monotonic() > deadline:
                raise RuntimeError('View did not open a return; unsupported document or permission failure')
            page.wait_for_timeout(100)
        if len(opened) > 1:
            raise RuntimeError('View opened multiple tabs; return provenance is ambiguous')
        detail = opened[0] if opened else page
        detail.wait_for_load_state('domcontentloaded', timeout=60000)
        verify_detail_url(detail.url, taxpayer_id, record_id)
        if json_capture is not None:
            json_capture.bind_detail_page(detail)
        verified = True
        return detail, bool(opened)
    finally:
        page.remove_listener('popup', callback)
        if not verified:
            for tab in opened:
                try:
                    tab.close()
                except Exception:
                    pass  # Pertahankan error navigasi jika popup sudah ditutup.


def observe_corporate_forms(page, record, scope, capture, **kwargs):
    from coretax_corporate import observe_forms
    return observe_forms(page, record, scope, capture, approved_digest=CIT_SOURCE_SHA256, **kwargs)


def capture_financial_detail(page, **kwargs):
    from coretax_corporate import capture_financial
    return capture_financial(page, **kwargs)


def _check_corporate_request_identities(observations, record, scope):
    from coretax_corporate import GRID_ROLES
    grid_paths = {'/returnsheet/api/loadcit/' + suffix
                  for roles in GRID_ROLES.values() for _, suffix, _ in roles}
    period = record.get('source_fields', {}).get('TaxPeriodCode')
    expected_year = period[-4:] if isinstance(period, str) and re.search(r'[0-9]{4}$', period) else None
    if expected_year is None and scope[2] == 'period':
        expected_year = str(scope[1])
    for item in observations:
        url = item['url']
        if not trusted_origin(url):
            continue
        path = urlparse(url).path
        if path == '/returnsheet/api/prefillreturnsheet/corporate-income':
            field = 'RecordId'
        elif path in grid_paths:
            field = 'ReturnSheetRecordId'
        else:
            continue
        request_data = item.get('request_json')
        if not isinstance(request_data, dict):
            continue
        # Missing evidence grants no JSON eligibility. Explicit contradictions
        # remain fatal even when the build/forms or response MIME are unknown.
        if field in request_data:
            value = request_data[field]
            if type(value) is not str or value != record['record_id']:
                raise JsonSafetyError('Known corporate request contradicts selected return')
        if (path == '/returnsheet/api/loadcit/l4-table-a-grid'
                and expected_year is not None and 'PeriodYear' in request_data):
            value = request_data['PeriodYear']
            if type(value) is not str or value != expected_year:
                raise JsonSafetyError('Known corporate request contradicts selected period')


def _identity_checked_packets(packets, record, scope):
    from coretax_json import (_corporate_json, _corporate_primary,
                              _corporate_selected, _UnsupportedMetadata)
    selected = _corporate_selected(record, scope)
    for packet in packets:
        url = packet['context']['url']
        if (trusted_origin(url) and urlparse(url).path ==
                '/returnsheet/api/prefillreturnsheet/corporate-income'):
            envelope = _corporate_json(packet['body'])
            payload = envelope.get('Payload') if isinstance(envelope, dict) else None
            if isinstance(payload, dict):
                try:
                    # Negative identity checks do not grant UI coverage. In
                    # particular, unknown builds cannot hide a known TIN/ID clash.
                    _corporate_primary(payload, record, selected, scope, [], {})
                except _UnsupportedMetadata:
                    # Missing coverage permits fallback, never identity clashes.
                    pass
        yield packet


def _hybrid_detail(page, record, scope, folder, capture, max_pages, check_cancel):
    from coretax_json import adapt_corporate_detail
    corporate = record['meta'].get('Jenis Pajak') == 'PPh Badan'
    masa = record['meta'].get('Jenis Pajak') in ('PPN', 'PPh Pasal 21/26', 'PPh Unifikasi')
    if masa:
        from coretax_masa_json import adapt_masa_detail, check_masa_request_identities
        if record['meta'].get('Jenis Pajak') == 'PPh Pasal 21/26':
            from coretax_pph21_observer import observe_pph21_forms as observe_masa_forms
        else:
            from coretax_masa_observer import observe_masa_forms
        check_masa_request_identities(capture.request_observations(), record, scope)
    if corporate:
        _check_corporate_request_identities(capture.request_observations(), record, scope)
    with diagnostics.measure('json_observe'):
        forms = observe_corporate_forms(page, record, scope, capture,
            max_pages=max_pages, check_cancel=check_cancel) if corporate else None
        if masa:
            forms = observe_masa_forms(page, record, scope, capture,
                max_pages=max_pages, check_cancel=check_cancel)
    observations = capture.request_observations()
    if masa:
        check_masa_request_identities(observations, record, scope)
    if corporate:
        _check_corporate_request_identities(observations, record, scope)
    if any(item.get('status') in (401, 403) for item in observations):
        raise JsonSafetyError('Detail HTTP authorization was rejected')
    manifest = capture.drain(check_cancel=check_cancel)
    if masa:
        check_masa_request_identities(capture.request_observations(), record, scope)
    if corporate:
        _check_corporate_request_identities(capture.request_observations(), record, scope)
    # Kegagalan privasi atau identitas menghentikan jalur hybrid; hasil DOM
    # tidak boleh menutupi bukti sumber yang sudah dinyatakan tidak aman.
    if any(reason in manifest['reasons'] for reason in (
            'secret-body', 'secret-request', 'invalid-json', 'response-source-mismatch',
            'request-context-unavailable', 'authorization-rejected')):
        raise JsonSafetyError('Detail JSON privacy or source verification failed')
    bodies = capture.iter_bodies(check_cancel=check_cancel)
    if corporate:
        bodies = _identity_checked_packets(bodies, record, scope)
    with diagnostics.measure('json_project'):
        decoded = adapt_corporate_detail(bodies, record=record, scope=scope,
                                         observed_forms=forms or []) if corporate else None
        if masa:
            decoded = adapt_masa_detail(bodies, record=record, scope=scope, observed_forms=forms or [])
    if not corporate and not masa:
        for packet in bodies:
            _check_cancel(check_cancel)
            if packet['context']['status'] in (401, 403):
                raise JsonSafetyError('Detail HTTP authorization was rejected')
    _check_cancel(check_cancel)
    # Pilihan sumber berlaku untuk seluruh SPT agar form JSON yang belum lengkap
    # tidak dicampur dengan sebagian nilai DOM dan dianggap satu capture utuh.
    eligible = ((corporate or masa) and forms is not None and manifest['complete']
                and decoded['eligible'] and decoded['coverage']['complete'])
    source_reason = ('native_verified' if eligible else
                     'unsupported_tax' if not corporate and not masa else
                     'forms_unavailable' if forms is None else
                     'capture_incomplete' if not manifest['complete'] else
                     'adapter_ineligible' if not decoded['eligible'] else 'coverage_incomplete')
    diagnostics.record('detail.source', source_requested='json-first',
                       source_used='json' if eligible else 'dom', source_reason=source_reason)
    audit = {'version': 1, 'requested': 'json-first', 'used': 'json' if eligible else 'dom',
             'capture': manifest}
    if decoded is not None:
        audit.update(coverage=decoded['coverage'], json=decoded['provenance'])
    if eligible:
        if corporate:
            result = capture_financial_detail(page, record=record, folder=folder, check_cancel=check_cancel)
        else:
            result = {'detail_url': page.url, 'capture_complete': True, 'errors': [], 'attachments': []}
        result['sections'] = decoded['sections']
        audit['reason'] = ('verified_native_corporate_source' if corporate else
                           'verified_native_ppn_source' if record['meta'].get('Jenis Pajak') == 'PPN'
                           else 'verified_native_unifikasi_source' if record['meta'].get('Jenis Pajak') == 'PPh Unifikasi'
                           else 'verified_native_pph21_source')
    else:
        audit['reason'] = (decoded['reason'] if decoded is not None and not decoded['eligible']
                           else 'unsupported_observed_forms_or_capture')
        result = capture_detail(page, max_pages=max_pages, check_cancel=check_cancel,
                                record=record, folder=folder)
    result['detail_source'] = audit
    return result


def _atomic_checkpoint(path, value):
    from coretax_pdf import _directories
    from spt_desktop.output_windows import DirectoryGuard
    path = Path(path).absolute()
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    created = None
    with DirectoryGuard() as guard:
        guard.include(_directories(path.parent))
        try:
            with temporary.open('xb') as stream:
                info = os.fstat(stream.fileno())
                created = (info.st_dev, info.st_ino)
                stream.write(json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            # Hanya inode sementara milik penulisan ini yang boleh dibersihkan;
            # penggantian nama oleh proses lain tidak memberi hak menghapusnya.
            if created is not None and temporary.exists():
                current = temporary.lstat()
                if (current.st_dev, current.st_ino) == created:
                    temporary.unlink()


def read_detail_checkpoint(path, record, scope, *, detail_source='dom'):
    """Terima hanya hasil capture dengan identitas dan scope inventaris yang sama."""
    validate_detail_source(detail_source)
    path = Path(path).absolute()
    from coretax_pdf import _directories
    from spt_desktop.output_windows import DirectoryGuard, locked_file
    with DirectoryGuard() as guard:
        guard.include(_directories(path.parent))
        with locked_file(path) as stream:
            saved = json.load(stream)
    identity_fields = ('key', 'record_id', 'meta', 'list_url', 'list_page', 'list_page_size',
                       'row_position', 'source_status')
    if (not isinstance(saved, dict) or saved.get('scope') != scope
            or any(saved.get(field) != record.get(field) for field in identity_fields)):
        raise RuntimeError('Existing detail checkpoint belongs to a different record, scope or source; use a new output folder')
    if saved.get('capture_complete'):
        try:
            verify_detail_url(saved.get('detail_url'), list_taxpayer_id(record['list_url']), record['record_id'])
        except RuntimeError as exc:
            raise RuntimeError('Existing detail checkpoint has unverifiable return provenance') from exc
    audit = saved.get('detail_source')
    if audit is not None:
        if (not isinstance(audit, dict) or type(audit.get('version')) is not int or audit['version'] != 1
                or audit.get('requested') not in ('dom', 'json-first') or audit.get('used') not in ('dom', 'json')):
            raise JsonSafetyError('Checkpoint detail-source descriptor is unsupported')
        if audit['used'] == 'json' and (audit['requested'] != 'json-first' or detail_source != 'json-first'):
            raise JsonSafetyError('Checkpoint JSON source does not match the requested mode')
        if audit.get('capture') is not None or audit['used'] == 'json':
            from coretax_json_capture import checkpoint_bodies
            checkpoint_bodies(path.parent.parent, audit.get('capture'), saved, scope)
        if audit['used'] == 'json':
            from coretax_pdf import pdf_custody
            probe = {'npwp': scope[0], 'year': scope[1], 'year_basis': scope[2],
                     'complete': False, 'records': [saved]}
            probe['output_attachments'] = [{**item, 'record_id': saved['record_id'], 'scope': list(scope)}
                for item in saved.get('attachments', []) if item['status'] == 'COMPLETE']
            try:
                with pdf_custody(probe, path.parent.parent):
                    pass
            except (OSError, ValueError):
                # A missing or changed PDF invalidates the checkpoint; do not
                # expose private paths or turn this into a DOM fallback.
                raise JsonSafetyError('Checkpoint PDF custody cannot be safely verified') from None
    # Berkas detail tidak boleh menimpa identitas atau metadata asal inventaris.
    return {field: saved[field] for field in ('detail_url', 'sections', 'capture_complete', 'scope', 'attachments', 'detail_source') if field in saved}


def _benchmark_tax_kind(record):
    value = record.get('meta', {}).get('Jenis Pajak')
    if type(value) is not str:
        return 'other'
    return {'PPN': 'ppn', 'PPh Pasal 21/26': 'pph21', 'PPh Unifikasi': 'unifikasi',
            'PPh Badan': 'corporate'}.get(value, 'other')


def _benchmark_result(record):
    try:
        result = {'status': 'COMPLETE' if record.get('capture_complete') is True else 'PARTIAL'}
        sections = record.get('sections')
        if type(sections) is not list:
            return result
        tables = [table for section in sections for table in section.get('tables', [])]
        result.update(forms=len(sections), grids=len(tables))
        # Unknown counts are absent, not fabricated zeroes. Footer/layout rows
        # must not be inferred to be business rows when no body count is supplied.
        for output, key in (('body_rows', 'body_row_count'), ('pages', 'pages')):
            if all(type(t.get(key)) is int and t[key] >= 0 for t in tables):
                result[output] = sum(t[key] for t in tables)
        return result
    except Exception:
        # Optional diagnostics must never replace capture/Stop outcomes.
        return {}


def _verify_restored_metadata(page, run, record, current_meta, api_record, folder, ordinal, check_cancel):
    """Prove a display alias before View without changing inventory literals."""
    failure = 'SPT metadata changed since inventory; refusing to capture a different return'
    for field in ('Jenis Pajak', 'Model SPT', 'Nomor Bukti Penerimaan'):
        _check_cancel(check_cancel)
        if record['meta'].get(field, '') != current_meta.get(field, ''):
            raise RuntimeError(failure)
    left, right = record['meta'].get('Masa Pajak', ''), current_meta.get('Masa Pajak', '')
    if left == right:
        return
    saved_proof = record.get('period_equivalence')
    occurrences = record.get('source_occurrences')
    source_keys = ('key', 'source_status', 'list_url', 'list_page', 'row_position')
    fresh = ('period_equivalence' not in record and record.get('source_status') == 'SPT Dilaporkan'
             and isinstance(occurrences, list) and len(occurrences) == 1
             and isinstance(occurrences[0], dict)
             and occurrences[0].get('meta') == record['meta']
             and all(key in record and occurrences[0].get(key) == record[key] for key in source_keys))
    if not fresh and not isinstance(saved_proof, dict):
        raise RuntimeError(failure)
    _check_cancel(check_cancel)
    diagnostics.record('catalog.checkpoint', catalog_stage='restoration')
    proof = None
    try:
        catalog = read_period_catalog(page)
        _check_cancel(check_cancel)
        proof = prove_period_equivalence(left, right, catalog, run['year'])
    except Exception:
        diagnostics.record('catalog.validation', catalog_reason='evaluation_error')
    _check_cancel(check_cancel)
    if proof is None or api_record.get('TaxPeriodCode') != proof['code']:
        raise RuntimeError(failure)
    if not fresh:
        if any(proof[key] != saved_proof.get(key) for key in ('code', 'label', 'catalog_binding_sha256')):
            raise RuntimeError(failure)
        return
    # Exclusive private evidence: never replace inventory or an earlier snapshot.
    _check_cancel(check_cancel)
    name = f'period-catalog-restoration-{ordinal:04d}-{uuid4().hex}.json'
    with (folder / name).open('x', encoding='utf-8') as handle:
        json.dump(catalog, handle, ensure_ascii=False, indent=2)
    _check_cancel(check_cancel)
    record['period_equivalence'] = {**proof, 'catalog_file': name}


@diagnostics.traced('details')
def collect_details(page, run, folder, max_pages=1000, detail_limit=None, on_progress=None, check_cancel=None, *, detail_source='dom'):
    """Lanjutkan checkpoint yang sah dan ambil detail SPT yang belum lengkap."""
    validate_detail_source(detail_source)
    _check_cancel(check_cancel)
    folder = Path(folder)
    checkpoint_dir = folder / 'returns'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    observer = None
    active_group, current_response = None, None
    group_routes = ExitStack()
    run['errors'] = [e for e in run.get('errors', []) if e.get('phase') != 'details']
    scope = [run['npwp'], run['year'], run['year_basis']]
    run['complete'] = False
    attempted = 0
    try:
        observer = ListObserver(page, check_cancel=check_cancel)
        for ordinal, record in enumerate(run['records'], 1):
            with diagnostics.detail_context(ordinal=ordinal, tax_kind=_benchmark_tax_kind(record), source_requested=detail_source):
                with diagnostics.measure('return_detail', source_used='none', cached=False) as timing:
                    try:
                        _check_cancel(check_cancel)
                        checkpoint = checkpoint_dir / f'{ordinal:04d}.json'
                        if checkpoint.exists():
                            saved = read_detail_checkpoint(checkpoint, record, scope, detail_source=detail_source)
                            # COMPLETE lama belum membuktikan inspeksi lampiran Badan.
                            # Hanya resume live yang mengambil ulang; ekspor offline tetap kompatibel.
                            needs_financial = record['meta'].get('Jenis Pajak') == 'PPh Badan'
                            if saved.get('capture_complete') and (not needs_financial or saved.get('attachments')):
                                diagnostics.record('checkpoint.reused', phase='details')
                                record.update(saved)
                                timing.update(cached=True, source_used=saved.get('detail_source', {}).get('used', 'dom'))
                                diagnostics.record('detail.source', source_used=timing['source_used'], source_reason='checkpoint_reuse')
                                print(f"Resume {ordinal}/{len(run['records'])}: verified checkpoint", flush=True)
                                if on_progress:
                                    on_progress(run, ordinal)
                                continue
                        if detail_limit is not None and attempted >= detail_limit:
                            run['errors'].append({'object': 'Scope', 'phase': 'details', 'message': f'Test detail limit {detail_limit} reached; full export not complete'})
                            break
                        attempted += 1
                        record['scope'] = [run['npwp'], run['year'], run['year_basis']]
                        print(f"Detail {ordinal}/{len(run['records'])}: {record['meta'].get('Jenis Pajak', '')} | {record['meta'].get('Masa Pajak', '')}", flush=True)
                        detail, is_popup, json_capture = None, False, None
                        try:
                            taxpayer_id = list_taxpayer_id(record['list_url'])
                            condition = record.get('list_filter')
                            # Pemulihan daftar harus memakai halaman, ukuran, dan filter asal;
                            # RecordId tetap dicocokkan sebelum View meski posisi baris berubah.
                            group = (record['list_url'], record['list_page'], record.get('list_page_size'),
                                     json.dumps(condition, sort_keys=True, ensure_ascii=False))
                            if group != active_group:
                                with diagnostics.measure('list_restore'):
                                    observer.request_filter = None
                                    group_routes.close()
                                    if condition is not None:
                                        observer.request_filter = group_routes.enter_context(
                                            InventoryFilterRoute(page, taxpayer_id, condition, check_cancel=check_cancel))
                                    before = observer.sequence
                                    page.goto(record['list_url'], wait_until='domcontentloaded', timeout=60000)
                                    if list_taxpayer_id(page.url) != taxpayer_id:
                                        raise RuntimeError('Return-list navigation changed the selected taxpayer; refusing capture')
                                    current_response = observer.wait(before)
                                    table = page.locator('.main-content table').first
                                    container = table.element_handle().evaluate_handle('e=>e.closest(\"p-table\")||e.parentElement')
                                    current_size = container.query_selector('.p-paginator-rpp-options .p-dropdown-label')
                                    desired = record.get('list_page_size')
                                    if desired and current_size and current_size.inner_text().strip() != str(desired):
                                        before = observer.sequence
                                        if maximize_page_size(page, container):
                                            current_response = observer.wait(before)
                                        if current_size.inner_text().strip() != str(desired):
                                            raise RuntimeError('Could not restore inventory page size; row provenance would be ambiguous')
                                    previous_selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'
                                    for _ in range(max_pages):
                                        _check_cancel(check_cancel)
                                        previous = _list_paginator(container, previous_selector)
                                        if not previous:
                                            break
                                        before = observer.sequence
                                        previous.evaluate('(e)=>e.click()')
                                        current_response = observer.wait(before)
                                    if _list_paginator(container, previous_selector):
                                        raise RuntimeError(f'List reset page limit {max_pages} reached')
                                    if current_response['first'] != 0:
                                        raise RuntimeError('List reset did not verify the first page')
                                    for _ in range(record['list_page'] - 1):
                                        _check_cancel(check_cancel)
                                        next_button = _list_paginator(container, '.p-paginator-next:not([disabled]):not(.p-disabled)')
                                        if not next_button:
                                            raise RuntimeError('Inventory page is no longer available; source changed')
                                        before = observer.sequence
                                        next_button.evaluate('(e)=>e.click()')
                                        current_response = observer.wait(before)
                                    if current_response['first'] != (record['list_page'] - 1) * current_response['page_size']:
                                        raise RuntimeError('Restored list response has an unexpected page offset')
                                    container.dispose()
                                    active_group = group
                            if condition is not None:
                                validate_partition_response(current_response, condition)
                                if current_response['binding']['request']['Rows'] != record.get('list_page_size'):
                                    raise JsonSafetyError('Filtered inventory page size changed during restoration')
                            identifiers = validate_inventory_rows(current_response['rows'], taxpayer_id)
                            if record['record_id'] not in identifiers:
                                raise RuntimeError('Inventoried SPT is not on the expected source page; rerun inventory')
                            position = identifiers.index(record['record_id'])
                            table = page.locator('.main-content table').first
                            source_row = table.locator('tbody tr').nth(position)
                            data = table.evaluate(TABLE_JS)
                            current_meta = dict(zip(data['headers'], data['rows'][position]))
                            _verify_restored_metadata(page, run, record, current_meta,
                                current_response['rows'][position], folder, ordinal, check_cancel)
                            if detail_source == 'json-first' and record['meta'].get('Jenis Pajak') in ('PPN', 'PPh Pasal 21/26', 'PPh Unifikasi', 'PPh Badan'):
                                from coretax_masa_json import (bind_ppn_listing_identity, bind_pph21_listing_identity,
                                                               bind_unifikasi_listing_identity, bind_corporate_listing_identity)
                                prefix, bind_identity = {
                                    'PPN': ('ppn', bind_ppn_listing_identity),
                                    'PPh Pasal 21/26': ('pph21', bind_pph21_listing_identity),
                                    'PPh Unifikasi': ('unifikasi', bind_unifikasi_listing_identity),
                                    'PPh Badan': ('corporate', bind_corporate_listing_identity),
                                }[record['meta']['Jenis Pajak']]
                                identity = bind_identity(current_response, record=record, scope=scope)
                                if identity['eligible']:
                                    from coretax_pdf import _directories
                                    from spt_desktop.output_windows import DirectoryGuard
                                    relative = Path('listing-responses') / f'{prefix}-identity-{ordinal:04d}-{uuid4().hex}.json'
                                    target = (folder / relative).absolute()
                                    with DirectoryGuard() as guard:
                                        # Detail-only/resumed collection need not have saved inventory bodies.
                                        guard.include(_directories(target.parent.parent))
                                        target.parent.mkdir(exist_ok=True)
                                        guard.include(_directories(target.parent))
                                        with target.open('xb') as handle:
                                            handle.write(current_response['body'])
                                            handle.flush()
                                            os.fsync(handle.fileno())
                                    record['source_fields'] = identity['source_fields']
                                    record['source_identity'] = {**identity['source_identity'],
                                                                 'relative_path': relative.as_posix()}
                            session = nullcontext(None)
                            if detail_source == 'json-first':
                                from coretax_json_capture import DetailJsonCapture
                                session = DetailJsonCapture(page.context, page, record, scope, folder,
                                                            ordinal=ordinal, check_cancel=check_cancel)
                            with session as json_capture:
                                with diagnostics.measure('open_detail'):
                                    detail, is_popup = open_return_readonly(page, source_row, taxpayer_id, record['record_id'],
                                                                            json_capture=json_capture)
                                    detail.set_viewport_size({'width': 1600, 'height': 1000})
                                if json_capture is None:
                                    timing['source_used'] = 'dom'
                                    diagnostics.record('detail.source', source_used='dom', source_reason='dom_requested')
                                    capture = capture_detail(detail, max_pages=max_pages, check_cancel=check_cancel,
                                                             record=record, folder=folder)
                                else:
                                    capture = _hybrid_detail(detail, record, scope, folder, json_capture, max_pages, check_cancel)
                            timing['source_used'] = capture.get('detail_source', {}).get('used', 'dom')
                            if 'detail_source' in capture:
                                record['detail_source'] = capture['detail_source']
                            record.update({'detail_url': detail.url, 'sections': capture['sections'], 'capture_complete': capture['capture_complete'], 'scope': [run['npwp'], run['year'], run['year_basis']]})
                            record['attachments'] = capture.get('attachments', [])
                            for error in capture['errors']:
                                _check_cancel(check_cancel)
                                run['errors'].append({'object': record['record_id'] + '/' + error['object'], 'phase': 'details', 'message': error['message']})
                        except CaptureCancelled:
                            record.update(capture_complete=False, sections=[], attachments=[])
                            record.pop('detail_source', None)
                            raise
                        except Exception as exc:
                            diagnostics.record('capture.partial', level='WARNING', error=exc)
                            active_group = None
                            record['capture_complete'] = False
                            if isinstance(exc, JsonSafetyError) and json_capture is not None:
                                record.update(sections=[], attachments=[])
                                record.pop('detail_source', None)
                                raise
                            run['errors'].append({'object': record['record_id'], 'phase': 'details', 'message': str(exc).split('\n')[0]})
                            print(f"Detail partial: {str(exc).splitlines()[0]}", flush=True)
                        finally:
                            if detail is not None and is_popup:
                                detail.close()
                            elif detail is not None:
                                active_group = None
                            _atomic_checkpoint(checkpoint, record)
                            _atomic_checkpoint(folder / 'run.json', run)
                            if on_progress:
                                on_progress(run, ordinal)
                    finally:
                        timing.update(_benchmark_result(record))
    finally:
        if observer is not None:
            observer.request_filter = None
            observer.close()
        group_routes.close()
    # Baca ulang checkpoint tersimpan dan agregasikan sebelum menetapkan COMPLETE.
    for ordinal, record in enumerate(run['records'], 1):
        _check_cancel(check_cancel)
        checkpoint = checkpoint_dir / f'{ordinal:04d}.json'
        if checkpoint.exists():
            record.update(read_detail_checkpoint(checkpoint, record, scope, detail_source=detail_source))
    run['complete'] = bool(run.get('inventory_complete')) and not run['errors'] and all(r.get('capture_complete') for r in run['records'])
    return run
