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
never widen the allowlist, and the reviewed bundle stays authoritative
whenever it matches.
"""
import contextlib
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


def _load_overlay():
    target = local_pins_path()
    if target is None:
        return {}
    try:
        data = json.loads(target.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        return _valid(data.get('digests')) or {}
    except Exception:
        return {}


def load_build_pins(path=None):
    """Return {url: sha256} from the reviewed pin file, or {} if unusable.

    An explicit ``path`` is read verbatim (tests and tooling). The default
    reviewed bundle is merged with the local overlay, which may only override
    digests for URLs the reviewed file already pins.
    """
    try:
        root = Path(__file__).resolve().parent
        target = Path(path) if path is not None else root / 'resources' / 'build-pins.json'
        raw = target.read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        digests = _valid(data.get('digests'))
        if digests is None:
            return {}
    except Exception:
        # A broken pin file must never crash startup or grant native
        # eligibility; DOM fallback is the safe default.
        return {}
    if path is None:
        for url, digest in _load_overlay().items():
            if url in digests:
                digests[url] = digest
    return digests


def record_local_pins(digests):
    """Atomically record auto-measured digests in the user-scoped overlay.

    Returns False when the overlay cannot be written, so the caller keeps the
    fail-closed DOM fallback rather than admitting an unrecorded build.
    """
    target = local_pins_path()
    if target is None:
        return False
    clean = _valid(digests)
    if clean is None:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump({'version': 1, 'digests': clean}, fh,
                          indent=2, sort_keys=True)
            os.replace(tmp, target)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
        return True
    except Exception:
        return False


def clear_local_pins():
    """Drop the overlay (used by tests and by a manual reset)."""
    target = local_pins_path()
    if target is None:
        return
    with contextlib.suppress(OSError):
        target.unlink()
