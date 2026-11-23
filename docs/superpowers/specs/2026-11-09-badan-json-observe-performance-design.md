# Corporate `json_observe` performance — measured, proof-preserving follow-up

Original proposal: 2026-11-09. Updated evidence/status: **2026-11-23** (20 November baseline archived).
Scope: design and measurement planning **only** in PR #208. The production
instrumentation and performance implementation were separately reviewed,
tested and merged through [#234](https://github.com/cepeter-job/spt-downloader/pull/234)
and [#236](https://github.com/cepeter-job/spt-downloader/pull/236); this
proposal **does not** change either of their runtime contracts. Corporate L7
native correctness and DOM initial-loading diagnostics are independently
tracked by [#235](https://github.com/cepeter-job/spt-downloader/pull/235)
(merged as `8726aae`; see current status below).

## Current baseline and decision — 23 November 2026

Baseline: [main `61dce51`](https://github.com/cepeter-job/spt-downloader/commit/61dce517e221cece74b4cef79f251be54fe39c80)
(merged #339). This section **supersedes the 20 November status section below**;
older measurements and acceptance gates remain historical evidence. This PR
is **documentation/design only**: synchronizing it must not alter scraping,
source admission, workbook values, parallelism, Stop or CI policy.

### What is now merged, and what remains open

| Track | Status as of 23 Nov |
| --- | --- |
| Native observer timing, owned paginator probes | #234/#236 merged; do not mistake residual reclassification for a speedup |
| Corporate strict CLI JSON-only | #327 merged; still refuses unsupported source without DOM detail-value fallback |
| Data-conditional/nullable Corporate roots | #328/#329/#330/#331/#332 merged; preserve required-form and present-but-unproved refusals |
| L11-B null totals, L10-A metadata and visibility, L9 details/footer, L10-B custody | #333/#334/#335/#336/#337 merged |
| L10-C gate reason and custody-vs-projection classification, L11-B quarter precision | #339 merged; diagnostic does not itself admit Amendment L10-C |
| Six privacy-safe L10-C `history_*` gate subreasons | [#340](https://github.com/cepeter-job/spt-downloader/pull/340) OPEN: regression/CI/peer review and a fresh live diagnostic are separate gates |
| Complete L3 domestic DOM `TOTAL` → reviewed `JUMLAH` footer shape | [#341](https://github.com/cepeter-job/spt-downloader/pull/341) OPEN: exact-shape candidate with three-table/60-row regressions; needs CI/merge and live workbook acceptance |
| First-open versus navigation response chronology (Stage 0b part 2) | Not implemented by #339/#340; separately design and review only after source-compatible measurements |
| Native larger page size / packet reuse | NOT APPROVED, with no synthetic authenticated requests or speculative replay |

### Latest available selected-scope live evidence (not a controlled benchmark)

The 23 November GUI worker `c2bb6ed` (PR #339 test build, workflow
`45115019738`, `frozen=false`) finished **COMPLETE** for two submitted
2025 Corporate returns. The previous comparable GUI worker used `e894f12`
(workflow `45046507796`). These are two builds, each observed once; they are
**not** an A/B proof of code-caused performance change or independent release
acceptance of main `61dce51`.

| Observed outcome | Normal | Amendment 001 |
| --- | --- | --- |
| Selected detail source | JSON / `native_verified` | DOM / `projection_incomplete` |
| Network source capture | 32 accepted, 0 failed | 59 accepted, 0 failed |
| Source coverage | `complete=true` | `complete=true` |
| Projection | `complete=true` | `complete=false` |
| DOM fallback | Not needed for detail values | Still required |
| L10-C gate | Not present in selected Normal tabs | `corporate.l10c_detail_gate=history` |

All 18 worksheet XML parts (eight Normal, ten Amendment) were byte-identical
between the two compared workbook exports. This protects against a *new*
worksheet regression in that pair, **not** against older unmapped source rows,
missing fields, workbook-wide metadata differences or PDF parity. Only **5/18**
template mappings were complete; `operation.finished=COMPLETE` refers to the
job's verified collection/export, not a blanket claim that every projection
slot is mapped. The submitted Amendment L3 domestic table captured **60 body
rows and three footers**, but its workbook remained empty/partial because
the exact DOM `TOTAL` footer was not bound to the approved `JUMLAH` merge;
#341 targets that presentation gap, not JSON capture.

| Time (seconds) | Earlier `e894f12` | Newer `c2bb6ed` |
| --- | ---: | ---: |
| Amendment `json_observe` | 68.65 | 81.10 |
| Normal `json_observe` | 37.96 | 47.26 |
| Amendment `return_detail` (DOM) | 117.61 | 147.17 |
| Normal `return_detail` (JSON) | 60.97 | 78.29 |
| Worker elapsed (includes dialogs/waits) | 295.02 | 284.67 |

The earlier run waited about **61.1 s** for the selection/overwrite dialogs,
whereas the newer waited about **3.4 s** for selection. Removing these
documented waits gives approximately **234.0 s vs 281.3 s** of active
elapsed time (+20.2% in the newer run), but stages overlap and cannot
be summed into an independent grand total. Portal/host latency is a
hypothesis, not an established cause; repeat on the same build, same
record/scope, with unchanged diagnostics before ranking optimization.

### Immediate sequencing and acceptance boundaries

1. **Native Normal:** verify the same selected scope with current exact-head
   `--detail-source json-only --spt-badan-only`, preserving packet provenance,
   source coverage, original values and workbook/PDF checks; do not extend its
   success to other forms or Amendment.
2. **Amendment L10-C ([#338](https://github.com/cepeter-job/spt-downloader/issues/338)):**
   once #340 has passing exact-head CI and review, use a fresh authorized live
   run to identify whether history refuses capture API, source controls, grid
   structure, bind-start, bind-end or lifetime. Never bypass those guards just
   to select JSON. `projection_incomplete` differs from missing capture.
3. **L3 Amendment DOM:** after #341 passes CI and merges, rerun the complete
   three-table source and verify all 60 ordered rows, exact three footer
   mappings, original source custody and remaining PARTIAL audit identities.
   This is distinct from issue #161's much larger 4,654-row L3-B test.
4. **Large DOM #161:** retain full-page/row/footer and end-to-end workbook
   acceptance, the existing bounded timeout, original UI owner, Stop, and
   fail-closed refusal; #321/#326 improvements alone did not prove 4,654-row
   completeness.
5. **Other open acceptance tracks:** #291 DOM presentation/DER, #307 frozen
   HOST_CPU forwarding, #302 XML UI catalog, #156 MPN; #168/#169, #288/#290
   remain independent deferred design backlogs. Do not conflate these with
   the documentation-only PR #208.

No claim of new native page-size options, packet reuse, skipped security
checks, whole-record DOM/JSON mixing, or runtime performance gain is made
by this update. Each implementation remains subject to independent tests,
review and CI at its exact head.

---

## Archived baseline and decision — 20 November 2026

Baseline: [main `818246f`](https://github.com/cepeter-job/spt-downloader/commit/818246f9c0d1714bdf02941f3edb28644bb662ad).
This section supersedes historical implementation/dependency status below,
not the recorded measurements. #208 remains a design-only PR.

### Native JSON: establish admission before optimizing

| Work | Status at baseline |
| --- | --- |
| #234 / #236 native paginator timing and owned probe | Merged; historical measurements below |
| #235 strict L7 lifecycle / initial loading | Merged; subsequent L7 fixes and #287 native consolidation do not prove live acceptance |
| #267 / #269 / #287 native representation and integration | Merged; preserve exact source, identity and workbook contracts |
| #295 / #299 / #305 / #312 / #319 Corporate correctness | Merged; L2 optional fields and numeric roundtrip, L3 period/year, L10-C clock and L4 fractional USD |
| #322 / #323 / #324 / #325 observer refusal diagnostics and L8 history budget | Merged; distinguish build, stage, L8 sub-guard and missing forms; no blanket admission |
| #327 strict Corporate CLI JSON-only mode | Merged; no DOM detail-value fallback on refusal |
| [#328](https://github.com/cepeter-job/spt-downloader/pull/328) data-conditional sheets | OPEN candidate; exact-head CI/review and live acceptance pending |
| Stage 0b part 2 request/response chronology | Pending proposal; not implemented by the refusal diagnostics |
| Larger native page size / packet reuse | Not approved; separate proof and review required |

The #328 description reports a #325 live refusal with
`corporate_missing_forms=L10-D,L11-A,L11-C,L4,L7`, whose corresponding
source roots were reported absent. It proposes tolerating genuinely
data-conditional missing tabs; it is not a merged change or proof of native
COMPLETE. Review must establish return-specific source absence (not just a
missing tab), reject present data with missing/unowned UI evidence, preserve
required forms and L1-B/L8 custody, and verify complete workbook projection.
Its reported 60-row L3-B API example is a **different workload** from issue
#161's 4,654-row case; never use it to certify the large case.

Use the exact checked-out commit, pinned environment and authorized private
scope per [AGENTS.md](../../../AGENTS.md). Baseline each case with
`--detail-source json-only --spt-badan-only` (#327), using a fresh private
output folder/profile and no detail limit for full acceptance. Inventory,
UI binding and PDF work can still occur. Incomplete native capture remains
PARTIAL (exit 2), with retained JSON and no DOM detail-value fallback.
Run `json-first` and `dom` separately when comparing fallback behavior.
Record the actual checkout SHA for source CLI even if diagnostic build
metadata says unknown; CLI is pre-acceptance evidence, not a CI/release
or frozen-EXE substitute.

### DOM: independent correctness and performance track (#161)

Merged since the historical comparison: #241/#242/#243 reset/rewind
attribution, #247/#248/#250/#252/#301 passive/opt-in diagnostics,
#311 owned pilot lookup, #246 missing-Previous lookup, #321 guarded
fused cursor turn, and #326 proved-absent First lookup plus finite
cursor readiness outcomes. #246 is **merged**, not an open dependency;
the documented runs had zero enabled-Previous clicks, so an actual
enabled-Previous A/B remains unproven.

Latest documented authorized source CLI evidence in
[#161](https://github.com/cepeter-job/spt-downloader/issues/161#issuecomment-7026296865):

| Metric | 19 Nov main a3a4ff0 (#246) | 20 Nov main 8ed1e9d (#321) |
| --- | ---: | ---: |
| Whole job | 465.98 s | 404.30 s |
| L3-B retained original rows | 2,500/4,654 | 2,000/4,654 |
| L3-B table wall | 205.62 s | 207.03 s |
| L3-B pre-read | 37.51 s | 56.86 s |
| Pilot label lookup | 17.07 s | 26.67 s |
| First lookup (zero clicks) | 17.32 s | 28.12 s |
| Complete tables | 36/37 | 36/37 |
| L3 worksheet dimensions | 11 x 10 | 11 x 10 |
| Result | PARTIAL | PARTIAL |

Four fused turns still needed separate 16–19 s snapshot RPCs. The
different-day source values differ; the shorter whole job does not
establish a causal speedup, and L3-B coverage was worse. The wall/renderer
residual does not identify an IPC, browser, network or scheduling cause.
The unchanged nominal 180 s table budget can be crossed by an in-flight
synchronous RPC but still prevents further row acceptance. Retained
checkpoint rows are not verified workbook rows.

[#326](https://github.com/cepeter-job/spt-downloader/pull/326) merged at
the baseline above. It skips a redundant First lookup only for a proven
negative on the selected 500-row owner, rechecks owner/label/First in the
existing initial snapshot, and emits allowlisted readiness outcomes on
existing calls. It does not establish that the extra snapshot RPC is
eliminated or that live throughput improved. Next authorized DOM CLI run:
check `table_first_lookup_source`, `table_cursor_turn_outcome` and
`table_cursor_snapshot_outcome`, compare same-source wall/RPC counts,
and require all 4,654 original ordered rows, footer and workbook parity.
Keep the 180 s budget, Stop, ownership and fail-closed rules; investigate
pending overlay/settle separately rather than raising limits.

### Open backlog and sequencing

- **#161** — active: large-table DOM coverage and genuine native/DOM
  acceptance; no COMPLETE claim. **#328** — active native admission
  candidate; do not duplicate or presume merge.
- **#291** — #289/#293 DOM mapping fixes are merged; L3-A live footer
  acceptance remains open, independent of L3-B source completeness.
- **#307** — HOST_CPU forwarding/diagnostics: #310 added tracing;
  frozen-worker flag acceptance remains open unless separately proved.
- **#302** — #303 XML catalog and #320 value-only-edit CI fixes merged;
  issue remains open, UI/build acceptance separate from capture.
- **#156** — MPN source acceptance remains open; #298 test stabilization
  does not establish live success. **#296** closed; #310 CI retry work
  is separate from scraper optimization.
- **#168/#169** — conditional filesystem/hash-reader extraction backlog;
  no helper consolidation or policy weakening authorized.
- **#288/#290** — deferred architecture and parallel capture; no
  implementation authorization and no new concurrency in #208.

Priority: (1) review #328 and verify strict JSON-only admission with
source/workbook/PDF parity; (2) independently verify merged #326 on
large DOM #161 and resolve #291/#307 where relevant; (3) collect
repeatable native timings and separately propose bounded chronology
instrumentation if needed; (4) consider native page size or packet reuse
only on measured evidence and separate approval. No architecture or
parallel capture changes are authorized by this design.

## Historical evidence — what the recorded runs actually establish

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
necessary source requests or as arrivals before navigation. The historical
pinned-build tab inventory was **15 observed tabs** (L1-B and L8 absent),
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
  OPEN; the independently reviewed
  [PR #235](https://github.com/cepeter-job/spt-downloader/pull/235) has since merged. See current baseline above.
  Do not claim that a performance PR repairs L7, a PDF or a DOM timeout.

### Historical 11 November stage status (native performance)

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

### Step 0b — remaining request/response chronology (proposed after admission baseline)

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

**Historical gate:** the #236 operator-run supplied measured step timings, but
was PARTIAL, with no native admission and differing inventory checksum.
Before approving further optimization, use the #327 strict JSON-only mode on the current reviewed baseline and obtain source-compatible repeat
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
4. **Historical live acceptance:** the #236 merged-tree artifact was verified and
   run but returned PARTIAL (L7 refusal plus DOM L3 timeout), so the
   end-to-end gate remains **open**. Require an operator-run id-ID
   `detail.source=native_verified`, complete L3-B 4,654-row source-
   to-workbook parity and independently verified financial-PDF custody/
   publication, or a separately supported fully complete DOM fallback.
   Track this under #161, not as proof furnished by design PR #208. The 20 November DOM evidence above still fails this gate; a smaller native return cannot stand in for the large workload.

PR #208 remains **design-only** and must be synchronized with current
`main` before review. Merged runtime changes are not delivered by this
design document. Any next runtime proposal must link exact-build evidence,
preserve the merged #235 correctness contract and coordinate with open
#328 and #161 without duplicating their implementation.
