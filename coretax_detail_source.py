"""Literal capture-mode validation; json-only is for Corporate CLI capture only."""


def validate_detail_source(value):
    """Validate known literals; CLI and collector enforce json-only Corporate scope."""
    if type(value) is not str or value not in ('dom', 'json-first', 'json-only'):
        raise ValueError('Detail source must be dom, json-first or json-only.')
    return value
