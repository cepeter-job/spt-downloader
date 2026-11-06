# PPh21 build digest pin refresh

Baseline main: fa139513743024dc0c5108269edc3bbde58802b1 (PR #193 merge).

## Evidence

Live test 6 Nov 2026 on the PR #193 build: `pph21.observer_gate` =
`build_digest` then DOM fallback (COMPLETE run). The gate instrumentation
did its job — it named the stale pin instead of the generic
`forms_unavailable`.

## Live measurement

Read from the logged-in Coretax page via CDP (same-origin fetch,
SHA-256 over response bytes, same algorithm as the observer):
- `/returnsheets/id-ID/main.cccfdb820c20596c.js` → `5535c900…f454`
- `/returnsheets/id-ID/803.8681206e4827011e.js` → `5535c900…f454`

Both pinned URLs still return 200 and now serve identical bytes;
both pins were stale. Stable across repeat fetches. (The `/home/id-ID/`
shell bundle `main.5caf661a…js` is a different app surface and is not
the returnsheets pin.)

## Design

Update only the two digest constants. URLs unchanged (both live).
This also re-enables native PPN/Unifikasi eligibility, which shares
`MAIN_SOURCE`. Fixture digests are synthetic-local and unaffected.

## Verification

CI, then live rerun: expect `detail.source=native_verified` for
PPh 21/26 (or the next honest gate if the structure has changed).
