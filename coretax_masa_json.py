"""Native Masa response safety; never grants eligibility from requests alone."""
from urllib.parse import urlparse

from coretax_json import (
    JsonSafetyError,
    _corporate_privacy,
    _corporate_selected,
    _corporate_url,
)

_PREFILL_PATHS = frozenset({
    '/returnsheet/api/prefillreturnsheet/nvat',
    '/returnsheet/api/prefillreturnsheet/withholding-tax',
})
_GRID_PREFIXES = ('/returnsheet/api/loadndvat/', '/returnsheet/api/loadwtr/')


def check_masa_request_identities(observations, record, scope):
    """Reject observed contradictions before build/form eligibility is tested.

    The existing selected-record helper validates literal scope and URL identity;
    it does not impose corporate tax codes or corporate primary payload shapes.
    Check both Masa families: an unexpected family must not hide another return.
    """
    selected = _corporate_selected(record, scope)
    for event in observations:
        if not isinstance(event, dict):
            raise JsonSafetyError('Masa request observation is invalid')
        _corporate_privacy(event)
        url = event.get('url')
        if not _corporate_url(url):
            raise JsonSafetyError('Masa request origin is unauthorized')
        path = urlparse(url).path
        if path in _PREFILL_PATHS:
            identity_key = 'RecordId'
        elif path.startswith(_GRID_PREFIXES):
            identity_key = 'ReturnSheetRecordId'
        else:
            continue
        request = event.get('request_json')
        if not isinstance(request, dict) or identity_key not in request:
            # Absence is not proof of identity. The adapter separately requires
            # full bindings; continue so a later contradiction cannot be hidden.
            continue
        if type(request[identity_key]) is not str or request[identity_key] != selected['record_id']:
            raise JsonSafetyError('Observed Masa request contradicts selected return')
