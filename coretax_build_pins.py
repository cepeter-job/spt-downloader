"""Build-pin allowlist loader: reviewed data, fail-closed when absent.

The live Coretax frontend redeploys without notice, rotating the hashed
filename of every chunk. Pins therefore live in resources/build-pins.json
(reviewed data) instead of scattered Python constants; a missing or malformed
file yields an empty allowlist, which fails closed to DOM capture.

A redeploy needs no release. When the observer sees a build it does not
recognise it discovers what the portal currently serves, re-measures those
assets, and records them in a user-scoped overlay keyed by *role* rather than
by URL (build-pins.local.json, version 2). Keying by role is what makes a
rename self-healing: the overlay can follow a chunk to its new filename,
where a URL-keyed overlay could only ever override digests for URLs the
reviewed file already listed.

The overlay is stamped with the reviewed bundle it was measured against, so
shipping a new reviewed file invalidates it and the reviewed bundle stays
authoritative whenever it changes. Admission still requires the re-measured
CIT asset to equal the digest the page actually loaded, and the structural
checks in the observer remain the real gate on the build.
"""
import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

_DIGEST = re.compile(r'\A[0-9a-f]{64}\Z')
_CHUNK_ID = re.compile(r'(\d{3,4})\.[0-9a-f]{16}\.js\Z')
_LOCAL_NAME = 'build-pins.local.json'
_OVERLAY_VERSION = 2

# The numeric chunk id is stable across rotations; only its hash changes. That
# is what lets a role follow a rename. Ids are the ones the reviewed bundle
# pins, so an unrecognised id degrades to a chunkN role instead of colliding.
_ROLE_BY_CHUNK = {'525': 'cit', '803': 'l1', '640': 'l2', '693': 'l3'}


def _valid(digests):
    """Return a clean {url: digest} copy, or None when anything is unusable."""
    if not isinstance(digests, dict) or not digests:
        return None
    for url, digest in digests.items():
        if not isinstance(url, str) or not url.startswith('https://'):
            return None
        if not isinstance(digest, str) or not _DIGEST.match(digest):
            return None
    return dict(digests)


def role_for_url(url):
    """Map a pinned URL to its stable role, never echoing the URL itself."""
    name = url.rsplit('/', 1)[-1]
    if name.startswith('main.'):
        return 'main'
    if name.startswith('vendor.'):
        return 'vendor'
    found = _CHUNK_ID.match(name)
    if found:
        return _ROLE_BY_CHUNK.get(found.group(1), 'chunk' + found.group(1))
    return 'other'


def local_pins_path():
    """User-scoped overlay written when a redeploy is auto-admitted."""
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_STATE_HOME')
    if not base:
        return None
    return Path(base) / 'SPTDownloader' / _LOCAL_NAME


def _read_pins(target):
    """Read one pin file verbatim; anything unusable yields an empty allowlist."""
    try:
        data = json.loads(Path(target).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        return _valid(data.get('digests')) or {}
    except Exception:
        # A broken pin file must never crash startup or grant native
        # eligibility; DOM fallback is the safe default.
        return {}


def _reviewed():
    """The reviewed bundle, read verbatim and never merged with the overlay."""
    root = Path(__file__).resolve().parent
    return _read_pins(root / 'resources' / 'build-pins.json')


def _base(digests):
    """Stable identity of a reviewed bundle, so a new release drops the overlay."""
    canonical = json.dumps(digests, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _overlay():
    """Return the raw overlay document, or {} when absent or unusable."""
    target = local_pins_path()
    if target is None:
        return {}
    try:
        data = json.loads(target.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return {}
        # A version 1 overlay was URL-keyed and cannot follow a rename; a
        # version 2 one is role-keyed. Anything else is ignored.
        if data.get('version') != _OVERLAY_VERSION:
            return {}
        roles = data.get('roles')
        if not isinstance(roles, dict):
            return {}
        return data
    except Exception:
        # An unreadable overlay is simply absent; the reviewed pins still apply.
        return {}


def _roles(base):
    """Overlay roles measured against this reviewed bundle, else {}."""
    data = _overlay()
    if not data or data.get('base') != base:
        # An overlay measured against a retired reviewed bundle must not
        # override the bundle that replaced it.
        return {}
    return data['roles']


def resolve_role_url(role, default):
    """The URL a role currently resolves to: overlay first, reviewed default.

    This is what lets a renamed chunk be picked up without a release: the
    overlay records the new filename under the same role.
    """
    entry = _roles(_base(_reviewed())).get(role)
    if isinstance(entry, dict):
        url = entry.get('url')
        if isinstance(url, str) and url.startswith('https://'):
            return url
    return default


def load_build_pins(path=None):
    """Return {url: sha256} from the reviewed pin file, or {} if unusable.

    An explicit ``path`` is read verbatim (tests and tooling). The default
    reviewed bundle is merged with the local overlay, which may override the
    digest of a URL the reviewed file pins and may add the new URL a role has
    moved to. It can never widen the allowlist beyond the roles the reviewed
    file defines.
    """
    if path is not None:
        return _read_pins(path)
    reviewed = _reviewed()
    if not reviewed:
        return {}
    merged = dict(reviewed)
    known = {role_for_url(url) for url in reviewed}
    for role, entry in _roles(_base(reviewed)).items():
        if role not in known or not isinstance(entry, dict):
            continue
        url, digest = entry.get('url'), entry.get('digest')
        if not isinstance(url, str) or not _valid({url: digest}):
            continue
        merged[url] = digest
    return merged


def record_local_pins(digests):
    """Atomically record auto-measured digests in the user-scoped overlay.

    Returns False when the overlay cannot be written, so the caller keeps the
    fail-closed DOM fallback rather than admitting an unrecorded build. The
    overlay is stamped with the reviewed bundle it was measured against and
    keyed by role, so a later rename is followed instead of refused.
    """
    target = local_pins_path()
    if target is None:
        return False
    clean = _valid(digests)
    reviewed = _reviewed()
    if clean is None or not reviewed:
        return False
    known = {role_for_url(url) for url in reviewed}
    roles = {}
    for url, digest in clean.items():
        role = role_for_url(url)
        if role in known:
            roles[role] = {'url': url, 'digest': digest}
    if not roles:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump({'version': _OVERLAY_VERSION, 'base': _base(reviewed),
                           'roles': roles}, fh, indent=2, sort_keys=True)
            os.replace(tmp, target)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
        return True
    except Exception:
        # An unwritable overlay must not crash the run; the caller keeps the
        # fail-closed DOM fallback instead of admitting an unrecorded build.
        return False


def clear_local_pins():
    """Drop the overlay (used by tests and by the explicit reset command)."""
    target = local_pins_path()
    if target is None:
        return
    with contextlib.suppress(OSError):
        target.unlink()