"""Build-pin allowlist loader: reviewed data, fail-closed when absent.

The live Coretax frontend has redeployed twice in one day, each time
breaking native capture silently until someone re-measured the JS hashes.
Pins therefore live in resources/build-pins.json (reviewed data) instead
of scattered Python constants; a missing or malformed file yields an
empty allowlist, which fails closed to DOM capture.

A redeploy still needs no release: when the observer sees a build it does
not recognise it re-measures the assets the reviewed file already pins and
records them in a user-scoped overlay (build-pins.local.json). The overlay
can only supply digests for URLs the reviewed file already lists, so it can
never widen the allowlist, and it is stamped with the reviewed bundle it was
measured against -- shipping a new reviewed file invalidates it, so the
reviewed bundle stays authoritative whenever it changes.
"""
import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

_DIGEST = re.compile(r'\A[0-9a-f]{64}\Z')
_LOCAL_NAME = 'build-pins.local.json'


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


def _load_overlay(base):
    """Return the overlay digests, or {} when it was measured against another bundle."""
    target = local_pins_path()
    if target is None:
        return {}
    try:
        data = json.loads(target.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        # An overlay measured against a retired reviewed bundle must not
        # override the bundle that replaced it.
        if data.get('base') != base:
            return {}
        return _valid(data.get('digests')) or {}
    except Exception:
        # An unreadable overlay is simply absent; the reviewed pins still apply.
        return {}


def load_build_pins(path=None):
    """Return {url: sha256} from the reviewed pin file, or {} if unusable.

    An explicit ``path`` is read verbatim (tests and tooling). The default
    reviewed bundle is merged with the local overlay, which may only override
    digests for URLs the reviewed file already pins.
    """
    if path is not None:
        return _read_pins(path)
    reviewed = _reviewed()
    if not reviewed:
        return {}
    merged = dict(reviewed)
    for url, digest in _load_overlay(_base(reviewed)).items():
        if url in merged:
            merged[url] = digest
    return merged


def record_local_pins(digests):
    """Atomically record auto-measured digests in the user-scoped overlay.

    Returns False when the overlay cannot be written, so the caller keeps the
    fail-closed DOM fallback rather than admitting an unrecorded build. The
    overlay is stamped with the reviewed bundle it was measured against.
    """
    target = local_pins_path()
    if target is None:
        return False
    clean = _valid(digests)
    reviewed = _reviewed()
    if clean is None or not reviewed:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump({'version': 1, 'base': _base(reviewed), 'digests': clean},
                          fh, indent=2, sort_keys=True)
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