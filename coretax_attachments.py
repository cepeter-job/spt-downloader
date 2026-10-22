"""Read existing corporate financial PDFs without remote document actions."""
from spt_desktop import diagnostics
import base64
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import stat
from urllib.parse import urlparse
import uuid

from coretax_browser import list_taxpayer_id, trusted_origin, verify_detail_url
from coretax_exporter import FINANCIAL_LABELS
from coretax_financial_post import FinancialPost, verify_sources
from spt_desktop.output_windows import DirectoryGuard, locked_file

MAX_PDF_BYTES = 20 * 1024 * 1024
_DOWNLOAD_TIMEOUT_MS = 30000
_LABELS = FINANCIAL_LABELS
POST_SOURCE_PINS = {
    '/returnsheets/id-ID/525.ec1edffbb4a91d20.js':
        'fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d',
    '/returnsheets/id-ID/main.cccfdb820c20596c.js':
        '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
}

_SCAN = r'''() => {
    const roots = document.querySelectorAll('.main-content');
    if (roots.length !== 1) return {controls: [], observations: []};
    const root = roots[0], labels = new Set(__LABELS__);
    const visible = el => !!el.getClientRects().length &&
        !['hidden','collapse'].includes(getComputedStyle(el).visibility) &&
        !el.closest('[hidden],[aria-hidden="true"]');
    const boundary = '.p-tabview-panel,.p-panel,p-panel,.p-accordion-tab,p-accordiontab,section,fieldset,.main-content';
    const owner = el => el.closest(boundary);
    const headings = 'label,legend,h1,h2,h3,h4,h5,h6,.p-panel-title,.p-accordion-header-text';
    const approved = el => el && visible(el) && typeof el.innerText==='string' &&
        labels.has(el.innerText.trim()) ? el.innerText : null;
    const attachmentTable = table => {
        const rows = table.tHead ? [...table.tHead.rows] : [];
        return rows.length === 1 && JSON.stringify([...rows[0].cells].map(c=>c.innerText.trim())) ===
            JSON.stringify(['NO.','FILENAME','TINDAKAN']);
    };
    const tableLabel = table => {
        // Bind only the observed attachment-table shape, never an arbitrary grid.
        if (!attachmentTable(table)) return null;
        if (table.hasAttribute('aria-labelledby')) {
            const ids = table.getAttribute('aria-labelledby').trim().split(/\s+/);
            if (ids.length !== 1 || !ids[0]) return null;
            const matches = [...document.querySelectorAll('[id]')].filter(el=>el.id===ids[0]);
            if (matches.length !== 1 || !root.contains(matches[0]) || owner(matches[0]) !== owner(table)) return null;
            const label = approved(matches[0]);
            // Explicit contradictory/hidden ownership cannot fall back to nearby text.
            if (table.caption && approved(table.caption)?.trim() !== label?.trim()) return null;
            return label;
        }
        if (table.caption) return approved(table.caption);
        const candidates = [];
        for (let node=table; node && node!==owner(table); node=node.parentElement) {
            if (node!==table && node.matches('table')) return null;
            for (let sibling=node.previousElementSibling; sibling; sibling=sibling.previousElementSibling) {
                if (sibling.matches('table,'+boundary) || sibling.querySelector('table,'+boundary)) return null;
                const found = [...(sibling.matches(headings)?[sibling]:[]), ...sibling.querySelectorAll(headings)]
                    .filter(visible);
                candidates.push(...found);
            }
            if (candidates.length) return candidates.length===1 && owner(candidates[0])===owner(table)
                ? approved(candidates[0]) : null;
        }
        return null;
    };
    // Pengamatan struktur sendiri tidak mengizinkan request.
    const tables = [...root.querySelectorAll('table')].filter(visible).filter(attachmentTable);
    const observations = [];
    for (const table of tables) {
        const candidates = [...table.querySelectorAll('a,button,input,[role="button"]')]
            .filter(visible).filter(el=>el.closest('table')===table);
        const bound = !!tableLabel(table);
        for (const el of candidates.length ? candidates : [null]) {
            observations.push({attachment_tables: tables.length, candidate_controls: candidates.length,
                control_kind: el ? ({A:'anchor',BUTTON:'button',INPUT:'input'}[el.tagName]||'other') : 'none',
                binding_state: !el ? 'no_control' : bound ? 'bound' : 'unbound',
                href_present: !!el && el.hasAttribute('href'),
                handler_present: !!el && ['onclick','onmousedown','onpointerdown'].some(name=>el.hasAttribute(name))});
        }
    }
    const controls = [...root.querySelectorAll('a, button, input')].filter(visible).map(el => {
        const direct = el.innerText || el.value || el.getAttribute('aria-label') || '';
        const table = el.tagName==='A' ? el.closest('table') : null;
        const label = labels.has(direct.trim()) ? direct : table ? tableLabel(table) : null;
        if (!label) return null;
        return {label,
                href: el.tagName === 'A' ? el.getAttribute('href') : null,
                resolved_href: el.tagName === 'A' ? el.href : null,
                document_url: window.location.href,
                unsafe: el.tagName !== 'A' || el.hasAttribute('onclick') ||
                        el.hasAttribute('onmousedown') || el.hasAttribute('onpointerdown')};
    }).filter(Boolean);
    const forms = [...root.querySelectorAll('rshshr-citr-main-form')].filter(visible);
    if (forms.length === 1) {
        for (const table of tables) {
            const label = tableLabel(table), grid = table.closest('ui-grid-documents');
            if (!label || !grid || table.closest('rshshr-citr-main-form') !== forms[0] ||
                grid.querySelectorAll('table').length !== 1) continue;
            for (const body of table.tBodies) for (const row of body.rows) {
                const cells = [...row.cells];
                const actions = [...row.querySelectorAll('a,button,input,[role="button"]')].filter(visible);
                if (!visible(row) || cells.length !== 3 || cells.some(c=>c.colSpan!==1 || c.rowSpan!==1) ||
                    !/^\d+$/.test(cells[0].innerText.trim()) ||
                    !/\.pdf$/i.test(cells[1].innerText.trim()) || actions.length !== 1) continue;
                const button = actions[0];
                if (button.tagName !== 'BUTTON' || button.getAttribute('type') !== 'button' ||
                    button.getAttribute('title') !== 'Unduh' || button.disabled ||
                    button.getAttribute('aria-disabled') === 'true' || !cells[2].contains(button) ||
                    !button.classList.contains('p-button-secondary') ||
                    button.querySelectorAll('.pi.pi-download').length !== 1 ||
                    ['onclick','onmousedown','onpointerdown'].some(name=>button.hasAttribute(name))) continue;
                // WeakMap mengikat node asli; clone identik tidak mewarisi izin.
                if (!window._spt_financial_nodes) Object.defineProperty(window, '_spt_financial_nodes',
                    {value: new WeakMap(), configurable: true});
                const nodes = window._spt_financial_nodes;
                if (!nodes.has(button)) nodes.set(button, crypto.randomUUID());
                controls.push({label, method: 'POST', document_url: window.location.href,
                    button_index: [...root.querySelectorAll('button')].indexOf(button),
                    identity: nodes.get(button), row_text: row.innerText,
                    filename: cells[1].innerText});
            }
        }
    }
    if (!tables.length && !controls.length) observations.push({attachment_tables: 0,
        candidate_controls: 0, control_kind: 'none', binding_state: 'no_control',
        href_present: false, handler_present: false});
    return {controls, observations};
}'''.replace('__LABELS__', json.dumps(sorted(_LABELS)))

_START = r'''async ({key, url, limit, timeout, document_url, method='GET', body, headers}) => {
    // A Python-side scope check cannot bind a later browser evaluation.
    if (window.location.href !== document_url) {
        throw new Error('Inspected financial document changed before request');
    }
    const controller = new AbortController();
    const state = {controller, reader: null, total: 0, timer: null};
    Object.defineProperty(window, key, {value: state, configurable: true});
    state.timer = setTimeout(() => controller.abort(), timeout);
    try {
        const response = await fetch(url, {method, credentials: 'same-origin', body,
            redirect: 'error', cache: 'no-store', signal: controller.signal,
            headers: headers || {Accept: 'application/pdf'}});
        const length = response.headers.get('content-length');
        const type = (response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
        if (!response.ok || response.url !== url || response.redirected || type !== 'application/pdf' ||
            (length !== null && (!/^\d+$/.test(length) || Number(length) > limit)) || !response.body) {
            controller.abort();
            throw new Error('Unsupported financial response');
        }
        state.reader = response.body.getReader();
    } catch (error) {
        controller.abort();
        clearTimeout(state.timer);
        delete window[key];
        throw new Error('Financial PDF request was not accepted');
    }
}'''

_READ = r'''async ({key, limit}) => {
    const state = window[key];
    if (!state || !state.reader) throw new Error('Financial stream is unavailable');
    const {done, value} = await state.reader.read();
    if (done) return {done: true};
    state.total += value.byteLength;
    if (state.total > limit) {
        state.controller.abort();
        throw new Error('Financial PDF byte limit exceeded');
    }
    let binary = '';
    for (let start = 0; start < value.length; start += 32768) {
        binary += String.fromCharCode(...value.subarray(start, start + 32768));
    }
    return {done: false, data: btoa(binary)};
}'''

_CLOSE = r'''key => {
    const state = window[key];
    if (state) {
        state.controller.abort();
        clearTimeout(state.timer);
        if (state.reader) state.reader.cancel().catch(() => {});
        delete window[key];
    }
}'''


def _cancel(check_cancel):
    if check_cancel:
        check_cancel()


def _include_folder(guard, folder):
    expected = {}
    for path in reversed((folder, *folder.parents)):
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & 0x400):
            raise ValueError('Financial output path is not an ordinary directory')
        expected[path] = (info.st_dev, info.st_ino)
    guard.include(expected)


def _partial(label, reason):
    return {'label': label, 'relative_path': '', 'status': 'PARTIAL',
            'bytes': 0, 'hash': '', 'reason': reason}


def _release_nodes(page):
    try:
        page.evaluate('() => {delete window._spt_financial_nodes;}')
    except Exception:
        pass


def _verify_page(page, record):
    identifier = record.get('record_id')
    if not isinstance(identifier, str) or not identifier or len(identifier) > 512:
        raise ValueError('Financial download requires an inspected return identifier')
    taxpayer = list_taxpayer_id(record.get('list_url'))
    verify_detail_url(page.url, taxpayer, identifier)


def _read_pdf(page, url, check_cancel, document_url, request=None):
    key = '_spt_financial_' + uuid.uuid4().hex
    data = bytearray()
    try:
        _cancel(check_cancel)
        arguments = {'key': key, 'url': url, 'limit': MAX_PDF_BYTES,
                     'timeout': _DOWNLOAD_TIMEOUT_MS, 'document_url': document_url}
        if request is not None:
            arguments.update(request)
        page.evaluate(_START, arguments)
        _cancel(check_cancel)
        while True:
            _cancel(check_cancel)
            chunk = page.evaluate(_READ, {'key': key, 'limit': MAX_PDF_BYTES})
            _cancel(check_cancel)
            if chunk['done']:
                break
            value = base64.b64decode(chunk['data'], validate=True)
            if len(data) + len(value) > MAX_PDF_BYTES:
                raise ValueError('Financial PDF byte limit exceeded')
            data.extend(value)
        if not data.startswith(b'%PDF-') or not data.rstrip().endswith(b'%%EOF'):
            raise ValueError('Financial response is not a complete PDF byte stream')
        return bytes(data)
    finally:
        # A destroyed/navigated document already owns cleanup of its readers;
        # never let cleanup replace cancellation or expose a browser exception.
        try:
            page.evaluate(_CLOSE, key)
        except Exception:
            pass


def _financial_url(page_url, control):
    href = control.get('href')
    if (control.get('unsafe') or not isinstance(href, str) or not href
            or href != href.strip() or '\\' in href or any(ord(char) < 32 for char in href)):
        raise ValueError('Financial control is not an inspected ordinary href')
    if control.get('document_url') != page_url:
        raise ValueError('Financial control belongs to a changed detail document')
    # Resolusi anchor browser memperhitungkan <base> dan normalisasi URL;
    # href mentah tetap diperiksa agar normalisasi tidak menyamarkan input terlarang.
    url = control.get('resolved_href')
    if (not isinstance(url, str) or not trusted_origin(url) or urlparse(url).fragment
            or not urlparse(url).path.lower().endswith('.pdf')):
        raise ValueError('Financial href is outside the supported PDF contract')
    return url


@diagnostics.traced('pdf')
def download_financial_attachments(page, record, folder, check_cancel=None):
    """Return byte/hash metadata for observed PDFs; never swallow Stop.

    The caller must invoke this on the inspected visible corporate Induk and
    declare returned files in its scoped checkpoint/export manifest. No file is
    automatically authorized for public Downloads just because it exists here.
    """
    _cancel(check_cancel)
    if not isinstance(record, dict):
        raise ValueError('Financial capture requires an inspected return record')
    _verify_page(page, record)
    folder = Path(folder)
    if '..' in folder.parts:
        raise ValueError('Financial output cannot contain parent traversal')
    folder = folder.absolute()
    results = []
    sources = None
    with ExitStack() as lifecycle, DirectoryGuard() as guard:
        lifecycle.callback(_release_nodes, page)
        _include_folder(guard, folder)
        scanned = page.evaluate(_SCAN)
        _cancel(check_cancel)
        for observation in scanned['observations']:
            diagnostics.record('pdf.discovery', phase='pdf', **observation)
        controls = [item for item in scanned['controls'] if item['label'].strip() in _LABELS]
        if not controls:
            diagnostics.record('pdf.partial', phase='pdf', level='WARNING')
            return [_partial('', 'No supported financial PDF control was observed')]
        for control in controls:
            _cancel(check_cancel)
            label = control['label']
            try:
                with ExitStack() as operation:
                    _verify_page(page, record)
                    transport = None
                    if control.get('method') == 'POST':
                        if sources is None:
                            try:
                                sources = verify_sources(page, POST_SOURCE_PINS,
                                    control['document_url'], check_cancel)
                            except Exception:
                                sources = False
                                raise
                        if sources is False:
                            raise ValueError('Financial source build is not supported')
                        transport = operation.enter_context(FinancialPost(page, record, control,
                            POST_SOURCE_PINS, sources, _SCAN, _verify_page, check_cancel))
                        url = transport.url
                        data = _read_pdf(page, url, check_cancel, control['document_url'],
                                         request=transport.request())
                        identity = transport.identity()
                    else:
                        url = _financial_url(page.url, control)
                        data = _read_pdf(page, url, check_cancel, control['document_url'])
                        identity = url

                    def check_scope():
                        _cancel(check_cancel)
                        _verify_page(page, record)
                        if transport is not None:
                            transport.verified()

                    check_scope()
                    record_key = hashlib.sha256(record['record_id'].encode('utf-8')).hexdigest()[:32]
                    # POST mengikat URL dan hash body, tanpa menyimpan header/ID.
                    url_key = hashlib.sha256(identity.encode('utf-8')).hexdigest()
                    name = f'LK_{record_key}_{url_key}.pdf'
                    target = folder / name
                    if target.exists():
                        # Retry hanya menerima byte identik; tidak mengganti file lama.
                        with locked_file(target) as existing:
                            digest, size = hashlib.sha256(), 0
                            for chunk in iter(lambda: existing.read(1048576), b''):
                                check_scope()
                                size += len(chunk)
                                if size > len(data):
                                    raise ValueError('Existing financial PDF differs from the inspected response')
                                digest.update(chunk)
                            check_scope()
                            if size != len(data) or digest.hexdigest() != hashlib.sha256(data).hexdigest():
                                raise ValueError('Existing financial PDF differs from the inspected response')
                    else:
                        created = None
                        try:
                            check_scope()
                            with target.open('xb') as stream:
                                created = target.lstat()
                                check_scope()
                                stream.write(data)
                                stream.flush()
                                check_scope()
                        except BaseException:
                            # Bersihkan inode milik kita saja, tanpa menutupi Stop.
                            if created is not None:
                                try:
                                    current = target.lstat()
                                    if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                                        target.unlink()
                                except OSError:
                                    pass
                            raise
                    results.append({'label': label, 'relative_path': target.relative_to(folder).as_posix(),
                                    'status': 'COMPLETE', 'bytes': len(data),
                                    'hash': hashlib.sha256(data).hexdigest()})
            except Exception as error:
                diagnostics.record('pdf.partial', phase='pdf', level='WARNING', error=error)
                _cancel(check_cancel)
                results.append(_partial(label, 'Observed financial PDF could not be verified or saved'))
    _cancel(check_cancel)
    return results
