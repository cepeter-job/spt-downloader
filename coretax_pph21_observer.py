"""PPh21 navigation and metadata only; source values remain in captured JSON."""
import json
import re

from coretax_json import ORIGIN, JsonSafetyError
from coretax_corporate import _BUILD_HASH, _tabs, _turn_grid
from coretax_masa_bindings import MAIN_SOURCE, BUILD_DIGESTS as MASA_BUILD_DIGESTS
from coretax_masa_observer import TABLE, _PPN_MAIN_BUILD_HASH, _observations, _pages, _requests

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


def observe_pph21_forms(page, record, scope, capture, *, max_pages=1000, check_cancel=None):
    """Observe all five forms; this alone never grants native export coverage."""
    from coretax_browser import GROUP_JS, _check_cancel, list_taxpayer_id, verify_detail_url, wait_idle
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
            panel_id = tab.get_attribute('aria-controls')
            if not panel_id or tab.get_attribute('href') not in (None, '', '#', '#' + panel_id):
                return None
            target = '[id=' + json.dumps(panel_id) + ']'
            if view.locator(target).count() != 1:
                return None
            panel = view.locator(':scope > .p-tabview-panels > .p-tabview-panel' + target + ', '
                                 ':scope > .p-tabview-panels > p-tabpanel > .p-tabview-panel' + target)
            if panel.count() != 1:
                return None
            tab.click()
            wait_idle(page)
            verify_detail_url(page.url, taxpayer, record['record_id'])
            panel.wait_for(state='visible', timeout=30000)
            selector, container, roles = FORMS[name]
            root = panel.locator(selector)
            if root.count() != 1 or not root.is_visible():
                return None
            fields = root.evaluate(_FIELDS.replace('GROUP', GROUP_JS))
            if fields is None:
                return None
            binding = {'name': name, 'fields': fields, 'tables': [], 'builds': dict(builds), **environment}
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
        return forms
    except JsonSafetyError:
        raise
    except Exception:
        _check_cancel(check_cancel)
        return None
    finally:
        _observations(capture, record, scope)
