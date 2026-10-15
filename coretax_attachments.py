"""Read existing corporate financial PDFs without remote document actions."""
import base64
import hashlib
from pathlib import Path
import stat
from urllib.parse import urlparse
import uuid

from coretax_browser import list_taxpayer_id, trusted_origin, verify_detail_url
from spt_desktop.output_windows import DirectoryGuard, locked_file

MAX_PDF_BYTES = 20 * 1024 * 1024
_DOWNLOAD_TIMEOUT_MS = 30000
_LABELS = {'Laporan Keuangan', 'Laporan Keuangan yang Telah Diaudit*'}

_SCAN = r'''() => [...document.querySelectorAll('a, button, input')]
    .filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
    .map(el => ({label: el.innerText || el.value || el.getAttribute('aria-label') || '',
                href: el.tagName === 'A' ? el.getAttribute('href') : null,
                resolved_href: el.tagName === 'A' ? el.href : null,
                document_url: window.location.href,
                unsafe: el.tagName !== 'A' || el.hasAttribute('onclick') ||
                        el.hasAttribute('onmousedown') || el.hasAttribute('onpointerdown')}))'''

_START = r'''async ({key, url, limit, timeout, document_url}) => {
    // A Python-side scope check cannot bind a later browser evaluation.
    if (window.location.href !== document_url) {
        throw new Error('Inspected financial document changed before request');
    }
    const controller = new AbortController();
    const state = {controller, reader: null, total: 0, timer: null};
    Object.defineProperty(window, key, {value: state, configurable: true});
    state.timer = setTimeout(() => controller.abort(), timeout);
    try {
        const response = await fetch(url, {method: 'GET', credentials: 'same-origin',
            redirect: 'error', cache: 'no-store', signal: controller.signal,
            headers: {Accept: 'application/pdf'}});
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


def _verify_page(page, record):
    identifier = record.get('record_id')
    if not isinstance(identifier, str) or not identifier or len(identifier) > 512:
        raise ValueError('Financial download requires an inspected return identifier')
    taxpayer = list_taxpayer_id(record.get('list_url'))
    verify_detail_url(page.url, taxpayer, identifier)


def _read_pdf(page, url, check_cancel, document_url):
    key = '_spt_financial_' + uuid.uuid4().hex
    data = bytearray()
    try:
        _cancel(check_cancel)
        page.evaluate(_START, {'key': key, 'url': url, 'limit': MAX_PDF_BYTES,
                               'timeout': _DOWNLOAD_TIMEOUT_MS, 'document_url': document_url})
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
    # Native anchor resolution includes document <base> and URL normalization;
    # raw-href checks above remain required even when the resolved URL is safe.
    url = control.get('resolved_href')
    if (not isinstance(url, str) or not trusted_origin(url) or urlparse(url).fragment
            or not urlparse(url).path.lower().endswith('.pdf')):
        raise ValueError('Financial href is outside the supported PDF contract')
    return url


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
    with DirectoryGuard() as guard:
        _include_folder(guard, folder)
        controls = [item for item in page.evaluate(_SCAN) if item['label'].strip() in _LABELS]
        _cancel(check_cancel)
        if not controls:
            return [_partial('', 'No supported financial PDF control was observed')]
        for control in controls:
            _cancel(check_cancel)
            label = control['label']
            try:
                _verify_page(page, record)
                url = _financial_url(page.url, control)
                data = _read_pdf(page, url, check_cancel, control['document_url'])
                _verify_page(page, record)
                _cancel(check_cancel)
                record_key = hashlib.sha256(record['record_id'].encode('utf-8')).hexdigest()[:32]
                # Bind the flat filename to the return as well as the observed
                # URL: identical hrefs on distinct SPTs must never share a file.
                url_key = hashlib.sha256(url.encode('utf-8')).hexdigest()
                name = f'LK_{record_key}_{url_key}.pdf'
                target = folder / name
                if target.exists():
                    # Retry PARTIAL boleh memakai byte identik dari GET terbaru,
                    # tetapi tidak boleh mengganti file lama atau mengikuti symlink.
                    with locked_file(target) as existing:
                        digest, size = hashlib.sha256(), 0
                        for chunk in iter(lambda: existing.read(1048576), b''):
                            _cancel(check_cancel)
                            size += len(chunk)
                            if size > len(data):
                                raise ValueError('Existing financial PDF differs from the inspected response')
                            digest.update(chunk)
                        _cancel(check_cancel)
                        if size != len(data) or digest.hexdigest() != hashlib.sha256(data).hexdigest():
                            raise ValueError('Existing financial PDF differs from the inspected response')
                else:
                    created = None
                    try:
                        with target.open('xb') as stream:
                            created = target.lstat()
                            _cancel(check_cancel)
                            stream.write(data)
                            stream.flush()
                            _cancel(check_cancel)
                    except BaseException:
                        # Exclusive creation grants cleanup of our inode only; a
                        # name substituted by another writer is never our consent.
                        if created is not None:
                            try:
                                current = target.lstat()
                                if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                                    target.unlink()
                            except OSError:
                                # Jangan tutupi pembatalan asli dengan kegagalan cleanup.
                                # Byte yang tersisa tetap privat, tanpa deklarasi COMPLETE.
                                pass
                        raise
                results.append({'label': label, 'relative_path': target.relative_to(folder).as_posix(),
                                'status': 'COMPLETE', 'bytes': len(data),
                                'hash': hashlib.sha256(data).hexdigest()})
            except Exception:
                _cancel(check_cancel)
                results.append(_partial(label, 'Observed financial PDF could not be verified or saved'))
    _cancel(check_cancel)
    return results
