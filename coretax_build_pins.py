"""Build-pin allowlist loader: reviewed data, fail-closed when absent.

The live Coretax frontend has redeployed twice in one day, each time
breaking native capture silently until someone re-measured the JS hashes.
Pins therefore live in resources/build-pins.json (reviewed data) instead
of scattered Python constants; a missing or malformed file yields an
empty allowlist, which fails closed to DOM capture.
"""
import json
import re
from pathlib import Path

_DIGEST = re.compile(r'\A[0-9a-f]{64}\Z')


def load_build_pins(path=None):
    """Return {url: sha256} from the reviewed pin file, or {} if unusable."""
    try:
        root = Path(__file__).resolve().parent
        target = Path(path) if path is not None else root / 'resources' / 'build-pins.json'
        raw = target.read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        digests = data.get('digests')
        if not isinstance(digests, dict) or not digests:
            return {}
        for url, digest in digests.items():
            if not isinstance(url, str) or not url.startswith('https://'):
                return {}
            if not isinstance(digest, str) or not _DIGEST.match(digest):
                return {}
        return dict(digests)
    except Exception:
        # A broken pin file must never crash startup or grant native
        # eligibility; DOM fallback is the safe default.
        return {}
