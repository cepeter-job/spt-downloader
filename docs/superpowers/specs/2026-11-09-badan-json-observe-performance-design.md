# Corporate `json_observe` performance — measured, proof-preserving follow-up

Original proposal: 2026-11-09. Review corrections / status: 2026-11-10.
Scope: design and measurement planning **only** in PR #208, separated from
the correctness change in #207. Changes to production traversal, pagination
or source admission require their own reviewed implementation PRs.

## What the recorded runs actually establish

The initial observation used build/workflow `42595786607` (the #206-era
artifact). The capture accumulated **572 responses by the end of interactive
observation**, not when the SPT was first opened. Do not infer prefetch
availability or complete source coverage from the final count alone.

| Recorded phase | Initial run (ms) |
| --- | ---: |
| `json_observe` | **595,725** |
| `json_project` | 20,099 |
| `list_restore` | 17,772 |
| `open_detail` | 756 |

The reported full `return_detail` took approximately **1,139,400 ms**,
including subsequent fallback DOM work. Hence `json_observe` was about
**52.3% of the complete detail phase**, or **96.7% of only
`json_observe + json_project`**. The earlier `~92% of the detail phase`
description was incorrect. The difference from the four rows above is
other work, including the DOM fallback; do not label those four rows the
whole detail phase.

The later **#207 merged-build** `ecaabbc4` / run `42605722871`
reported `json_observe = 581,213.81 ms` and
`json_project = 11,545.97 ms`. It still selected
`dom / adapter_ineligible` and had independent `pdf.partial` evidence.
These are **two build-specific, incomplete/fallback observations**, not
a controlled before/after optimization benchmark and not a successful
`native_verified` run. Corporate live acceptance remains tracked in
[#161](https://github.com/cepeter-job/spt-downloader/issues/161).

The original run's private, value-free request inventory indicated **466
L3-B page requests with `Rows=10` and `TotalRecords=4654`**, out of
572 captured responses. This makes pagination a candidate, **not a
measured causal attribution**. Do not treat all 572 as independently
necessary source requests or as arrivals before navigation. The current
pinned-build tab inventory is **15 observed tabs** (L1-B and L8 absent),
not the 17-tab count assumed in this original proposal.

## Current code and status of measurement

**Step 0a — coarse observer-stage measurement: implemented on `main`.**
Commit [`0bfacd1`](https://github.com/cepeter-job/spt-downloader/commit/0bfacd14e873d22c44836d6afa8b408016f24ce6)
introduced `corporate.observe_timing` with a fixed stage name,
`duration_ms` and optional `form_ordinal`, emitted for completed
segments and normal refusal paths. The implementation distinguishes
`build`, `tabs`, `tab`, `panel`, `form` and specialized
`l3`/`l11a`/other observed-form stages. This is **coarse
attribution only**: a long `l3` segment does not by itself distinguish
paginator clicking, marker polling, overlay waits, source requests or
other observer work. No post-instrumentation build-matched live
per-substage analysis is established by this design document.

The reviewed `_turn_grid.advance` path clicks the existing native
paginator, **polls the visible page marker approximately every 100 ms**
with a **30-second marker-change deadline**, then invokes `wait_idle`
(loading-overlay wait, up to approximately 45 seconds, plus stabilization).
It **does not call `wait_for_response`**. Per-page hashing, response
waiting and request latency must not be asserted as measured bottlenecks
without separate evidence.

Other *unranked hypotheses* include tab/panel render churn, duplicate
L4 footer requests and repeated reviewed JavaScript-bundle hash reads.
Repeated request counts alone do not establish whether a response was
cached, retried, independently required or responsible for wall time.

## Next steps, in evidence-first order

### Step 0b — fine-grained, privacy-safe attribution (next implementation)

Instrument bounded, **fixed-enum** substeps within the existing observer
without changing source calls, control flow, request ownership or capture
admission:

- Per-form `tab_open`, panel readiness and form binding; per-grid
  `paginator_reset`, `paginator_advance`, `marker_change_wait`
  and `overlay_idle_wait`; separate build-pin fetch/verification.
- Report elapsed milliseconds, form ordinal, fixed grid category, page
  transition counts, total-page counts, and distinct request/response
  completion counts by fixed **endpoint category**. Preserve separate
  counts for requests already completed immediately after first detail
  open vs those completed after each navigation boundary.
- Define the first-open boundary from capture sequence/time metadata,
  with an explicit, same-attempt observation point. Bound counters and
  refuse ambiguous/unattributable timing events rather than treating
  unknown arrivals as initial prefetch.
- Correlate diagnostics via existing job/build/run/attempt context, but
  record **no** taxpayer/record identifiers, full URLs, body values,
  query parameters, raw sequence hashes, DOM business text or personal
  financial data. Fixed enum and aggregate counts only. Keep Stop,
  lifetime, build pins and refusal behavior unchanged.

**Gate:** one operator-authorized, build-matched completed live rerun with
a reconciled stage breakdown before selecting any optimization. A failed
native admission still yields useful timing evidence, but **is not**
success evidence for JSON-first capture.

### Step 1 — test native page-size control only if timings justify it

Where a named grid is demonstrably pagination-bound, inspect the **native
rows-per-page UI control** without reading business values. Only select
a supported option (for example `100` **if it is actually present**);
never synthesize authenticated `Rows=100` POST requests, assume an API
accepts that value or borrow the DOM fallback's unrelated 500-row cap.

Require unchanged same-record/scope/attempt and owned grid/request
bindings, original server `TotalRecords`, contiguous offsets with no
gaps/duplicates, full page/row ordering and actual UI-originated requests.
Preserve L3/L4/L11-A footers, references, source pins, provenance and
existing bounded Stop/timeout/fallback semantics. Compare the same
selected source before/after; reject optimization if the control is
absent, rebinding is ambiguous or any coverage assertion fails.

### Step 2 — optional reuse of already-arrived source packets

**Separate design approval required.** For every candidate captured
packet, prove whether it was completed before the first-open boundary or
only after interactive tab/pagination navigation. Require the same
selected record, scope, pinned build, capture attempt, request key,
original response sequence and component lifetime. Reuse is permitted
only with complete binding and all required page offsets, footer and
reference evidence. An early `CurrentFormData` response is **not**
evidence that L3-B, L4 or L11-A grids and footers were already loaded.
Any missing, late, conflicting or ambiguous packet follows the current
verified UI observation path; do not manufacture calls, shortcuts or
PDF completeness.

## Explicit safety boundaries

- No relaxation of `native_verified`, source/identity/build-pin checks,
  workbook reconciliation, original-value provenance, Stop, privacy or
  completion/publishing gates.
- No parallel paginator clicks or speculative authenticated requests.
- PDF retrieval/publication and `pdf.partial` are **independent** of
  JSON performance; faster `adapter_ineligible` is not acceptance.
- Documentation and diagnostics alone do not establish new performance
  gains, complete workbook output or live native eligibility.

## Acceptance and sequencing

1. **Measurement evidence:** reviewed, bounded per-grid and per-stage
   timings with request/response counts and opening-vs-navigation arrival
   chronology for an exact, identifiable build and capture attempt.
2. **Optional optimization:** a measured reduction in `json_observe`
   and page/request overhead relative to the **same selected SPT, same
   source total/scope and comparable live conditions**, with no
   regression in source eligibility, complete ordered rows or workbook
   values. Do not use an arbitrary `<596s` threshold alone.
3. **Integration:** targeted regressions for good/malformed pagination,
   replay, conflicting identity, Stop, changed owner and privacy; full
   exact-head portable, dependency/security, Windows shards, packaging,
   artifact-readback and bootstrap CI. Independent peer review and
   authorized merge required.
4. **Live acceptance:** install the exact verified merged artifact,
   obtain an operator-run id-ID `detail.source=native_verified` with
   full worksheet/source-count parity and independently verified
   financial-PDF custody/publication. Track this under #161, not as
   proof furnished by this design PR.

PR #208 should remain **design-only**; subsequent implementation PRs
must reference this plan and replace hypotheses with evidence.
