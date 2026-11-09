# Corporate json_observe performance proposal (follow-up, not #207)

Date: 2026-11-09
Prompt: PR #207 review requested the ~596-second `json_observe` effort to
stay a follow-up instead of being folded into the correctness patch.
Baseline: `main` @ `92d062d` (PR #206) + #207 in flight.

## Measured problem (live evidence)

Coretax Badan detail, merged build `42595786607`
(`returns/json/0001/b4c52138…`, 572 captured responses, complete):

| phase | duration |
| ----- | -------- |
| json_observe | **595,725 ms (≈10 min)** |
| json_project | 20,099 ms |
| list_restore | 17,772 ms |
| open_detail | 756 ms |

`json_observe` is ~92% of the detail phase. The capture already buffers all
572 responses — observe re-drives tab/pagination interactivity with no
sub-stage attribution.

## Candidate drivers (to verify, not assume)

1. **L3 pagination** — 466 of 572 requests are `l3-table-b-grid` pages at
   `Rows=10` (TotalRecords 4654). Each page click serializes: click →
   `wait_idle` — guarded `wait_for_response` with 30s deadline polling —
   hash/page bookkeeping. This phase alone can plausibly exceed 8 minutes.
2. **Tab/panel churn** — 17 panels clicked one by one with visibility checks
   and per-panel lifetime verification; each click pays a full render + idle
   wait even for already-arrived prefetches.
3. **Repeated identical fetches** — the L4 footer fires three times (two
   request shapes) because multiple lifecycle points re-query the same page;
   L3/L9 grids re-render on tab re-show.
4. **Unmeasured hashing** — the build-hash gate fetches 4+ JS chunks per run
   (cached no-store by design; sizes unverified here).

## Proposal (follow-up PR, ordered by signal)

### Step 0 — Measure before moving (diagnostics-only, fast)

Add stage timings to the observer: one privacy-safe
`corporate.observe_stage` diagnostic per stage (`build`, `tabs`, `tabs_done`,
per-grid pagination, `footers`, `final`) with enum stage names and counted
durations only — no URLs, digests, values, or page state. Mirrors the
`*.observer_gate` fixed-enum style. Confirm driver ranking on one live rerun
against:
- L3 pagination (predicted dominant),
- tab clicks + `wait_idle` wall time,
- hash fetch time.

### Step 1 — Page-size (only if Step 0 confirms pagination-bound)

For L3 (and L9/L11 where the backend honors it), request `Rows=100` if the
paginator rows-per-page control demonstrably offers it and the grid binding
declares it. Proof-preserving by construction: the adapter covers grids by
declared page keys, so a larger page is exactly the same
computed-`TotalRecords` coverage. Never guesstimate — probe the live paginator
controls first (fixed enum diagnostics kept values-free).

### Step 2 — Reuse already-arrived responses (design-heavy, optional)

Capture already holds the session's earliest responses (prefill + footers on
first view). The observer today re-clicks tabs to re-derive them. A
proof-preserving variant would let the binding layer accept capture-buffered
packets *only* when the full declared key/shape set is satisfied by them;
with any gap, the current interactivity runs. This is the largest structural
change and should not ceil the correctness effort — only pursue after
Steps 0–1 and only with a dedicated design doc.

## Explicit non-goals / guards

- No change to `native_verified` semantics, custody/privacy gates, build-pin
  gates, or fallback behavior.
- No Rows increase without live probe evidence of paginator support.
- No parallelization of paginator clicks (ordering is required by the
  `seen`-offset completeness checks).
- Observable subset: measured per-stage timings must exist before any
  correctness-facing optimization lands.

## Acceptance (for the eventual implementation PR)

- Live `json_observe` under the current ~596s budget, with a named reduction
  tied to the step-(0..2) measurement.
- Full CI green (incl. coverage ratchet), review, merge, and the standard
  build-matched live `native_verified` rerun.

## Click budget estimate

- Step 0: small (diagnostics-only, ~1 PR).
- Step 1: medium (proof of `Rows=100`, binding/fixtures, ~1 PR).
- Step 2: large (dedicated design + implementation, may be split).
