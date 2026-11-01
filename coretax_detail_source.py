"""Literal capture-mode validation shared by GUI and backend entrypoints."""


def validate_detail_source(value):
    """Keep the opt-in literal identical across launcher, worker and collector."""
    if type(value) is not str or value not in ('dom', 'json-first'):
        raise ValueError('Detail source must be dom or json-first.')
    return value
