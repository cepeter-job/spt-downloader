"""Read a public, metadata-only update manifest without accessing GitHub or OneDrive.

The endpoint is intentionally disabled until a maintainer creates and verifies
an owned Cloudflare Pages site from the approved office network. A new release
must set the exact HTTPS endpoint in this source and pass CI before activation.
"""
from dataclasses import dataclass
from datetime import date
import json
import re
from urllib import error, parse, request

from .build_info import is_valid_build_info

# Activation requires a separate, reviewed commit after the real Pages endpoint
# exists. Do not guess a hostname or accept an environment-supplied endpoint.
MANIFEST_URL = ''
MAX_BYTES = 4096
HTTP_TIMEOUT_SECONDS = 5


class UpdateLookupError(ValueError):
    """Expected, non-sensitive failure; callers must not display exception text."""


@dataclass(frozen=True)
class UpdateNotice:
    version: str
    published_at: str
    notes: str
    commit: str
    run_id: str
    run_attempt: int


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url):
    """Permit only one exact HTTPS JSON path on a Pages project, never a URL from a response."""
    if not isinstance(url, str):
        raise UpdateLookupError('invalid update endpoint')
    try:
        parsed = parse.urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UpdateLookupError('invalid update endpoint') from exc
    if (parsed.scheme != 'https' or not host or port is not None
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path != '/latest.json'
            or re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\.pages\.dev', host) is None
            or parsed.netloc != host):
        raise UpdateLookupError('invalid update endpoint')
    return url


def _strict_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate key')
        result[name] = value
    return result


def parse_manifest(raw):
    """Reject ambiguous metadata and unsafe prose; never parse executable/download URLs."""
    try:
        data = json.loads(raw, object_pairs_hook=_strict_pairs)
        if not isinstance(data, dict) or set(data) != {
                'schema', 'version', 'published_at', 'notes',
                'commit', 'run_id', 'run_attempt'}:
            raise ValueError('fields')
        version, published, notes = data['version'], data['published_at'], data['notes']
        commit, run_id, attempt = data['commit'], data['run_id'], data['run_attempt']
        if type(data['schema']) is not int or data['schema'] != 1:
            raise ValueError('schema')
        if (not isinstance(version, str) or
                re.fullmatch(r'[1-9][0-9]{3}\.(?:0|[1-9][0-9]?)\.(?:0|[1-9][0-9]?)', version) is None):
            raise ValueError('version')
        if (not isinstance(published, str) or
                re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', published) is None):
            raise ValueError('published')
        date.fromisoformat(published)
        if (not isinstance(notes, str) or len(notes) > 320 or
                any(ord(char) < 32 or ord(char) == 127 for char in notes)):
            raise ValueError('notes')
        if not isinstance(commit, str) or re.fullmatch(r'[0-9a-f]{40}', commit) is None:
            raise ValueError('commit')
        if (not isinstance(run_id, str) or
                re.fullmatch(r'[1-9][0-9]{0,23}', run_id) is None):
            raise ValueError('run_id')
        if type(attempt) is not int or not 1 <= attempt <= 1_000_000:
            raise ValueError('run_attempt')
        return UpdateNotice(version, published, notes, commit, run_id, attempt)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise UpdateLookupError('invalid update manifest') from exc


def newer_than_installed(notice, installed):
    """A later verified Actions run may notify. Never compare Git hashes as versions.

    This is conservative: an installed build with an unknown or later run ID
    receives no notification, even when its commit differs from the release.
    """
    if not isinstance(notice, UpdateNotice) or not is_valid_build_info(installed):
        return False
    return notice.commit != installed['commit'] and int(notice.run_id) > int(installed['run_id'])


def fetch_notice(url, installed, *, opener=None):
    """Bounded one-shot read; no cookies, auth, redirects, telemetry, or downloads."""
    if not is_valid_build_info(installed):
        return None
    validate_url(url)
    headers = {
        'User-Agent': 'SPTDownloader-UpdateCheck/1.0',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
    }
    req = request.Request(url, headers=headers, method='GET')
    opener = request.build_opener(_NoRedirect()) if opener is None else opener
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if (response.status != 200 or response.geturl() != url
                    or response.headers.get_content_type().lower() != 'application/json'):
                raise UpdateLookupError('unexpected update response')
            raw = response.read(MAX_BYTES + 1)
    except (OSError, ValueError, error.URLError, error.HTTPError) as exc:
        raise UpdateLookupError('update check unavailable') from exc
    if len(raw) > MAX_BYTES:
        raise UpdateLookupError('oversized update response')
    notice = parse_manifest(raw)
    return notice if newer_than_installed(notice, installed) else None
