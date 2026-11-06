# Versioned build-pin allowlist + unfamiliar-build diagnostic

Baseline main: 48c510cb7cbc7067ace0b284b6b13ed5328cad6d (PR #196 merge).
PR #197 (main.bed1449/803.3216 + PPN/Unifikasi chunks) is the current
measured baseline; this design builds on top of its pins.

## Evidence

Two consecutive Coretax redeploys broke native capture twice in one day:
(1) pins went stale silently (generic `forms_unavailable`), (2) round-1
re-measurement hashed the SPA index HTML because the legacy JS URLs now
serve `text/html` fallback — pinning an HTML digest would have "passed"
the hash check against HTML bytes while the observer's content-type
gate rejected them. PR #193's `pph21.observer_gate` named the gate, but
no diagnostic records *what the live build looked like*, so every
redeploy still costs a manual CDP session.

## Design

1. **Pins as reviewed data.** `resources/build-pins.json`
   `{version: 1, digests: {<source URL>: <sha256>, ...}}` is the single
   reviewed allowlist of live build digests. Python constants
   (`BUILD_DIGESTS` etc.) are sourced from this file at import time;
   a missing/corrupt file fails closed (empty set → DOM fallback, so
   tests monkeypatching constants keep working).
2. **Structured unfamiliar-build diagnostic.** On a digest mismatch,
   observers record `build.unfamiliar_build` with fixed enums only:
   `build_source {main, article, ppn_chunk, unifikasi_chunk, corporate,
   vendor, pdf_guard}`, never URLs/digests, plus a byte count for the
   observed asset. Privacy-safe per the project invariants (no values,
   offsets, identities, payloads). Behavior is unchanged: DOM fallback.
3. **Pin update flow.** One-line JSON change in a reviewed PR with
   live-measurement evidence (CDP fetch, byte count, digest), instead
   of editing N Python constants across four modules + fixtures.

Safety semantics unchanged: native eligibility still requires digest
membership in the reviewed set *and* every structural/adapter gate.
An unreviewed build is noticed (diagnostic) but never trusted.

## Verification

New tests: JSON loader (valid/missing/corrupt → fail-closed), one
observer path recording the event on an unfamiliar digest, and the
refresh PR template. CI, then live rerun (native_verified expected for
PPh 21/26/PPN/Unifikasi with PR #197 pins).
