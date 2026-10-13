"""Pure presentation state. Only the controller can certify a job's result."""
from dataclasses import dataclass, replace
import re
from typing import Mapping


@dataclass(frozen=True)
class Counters:
    processed: int | None = None
    total: int | None = None
    verified: int | None = None
    scanned: int | None = None


@dataclass(frozen=True)
class ExportState:
    job_id: str | None = None
    view_state: str = 'idle'
    stage: str | None = None
    percent: int | None = 0
    npwp: str = ''
    year: str = ''
    inventory: Counters | None = None
    details: Counters | None = None
    selected_count: int | None = None
    terminal_status: str | None = None
    output: str | None = None
    consent: tuple[str, str] | None = None


_STAGE_STATES = {
    'authentication': 'authenticating', 'inventory': 'inventory',
    'details': 'capturing', 'export': 'exported', 'publish': 'publishing',
}
_TERMINAL_STATES = {
    'COMPLETE': 'complete', 'PARTIAL': 'partial', 'CANCELLED': 'cancelled',
    'BLOCKED': 'blocked', 'ERROR': 'error',
}
_STOPPING = frozenset({'stopping', 'cancellation_pending'})


def scope_errors(npwp: str, year: str) -> dict[str, str]:
    """Identify the field to correct without changing the user's literal input."""
    errors = {}
    if not isinstance(npwp, str) or not re.fullmatch(r'[0-9]{16}', npwp):
        errors['npwp'] = 'form.npwp.error'
    if (not isinstance(year, str) or not re.fullmatch(r'[0-9]{4}', year)
            or not 1900 <= int(year) <= 2100):
        errors['year'] = 'form.year.error'
    return errors


def begin_export(job_id: str, npwp: str, year: str) -> ExportState:
    if not isinstance(job_id, str) or not job_id:
        raise ValueError('An accepted export must have a job ID')
    return ExportState(job_id=job_id, npwp=npwp, year=year,
                       view_state='preparing', percent=None)


def _counters(event: Mapping[str, object]) -> Counters | None:
    values = {name: event.get(name) for name in ('processed', 'total', 'verified', 'scanned')}
    if all(value is None for value in values.values()):
        return None
    if any(name in event and (type(value) is not int or value < 0)
           for name, value in values.items()):
        return None
    # Check every known pair, including verified/total when processed is absent.
    for lower, upper in (('verified', 'processed'), ('processed', 'total'), ('verified', 'total')):
        if values[lower] is not None and values[upper] is not None and values[lower] > values[upper]:
            return None
    return Counters(**values)


def reduce_export(state: ExportState, event: Mapping[str, object], *,
                  controller_active: bool) -> ExportState:
    if not state.job_id or event.get('job_id') != state.job_id or state.terminal_status:
        return state
    kind = event.get('type')
    percent = event.get('percent')
    if kind == 'terminal':
        status = event.get('status')
        if (controller_active or not isinstance(status, str) or status not in _TERMINAL_STATES
                or type(percent) is not int or not 0 <= percent <= 100
                or (status == 'COMPLETE') != (percent == 100)):
            return state
        if state.view_state in _STOPPING and status == 'COMPLETE':
            return state
        output = event.get('output')
        if output is not None and (not isinstance(output, str) or not output or len(output) > 4096):
            return state
        if status == 'COMPLETE' and not output:
            return state
        view_state = _TERMINAL_STATES[status]
        if (status == 'COMPLETE' and state.details is not None
                and state.details.processed == state.details.total == state.details.verified == 0):
            view_state = 'empty_complete'
        return replace(state, view_state=view_state, terminal_status=status, percent=percent,
                       output=output if status in ('COMPLETE', 'PARTIAL') else None, consent=None)
    if not controller_active or state.view_state in _STOPPING or state.consent is not None:
        return state
    if kind == 'setup':
        return replace(state, view_state='preparing', percent=None)
    if type(percent) is not int or not 0 <= percent < 100:
        return state
    if kind in ('selection_required', 'overwrite_required'):
        request_id = event.get('request_id')
        if not isinstance(request_id, str) or not re.fullmatch(r'[0-9a-f]{32}', request_id):
            return state
        consent_kind = kind.removesuffix('_required')
        return replace(state, view_state='awaiting_' + consent_kind,
                       percent=percent, consent=(consent_kind, request_id))
    if kind == 'login_required':
        return replace(state, view_state='login_required', stage='authentication', percent=percent)
    stage = event.get('stage')
    if kind != 'progress' or not isinstance(stage, str) or stage not in _STAGE_STATES:
        return state
    changes = {'view_state': _STAGE_STATES[stage], 'stage': stage, 'percent': percent}
    if stage in ('inventory', 'details'):
        changes[stage] = _counters(event)
    return replace(state, **changes)


def mark_stopping(state: ExportState) -> ExportState:
    if not state.job_id or state.terminal_status or state.view_state == 'stopping':
        return state
    return replace(state, view_state='stopping', consent=None)


def record_reply(state: ExportState, *, job_id: str, kind: str, request_id: str,
                 selected_count: int | None = None, overwrite: bool | None = None) -> ExportState:
    """Record a controller-accepted reply, never grant consent from presentation."""
    if (job_id != state.job_id or state.consent != (kind, request_id)
            or state.terminal_status or state.view_state in _STOPPING):
        return state
    if kind == 'selection' and type(selected_count) is int and selected_count > 0:
        return replace(state, view_state='selection_submitted',
                       selected_count=selected_count, consent=None,
                       details=Counters(processed=0, total=selected_count, verified=0))
    if kind == 'overwrite' and type(overwrite) is bool:
        return replace(state, view_state='publishing' if overwrite else 'cancellation_pending', consent=None)
    return state
