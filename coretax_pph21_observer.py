"""PPh21 navigation and metadata only; source values remain in captured JSON."""
import re

from coretax_json import ORIGIN, PPH21_REFERENCE_URLS, JsonSafetyError
from coretax_corporate import _BUILD_HASH, _tabs, _turn_grid, _native_panel
from coretax_masa_bindings import MAIN_SOURCE, BUILD_DIGESTS as MASA_BUILD_DIGESTS
from coretax_masa_observer import (TABLE, _PPN_MAIN_BUILD_HASH, _observations, _pages, _requests,
                                   _reference_order_build)

ARTICLE_SOURCE = ORIGIN + '/returnsheets/id-ID/803.8681206e4827011e.js'
BUILD_DIGESTS = {MAIN_SOURCE: MASA_BUILD_DIGESTS[MAIN_SOURCE],
                 ARTICLE_SOURCE: 'cd7b51042384a63e1d1fae9b9b284a38a0a942ab9f95a7fceb46b3c76fcd9add'}
FORMS = {
    'Induk': ('rshshr-art2126-main-form', None, ()),
    'L-IA': ('rshshr-art2126-l1a-form', 'rshshr-art2126-l1a-grid', (('l1a', 'LIST-IA'),)),
    'L-IB': ('rshshr-art2126-l1b-form', 'rshshr-art2126-l1b-grid', (('l1b-bpa1', 'BPA1'), ('l1b-bpa2', 'BPA2'))),
    'L-II': ('rshshr-art2126-l2-form', 'rshshr-art2126-l2-grid', (('l2-bpa1', 'BPA1'), ('l2-bpa2', 'BPA2'))),
    'L-III': ('rshshr-art2126-l3-form', 'rshshr-art2126-l3-grid', (('l3-bp21', 'BP21'), ('l3-bp26', 'BP26'))),
}

# Unlike the shared observer, PPh21 controls can live inside Induk tables.
# Read binding names and geometry, never table-body labels, values or state.
_FIELDS = r'''root => {
 const visible=e=>!!e.getClientRects().length, group=GROUP, seen=new Set(), fields=[];
 for(const child of root.querySelectorAll('[formcontrolname],input,textarea,select,ui-dropdown,p-dropdown,p-checkbox,p-radiobutton,p-calendar')){
  if(child.closest('ui-grid,[hidden],[aria-hidden="true"]')||child.matches('input[type=hidden],input[type=password]'))continue;
  const dropdown=child.closest('ui-dropdown');
  if(dropdown&&seen.has(dropdown))continue;
  const control=child.closest('[formcontrolname]')||child.closest('ui-dropdown,p-dropdown,p-checkbox,p-radiobutton,p-calendar')||child;
  if(seen.has(control)||!visible(control))continue;
  seen.add(control);
  const groupName=group(control);
  let field=control.getAttribute('formcontrolname')||control.getAttribute('name')||control.id||'',label=field;
  if(!field&&control.matches('ui-dropdown')){
   const row=control.closest('.form-group'),labels=row?[...row.querySelectorAll(':scope > label')]:[];
   if(root.tagName!=='RSHSHR-ART2126-MAIN-FORM'||groupName!=='HEADER'||labels.length!==1||
      row.querySelectorAll('ui-dropdown').length!==1||labels[0].innerText.trim()!=='Status SPT'||
      fields.some(f=>f.field==='Status'))return null;
   field='Status';label='Status SPT';
  }
  if(!field)return null;
  fields.push({field,label,group:groupName,column_label:'',tag:control.tagName});
 }
 return fields;
}'''
# Geometry references the catalog above; it is not another value projection.
_INDUK_TABLE = r'''table => {
 const rows=[...table.rows];
 return {row_spans:rows.map(row=>[...row.cells].map(cell=>cell.colSpan)),
   row_fields:rows.map(row=>[...row.querySelectorAll('[formcontrolname]')].map(e=>e.getAttribute('formcontrolname')))};
}'''


# Fetch only reviewed read-only catalogs. Discard streamed bytes here; the
# capture owns original response bytes, privacy checks and replay custody.
_REFERENCE_GET = r'''async url => {
 const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),30000);
 let status=0;
 try {
  if(new URL(url).origin!==location.origin)return {ok:false,status};
  const response=await fetch(url,{method:'GET',mode:'same-origin',credentials:'same-origin',
    redirect:'error',cache:'no-store',headers:{'Content-Type':'application/json'},signal:controller.signal});
  status=response.status;
  const mime=(response.headers.get('content-type')||'').split(';')[0].trim().toLowerCase();
  const limit=32*1024*1024, length=response.headers.get('content-length');
  if(status!==200||(mime!=='application/json'&&!mime.endsWith('+json'))||
     (length!==null&&(!/^[0-9]+$/.test(length)||Number(length)>limit))){
    if(response.body)await response.body.cancel();
    return {ok:false,status};
  }
  if(!response.body)return {ok:false,status};
  const reader=response.body.getReader();let size=0;
  while(true){
   const chunk=await reader.read();
   if(chunk.done)break;
   size+=chunk.value.byteLength;
   if(size>limit){await reader.cancel();return {ok:false,status};}
  }
  return {ok:size>0,status};
 }catch(_){return {ok:false,status};}
 finally{clearTimeout(timer);}
}'''


def _reference_bindings(page, record, scope, capture, check_cancel, *, endpoints=PPH21_REFERENCE_URLS):
    from coretax_browser import _check_cancel, list_taxpayer_id, verify_detail_url
    taxpayer = list_taxpayer_id(record['list_url'])
    bindings = []
    for endpoint in endpoints:
        _check_cancel(check_cancel)
        verify_detail_url(page.url, taxpayer, record['record_id'])
        before = {event['sequence'] for event in _observations(capture, record, scope)}
        result = page.evaluate(_REFERENCE_GET, endpoint)
        events = _observations(capture, record, scope)
        _check_cancel(check_cancel)
        verify_detail_url(page.url, taxpayer, record['record_id'])
        if isinstance(result, dict) and result.get('status') in (401, 403):
            raise JsonSafetyError('PPh21 reference authorization was rejected')
        if not isinstance(result, dict) or result.get('ok') is not True or result.get('status') != 200:
            return None
        matches = [event for event in events if event['sequence'] not in before and event['url'] == endpoint]
        if len(matches) != 1:
            return None
        event = matches[0]
        if event.get('method') != 'GET' or event.get('request_json') is not None:
            raise JsonSafetyError('PPh21 reference observation contradicts its GET request')
        bindings.append({'endpoint': endpoint, 'method': 'GET', 'sequences': [event['sequence']]})
    return bindings


def observe_pph21_forms(page, record, scope, capture, *, max_pages=1000, check_cancel=None):
    """Observe all five forms; this alone never grants native export coverage."""
    from coretax_browser import GROUP_JS, _check_cancel, list_taxpayer_id, verify_detail_url
    _check_cancel(check_cancel)
    _observations(capture, record, scope)
    try:
        if record.get('meta', {}).get('Jenis Pajak') != 'PPh Pasal 21/26' or type(max_pages) is not int or max_pages <= 0:
            return None
        taxpayer = list_taxpayer_id(record['list_url'])
        verify_detail_url(page.url, taxpayer, record['record_id'])
        builds = {}
        for url in (MAIN_SOURCE, ARTICLE_SOURCE):
            _check_cancel(check_cancel)
            digest = page.evaluate(_PPN_MAIN_BUILD_HASH if url == MAIN_SOURCE else _BUILD_HASH, url)
            if digest != BUILD_DIGESTS[url]:
                return None
            builds[url] = digest
        reference_order = _reference_order_build(page, check_cancel)
        view, tabs = _tabs(page)
        canonical = {name.upper(): name for name in FORMS}
        names = [canonical.get(tabs.nth(i).inner_text().strip().upper()) for i in range(tabs.count())]
        if len(names) != len(set(names)) or set(names) != set(FORMS):
            return None
        environment = page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
        if environment != {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}:
            return None
        forms = []
        for ordinal, name in enumerate(names):
            _check_cancel(check_cancel)
            tab = tabs.nth(ordinal)
            if tab.evaluate('(e)=>e.closest("li").classList.contains("p-disabled")||e.getAttribute("aria-disabled")==="true"'):
                return None
            caption = tab.inner_text().strip()
            if canonical.get(caption.upper()) != name:
                return None
            panel = _native_panel(page, view, tab, caption, record, check_cancel)
            if panel is None:
                return None
            selector, container, roles = FORMS[name]
            root = panel.locator(selector)
            if root.count() != 1 or not root.is_visible():
                return None
            fields = root.evaluate(_FIELDS.replace('GROUP', GROUP_JS))
            if fields is None:
                return None
            binding = {'name': name, 'fields': fields, 'tables': [], 'builds': dict(builds), **environment}
            if name == 'Induk' and reference_order is not None:
                binding['reference_order_build'] = reference_order
            if not roles:
                if root.locator('ui-grid').count():
                    return None
                tables = root.locator('table:visible')
                for index in range(tables.count()):
                    physical = tables.nth(index)
                    binding['tables'].append({'name': 'Tabel ' + str(index + 1),
                        **physical.evaluate(TABLE.replace('GROUP', GROUP_JS)), **physical.evaluate(_INDUK_TABLE)})
                endpoint = ORIGIN + '/returnsheet/api/prefillreturnsheet/article-2126'
                requests = _requests(_observations(capture, record, scope), endpoint, record['record_id'])
                if any(item['request_json'].get('onManualClick') is not False for item in requests):
                    return None
                binding['primary'] = {'endpoint': endpoint, 'requests': requests}
            else:
                wrapper = root.locator(container)
                if wrapper.count() != 1 or root.locator('ui-grid').count() != len(roles):
                    return None
                grids = wrapper.locator('ui-grid')
                if grids.count() != len(roles) or root.locator('table:visible').count() != len(roles):
                    return None
                for index, (suffix, group) in enumerate(roles):
                    table = grids.nth(index).locator('p-table')
                    if table.count() != 1 or not _turn_grid(page, table, max_pages, check_cancel):
                        return None
                    verify_detail_url(page.url, taxpayer, record['record_id'])
                    physical, marker = table.locator('table:visible'), table.locator('.p-paginator-current')
                    if physical.count() != 1 or marker.count() != 1:
                        return None
                    match = re.search(r'(?:of|dari)\s+([0-9]+)(?![0-9.,])', marker.inner_text(), re.I)
                    if not match:
                        return None
                    total = int(match[1])
                    metadata = physical.evaluate(TABLE.replace('GROUP', GROUP_JS))
                    if metadata['group'] != group or not metadata['headers'] or not all(metadata['headers']):
                        return None
                    endpoint = ORIGIN + '/returnsheet/api/loadarticle2126/' + suffix + '-grid'
                    pages = _pages(_observations(capture, record, scope), endpoint, record['record_id'], total)
                    binding['tables'].append({'name': suffix, **metadata, 'endpoint': endpoint,
                                               'pages': pages, 'source_total': total})
            forms.append(binding)
        references = _reference_bindings(page, record, scope, capture, check_cancel)
        if references is None:
            return None
        next(form for form in forms if form['name'] == 'Induk')['references'] = references
        return forms
    except JsonSafetyError:
        raise
    except Exception:
        _check_cancel(check_cancel)
        return None
    finally:
        _observations(capture, record, scope)
