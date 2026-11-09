# Single pin source (kill duplicate digest constants)

Baseline main: c4dadb9 (PR #203 merge). Sequenced after PR #204 (Badan
pin refresh): this branch rebases onto main after #204 lands.

## Problem

`resources/build-pins.json` is the reviewed-data source, but two digest
constants duplicate it (and must be re-synced on every vendor/CIT roll):

- `coretax_corporate.CIT_SOURCE_SHA256` (copied via
  `coretax_browser.observe_corporate_forms` as `approved_digest`).
- `coretax_json.REFERENCE_ORDER_SHA256` (vendor reference-order digest).

## Fix

Initialise both from `coretax_build_pins.load_build_pins()` at import
(`None` when the pin is missing, so equality checks fail closed to DOM).
No logic changes; chunk filenames stay in code (they are route structure,
not pin data).

## Tests

- Existing suites patch `coretax_json.REFERENCE_ORDER_SHA256` and
  `driver.CIT_SOURCE_SHA256`; keep both names importable and patchable.
- New: missing-pin refusal (loader returns `{}` → `None` → refuse).
