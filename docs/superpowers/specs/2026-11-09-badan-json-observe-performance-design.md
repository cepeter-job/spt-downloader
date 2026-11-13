# Corporate `json_observe` performance — measured, proof-preserving follow-up

Original proposal: 2026-11-09. Updated evidence/status: **2026-11-11**.
Scope: design and measurement planning **only** in PR #208. The production
instrumentation and performance implementation were separately reviewed,
tested and merged through [#234](https://github.com/cepeter-job/spt-downloader/pull/234)
and [#236](https://github.com/cepeter-job/spt-downloader/pull/236); this
proposal **does not** change either of their runtime contracts. Corporate L7
native correctness and DOM initial-loading diagnostics are independently
tracked by [#235](https://github.com/cepeter-job/spt-downloader/pull/235)
(open at this update).

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
other observer work. The following original readings are historical; **#234 later
added aggregated per-paginator timing**, and #236 added owned-probe timing.
Request/response arrival chronology remains unmeasured. See the 11 November
section below before selecting another optimization.

### Historical stage timings, 10 November 2026 — read-only local logs

Inspected the **locally retained privacy-safe diagnostic events** on
DESKTOP-FR702P6, without copying taxpayer identities, raw response payloads,
URLs or output filenames into the repository. The latest completed run **for this historical comparison** uses
merge commit [`4e84bfb`](https://github.com/cepeter-job/spt-downloader/commit/4e84bfb253ec4d4eeb3c7ec9f3ea2d4b67592921)
(PR #215), build workflow `42744813416`, attempt 1. The preceding
instrumented comparison build is `7f250af`, workflow `42717280592`,
attempt 1. These are **different builds**, not proof of identical SPT
scope or a controlled performance improvement.

| Diagnostic (duration) | Earlier `7f250af` | Latest `4e84bfb` |
| --- | ---: | ---: |
| `phase.completed:json_observe` | 671,744.93 ms | **582,493.19 ms** |
| `phase.completed:json_project` | 15,011.88 ms | 12,683.06 ms |
| `phase.completed:return_detail` (includes DOM fallback) | 1,257,907.63 ms | **1,120,792.14 ms** |
| Stage `l3` | **475,541.5 ms** | **414,012.9 ms** |
| `l3` share of `json_observe` | **70.8%** | **71.1%** |
| Combined stage `grid` | 53,164.3 ms | 48,251.0 ms |
| Combined stage `panel` | 47,881.8 ms | 39,662.6 ms |
| Stage `l11a` | 23,560.1 ms | 23,720.5 ms |
| Stage `build` | 21,681.4 ms | 16,012.5 ms |

Both runs emitted **67 `corporate.observe_timing` records**. In the
10 November run, `json_observe` was about **52.0%** of the full
`return_detail` interval. The `l3` stage clearly dominates
**observer-stage wall time** in both runs; this does **not** establish
how its time is divided across paginator clicks, marker polling,
overlay wait, backend responses or processing.

**Crucial acceptance distinction:** both runs requested `json-first`
but emitted `detail.source: dom / adapter_ineligible`, recorded
`pdf.partial`, and subsequently hit a DOM table elapsed-budget
refusal. The 10 November run reached `operation.finished: PARTIAL` by
10:22:54 WIB, not COMPLETE. Its PDF was PARTIAL **at that time**;
the later 11 November runs reported completed PDF attachments but still
PARTIAL SPT capture. Neither run proves `native_verified` or validates an
optimized JSON-first workload.

**Historical priority decision (10 November):** separate L3 reset/advance,
marker-change, overlay wait and request/response attribution. The first
part has since been delivered by #234 and #236, but initial-versus-navigation
request/response chronology remains open. Only after the relevant source
proof should a native page-size control be considered. Panel/grid timing
remains a secondary hypothesis.

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

## Verified 11 November 2026 follow-up — #234 diagnostics and #236 optimization

The operator executed the **same selected large Corporate SPT and tax scope**
on DESKTOP-FR702P6 using the #234 artifact (`428cc6c` source build,
workflow `42951082441`) and the #236 artifact (`ad042af6` CI PR
merge ref, workflow `42963381072`). The latter build has the **same Git
tree** as squash-merged [`main` `8281fe58`](https://github.com/cepeter-job/spt-downloader/commit/8281fe58a2bf8298bd33157b5dd9f77c5fbe27e0).
Both runs selected the same record and scope but **their inventory SHA-256
digests differ**, so the snapshots and environment must not be called fully
identical. All numbers below come from locally retained sanitized diagnostic
events, not uploaded taxpayer files.

| Timed component | #234 baseline | #236 candidate | Difference |
| --- | ---: | ---: | ---: |
| `json_observe` | 608.725 s | **586.130 s** | -22.595 s (-3.71%) |
| `corporate.observe_timing: l3` | 437.925 s | **418.143 s** | -19.782 s (-4.52%) |
| Owned L3-B `native.paginator_timing: total` | 435.430 s | **414.997 s** | -20.433 s (-4.69%) |
| Native L3-B Next advances | 465 | 465 | unchanged |
| `return_detail`, including DOM fallback | 1,211.158 s | **998.835 s** | -212.323 s (-17.53%) |
| Source decision | DOM / `adapter_ineligible` | DOM / `adapter_ineligible` | unchanged |
| Terminal status | **PARTIAL** | **PARTIAL** | unchanged |

Only the primary L3-B paginator is shown in the paginator row, **not the sum
over all 19 native paginator invocations**. In both runs 465 Next actions
visited 466 native source pages for a 4,654-row, observed `Rows=10` grid.
The newer exact-head instrumented implementation retained the owned 10-row
request/offset contract; no native rows-per-page dropdown was verified
for a safe 100-row alternative, and the unrelated DOM 500-row cap is **not**
native page-size evidence.

| L3-B substep for 465 Next actions | #234 | #236 |
| --- | ---: | ---: |
| `advance_overlay_wait` | 221.161 s | 211.741 s |
| `advance_click` | 34.665 s | 72.763 s |
| `advance_marker_wait` | 16.426 s | 20.503 s |
| Old `other` host/locator residual | 163.178 s | not comparable |
| New `advance_probe` (owned marker/control lookup) | not instrumented | 109.946 s |
| New residual `other` | not comparable | about 0.04 s |

The #236 change replaces repeated locator checks with a single
`NATIVE_PAGINATOR_INSPECT_JS` evaluation on the original `p-table`,
then a guarded `NATIVE_PAGINATOR_CLICK_JS` evaluation. It does **not**
remove source work, skip pages, shorten overlay waits, weaken control
actionability or bypass Stop. The probe now measures formerly unattributed
work, so the fall in `other` from 163 s to near zero is **reclassification,
not a 163-second speedup**. Click time was higher in #236. The measured
total is approximately 20.4 s lower, but this is **one run per build with
different inventory hashes**; do not advertise a causal, reproducible
performance win without controlled repetitions.

### Acceptance status and separate correctness failures

- **#234 run:** `json-first` fell back to DOM. The DOM L3-B capture
  reached an elapsed-budget refusal at `before_dom_read`, after one
  500-row page of 4,654, leaving the run PARTIAL.
- **#236 run:** native source remained `dom / adapter_ineligible`, with
  retained manifest reason **`unverified_corporate_l7_main_lifecycle`**
  (not a pagination-speed refusal). Subsequent DOM L3 table ordinal 3
  raised a `TimeoutError`; its incomplete L3-B table was not included
  among the 36 other complete tables. Overall `capture_complete=false`,
  `run.complete=false`, terminal **PARTIAL** at **12:59:52 WIB**.
- The #236 run's financial PDF attachment is marked **COMPLETE**, and
  workbook export, verification and publication phases completed; these
  do **not** prove that the Corporate workbook has complete SPT content.
- This is **neither** native JSON admission **nor** full 4,654-row
  capture acceptance. Keep [issue #161](https://github.com/cepeter-job/spt-downloader/issues/161)
  OPEN and address strict L7/DOM diagnostics in the independently reviewed
  [PR #235](https://github.com/cepeter-job/spt-downloader/pull/235).
  Do not claim that a performance PR repairs L7, a PDF or a DOM timeout.

### Updated implementation status

1. **Stage 0a: DONE** — coarse `corporate.observe_timing`.
2. **Stage 0b/part 1: DONE** — #234 fixed-enum reset/advance click,
   marker-change, overlay/settling, total/other aggregate times. These
   timings include normal refusal and Stop paths.
3. **Stage 0b/part 1 follow-up: DONE** — #236 owned-probe RPC
   optimization and `reset_probe`/`advance_probe` timing, independently
   reviewed and merged to `main`; one operator live follow-up remains
   PARTIAL, with only preliminary timing improvement.
4. **Stage 0b/part 2: OPEN** — separately bound, privacy-safe,
   first-open-vs-navigation request/response completion counts and
   correlation to fixed endpoint categories; no early prefetch inference.
5. **Stage 1 native page size: NOT APPROVED** — inspect the real owned
   native dropdown first and prove it supports a larger option and emits
   originally UI-triggered, complete contiguous source requests; never
   synthesize `Rows=100` POSTs. Source admission must remain fail-closed.
6. **Stage 2 packet reuse: NOT APPROVED** — requires separate
   design/security review and complete same-attempt source/lifetime proof.

## Next steps, in evidence-first order

### Step 0b — remaining request/response chronology (proposed)

Extend the already merged, bounded, **fixed-enum** native timing events
without changing source calls, control flow, request ownership or capture
admission. Do not reimplement #234/#236 or duplicate their probes:

- Retain merged per-grid `reset_probe`, `advance_probe`, reset/advance
  click, marker-change, overlay wait and total timings. Add only any
  justified fixed form/grid category or pin-verification timestamps
  that the current existing events cannot explain.
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

**Gate:** the #236 operator-run has supplied measured step timings, but
was PARTIAL, with no native admission and differing inventory checksum.
Before approving further optimization, obtain source-compatible repeat
measurements, verify UI ownership for any new control, and establish a
concrete bottleneck and complete acceptance criteria. Incomplete native
admission supplies diagnostic evidence **only**, not JSON-first success.

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

1. **Measurement evidence:** #234/#236 aggregated per-grid and per-stage
   timing is implemented and has a preliminary same-SPT comparison;
   request/response completion counts and opening-vs-navigation arrival
   chronology remain **pending** for any proposal relying on packet reuse
   or fewer source fetches.
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
4. **Live acceptance:** the #236 merged-tree artifact was verified and
   run but returned PARTIAL (L7 refusal plus DOM L3 timeout), so the
   end-to-end gate remains **open**. Require an operator-run id-ID
   `detail.source=native_verified`, complete L3-B 4,654-row source-
   to-workbook parity and independently verified financial-PDF custody/
   publication, or a separately supported fully complete DOM fallback.
   Track this under #161, not as proof furnished by design PR #208.

PR #208 remains **design-only** and should be rebased/synchronized with
current `main` before review. Merged #234/#236 are completed stages,
not changes delivered by this design document. Any next runtime proposal
must link exact-build evidence and remain independent of the open #235
correctness gate.
