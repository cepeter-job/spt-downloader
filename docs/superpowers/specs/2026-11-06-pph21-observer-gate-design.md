# PPh21 observer gate diagnostic

Baseline main: f1fcbfde79407bc0bc71f06f47952324a97036f8.

## Evidence

Live PPh 21/26 run 6 Nov 2026 (build f1fcbfd): `detail.source` =
`source_requested=json-first`, `source_used=dom`,
`source_reason=forms_unavailable` with `json_observe` done in 427 ms.
The native observer bailed at an early strict gate, but the log could
not say which — the same reason appeared in the previous two PPh21
runs, so DOM fallback is the norm, not a regression.

## Design

Every `return None` in `observe_pph21_forms` (and
`_reference_bindings`) now records `pph21.observer_gate` with a fixed
allowlisted category (build_digest, tab_set, environment, tab_disabled,
tab_caption, panel, form_root, fields, grid_structure, table_shape,
total, reference, reference_bindings, evaluation_error,
unsupported_tax). No values, offsets, identities or payloads. Behavior
is unchanged: the observer still fails closed to DOM; this only makes
the refusal attributable.

## Verification

`tests/test_pph21_json_observer.py` defect fixtures pin the recorded
gate per defect (changed-build → build_digest, missing/extra-form →
tab_set, invalid-group → table_shape, extra-ui-grid → grid_structure,
unknown-status-label → fields, ambiguous-status → fields). Full
CI, then the next live run names the actual gate.
