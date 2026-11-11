"""Non-installing, public update notice; no GitHub or OneDrive API access.

An operator manually deploys an informational JSON response at an owned Worker
URL after accepting the exact released source-main Windows build.
"""
from dataclasses import dataclass
import json
import re
from urllib import error, request

from .build_info import is_valid_build_info

# This is the exact user-authorized public Cloudflare Worker. Its response
# currently has no manifest; invalid/empty responses cause no notification.
MANIFEST_URL = 'https://divine-hill-13fc.punzer4.workers.dev/'
MAX_BYTES = 4096
HTTP_TIMEOUT_SECONDS = 5


class UpdateLookupError(ValueError):
    """Network/format errors; do not display the exception to end users."""


@dataclass(frozen=True)
class UpdateNotice:
    commit: str
    run_id: str
    run_attempt: int


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url):
    """Only the approved Worker root; never use a URL supplied by the manifest."""
    if url != MANIFEST_URL:
        raise UpdateLookupError('unapproved update endpoint')
    return url


def _strict_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate key')
        result[name] = value
    return result


def parse_manifest(raw):
    """Require exact public build coordinates; refuse extra fields or links."""
    try:
        data = json.loads(raw, object_pairs_hook=_strict_pairs)
        if not isinstance(data, dict) or set(data) != {
                'schema', 'commit', 'run_id', 'run_attempt'}:
            raise ValueError('unexpected fields')
        commit, run_id, attempt = data['commit'], data['run_id'], data['run_attempt']
        if type(data['schema']) is not int or data['schema'] != 1:
            raise ValueError('schema')
        if not isinstance(commit, str) or re.fullmatch(r'[0-9a-f]{40}', commit) is None:
            raise ValueError('commit')
        if not isinstance(run_id, str) or re.fullmatch(r'[1-9][0-9]{0,23}', run_id) is None:
            raise ValueError('run_id')
        if type(attempt) is not int or not 1 <= attempt <= 1_000_000:
            raise ValueError('run_attempt')
        return UpdateNotice(commit, run_id, attempt)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise UpdateLookupError('invalid update manifest') from exc


def newer_than_installed(notice, installed):
    """Only notify for a newer manually approved Actions run; never sort SHAs."""
    return (isinstance(notice, UpdateNotice) and is_valid_build_info(installed)
            and notice.commit != installed['commit']
            and int(notice.run_id) > int(installed['run_id']))


def fetch_notice(url, installed, *, opener=None):
    """Read only public metadata; bounded, HTTPS, no redirects or telemetry."""
    if not is_valid_build_info(installed):
        return None
    validate_url(url)
    req = request.Request(url, headers={
        'User-Agent': 'SPTDownloader-UpdateCheck/1.0',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
    }, method='GET')
    opener = request.build_opener(_NoRedirect()) if opener is None else opener
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if (response.status != 200 or response.geturl() != url
                    or response.headers.get_content_type().lower() != 'application/json'):
                raise UpdateLookupError('unexpected update response')
            raw = response.read(MAX_BYTES + 1)
    except (OSError, ValueError, TypeError, error.URLError, error.HTTPError) as exc:
        raise UpdateLookupError('update check unavailable') from exc
    if len(raw) > MAX_BYTES:
        raise UpdateLookupError('oversized update response')
    notice = parse_manifest(raw)
    return notice if newer_than_installed(notice, installed) else None
