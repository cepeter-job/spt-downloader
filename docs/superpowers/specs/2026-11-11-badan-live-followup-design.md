# Corporate live follow-up: L7 lifecycle refusal and DOM first-page wait

Date: 2026-11-11

Status: Operator approved scope A (strict L7) plus B (DOM diagnostics only), related normal protected contract edits and hosted tests-first CI, through an explicit clarification response. Independent design review passed with no blockers; both coverage suggestions are included. Implementation is in progress on separate feature worktrees. No implementation GREEN or live acceptance is claimed. Design/implementation merges remain unauthorized.

## 1. Verified baseline and live outcome

- Operator build: `e5e0e988f1908d08c8a730d5a27e17665772b681`, official run `42813223671`, attempt 1.
- Repository main baseline: `4b615e4ef0485e9dcd61195879ede872c74c325b`. Its runtime source is identical to that operator build; the intervening changes are documentation/contracts only.
- The correlated current operator operation finished `PARTIAL`, with a complete inventory, incomplete record capture, one recorded capture error, and two published workbook declarations.
- The financial attachment is declared `COMPLETE` in both the record and published attachment inventory (one attachment). The original request was captured and the PDF phase completed. A read-only check found PDF signature/trailer and the existing size bound satisfied. This follow-up does not reopen PDF discovery or add attachment permissions.
- Requested detail source was `json-first`; actual source was DOM, with audit reason `unverified_corporate_l7_main_lifecycle`. Native observation completed; this is an adapter refusal, not an unfinished observer or a new `native_verified` result.
- A DOM table then raised `TimeoutError`, followed by `capture.partial`. Diagnostic coordinates are form ordinal 4; the source stack reaches `capture_panel` -> `capture_table` -> the first-page paginator branch -> `wait_idle`.
- Native observation took 646286.32 ms. Its largest measured segment was L3 at 466899.23 ms. These are nested timings, not additive job durations.

The earlier comparison checkpoint is no longer available. It must not be borrowed or reconstructed to fill current evidence. No private taxpayer identifiers, amounts, tax dates, document names, URLs, source payloads or authentication material belong in this record or tests.

## 2. Native refusal: source-proven boundary, not permission to clamp

`coretax_corporate_projection.py` currently raises the exact L7 lifecycle reason when its validated main `NetIncomeBeforeTax` operand is negative. The existing approved L7 contract deliberately covers a nonnegative-main branch only.

Before extending it, verify current original response bytes against their manifest, inspect operand types/predicate results without printing values, and trace the hash-matched corporate/MAIN frontend callbacks and renderer. Establish the actual negative-main branch, original row/footer operands, predecessor/current-year bindings and owned stable lifecycle. Do not remove the guard, substitute `max(main, 0)`, synthesize zeros, drop source leaves, reuse a prior attempt or claim a different record was supported.

A new supported lifecycle branch requires a bounded design and operator approval, clearly synthetic tests-first hosted RED/GREEN, typed original provenance and held-replay refusal cases. If the consumer/lifetime proof is missing, retain whole-record fallback and name the missing evidence. L11-A/L11-C and unrelated forms are not silently added to this scope.

## 3. DOM timeout: exact observed wait, unresolved cause

The runtime stack reaches `coretax_browser.py:435` after the inspected first-page paginator click, then `wait_idle` at line 361. The latter waits for the first visible `.p-datatable-loading-overlay` or `.p-blockui` to become hidden under its existing timeout. The table phase lasted 59424.87 ms in this failure.

This proves which wait expired; it does not prove whether the overlay belonged to the target table, another table or a global blocking layer, nor whether a page-size/first-page request race or a slow/failed response caused it.

Investigate retained request/response metadata and the pinned renderer before changing behavior. A candidate must preserve actual node/document/table ownership, global blocking UI, first-page completeness, Stop, existing transaction/time/page budgets and partial/publication semantics. Do not just increase timeouts, ignore overlays, invent a first-page response or add retries.

If current evidence cannot separate causes, specify a narrowly scoped value-free diagnostic/probe returning only reviewed owner categories, counts, booleans and timings. It must not read business fields/checked state, reveal private source data or authorize capture after a failed wait.

## 4. Completed investigation and source trace

Two independent read-only investigations verified the checkpoint-selected seal, both manifest copies and all 572 unique original response paths against declared byte lengths and SHA-256. All three inspected public bundles match committed pins. No product adapter, JavaScript or tests were executed. Scratch source hashes establish inspected public code, not a loaded same-attempt provider.

### 4.1 L7: bounded raw identity, not a blanket negative allowance

The refusal occurs at the existing negative-main guard. Independent data-only checks satisfy every later L7 predicate examined, including all six safe ordered sums and all six captured-total reconciliations. This does not execute the adapter, predict later forms, or certify native eligibility.

Hash-matched frontend source establishes the conditional profile below:

- Submitted Induk's `CalculateNetIncomeBeforeTax` does not derive another main value. Its separate sole-income-one callback can clear a nonpositive main and disable L7, so an arbitrary negative cannot be admitted.
- The proposed profile has explicit-null sole selector, numeric-zero under selector and numeric-one carry selector. The callback capable of clearing main is excluded by that exact shape, not by a silent default.
- Initial outer carry absence is not carry false. The Induk callback supplies current main and enables the direct L7 child.
- L7 initializes from current source, not predecessor fallback. Its first current-year captured profit is already nonzero and numerically equal to stable main. Its changed-main/falsy-or-previous-profit handler does not justify a clamp or rewriting later duplicate rows.
- The row number renderer preserves negative profit. The six ordered compensation reductions do not sum the profit column.

Public source anchors (zero-based Python Unicode character offsets in the hash-matched cached text, not private response offsets): CORPORATE parent/Induk callback 2695011; raw main mapping 2791437; sole-income callback 2805740; submitted calculation 2833156; sole-income disable 2841196; L7 changes 2434300; L7 renderer 2432000. Framework input/view lifecycle was inspected in the matching VENDOR, so the new native profile must acquire its own loaded vendor proof.

### 4.2 DOM: the decisive evidence gap

Checkpoint sections map diagnostic form ordinal 4 to L3. Its third table strongly maps to domestic B in the pinned three-table order, but no failed-table node/overlay identity was retained. The failure precedes the first table snapshot and cursor creation; it is not a Next/cursor read failure or an elapsed-table-budget refusal.

The JSON transaction seals before DOM fallback and stops admitting later requests. Its successful ten-row L3 pages and zero final pending count cannot explain the later DOM size/First actions.

Pinned paginator source retains a page derived from the new size; a size change does not unconditionally reset to zero. Legacy `ui-grid` loading combines body-request and reference-readiness state. These are possible paths, not evidence that a size/First overlap or unrelated overlay caused this run. No loading behavior repair is approved by this proposal.

## 5. Recommended bounded implementation scope

Implement the two workstreams independently, with no claim that either clears all remaining native/capture/mapping gates.

### A. New guarded L7 raw-negative profile

Keep the legacy two-pin `corporate-l7-v1` nonnegative behavior and old evidence readable. Do not add negative permission to a legacy proof or silently change its exact build-map contract. Offer the stronger negative capability additively and consume it only for the negative branch; a missing/unavailable child-history capability must not add a new requirement to old nonnegative admission. Known Document/identity contradictions remain fatal under existing guards. A structurally valid unsupported/expired observation is absence of negative permission, not fabricated malformed evidence.

The new profile must use an explicitly distinct versioned semantic proof, with all three positively valid loaded CORPORATE/MAIN/VENDOR provider fingerprints and the existing exact route, preceding Induk, locale, table/header/footer and original-packet ownership gates. Observation stays value-free and may supply stronger structural proof without inspecting an amount or input state.

The pure projection may preserve raw negative values only for this closed current-only source profile:

1. Ordinary Rupiah `ICT_RCIT`, submitted Normal, the selected literal non-history route; explicit current objects and literal-null PreviousFormData and LastSubmittedFormData. No predecessor/amendment/history/USD extension.
2. Current main has numeric-zero IsIncomeUnder, literal-null IsIncomeSolely, numeric-one IsCarriedForward and numeric TaxYear equal to outer PeriodYear. Outer IsCarriedForward is absent, not null, zero or defaulted.
3. Main is an exact safe negative integer. The first matching current-year row exists and its original nonzero profit already equals main. A zero/differing first profit remains unsupported under this branch. Preserve later duplicates, literal years and all source rows/leaves.
4. Retain every existing exact operand, formatting, ordered-intermediate and captured-total reconciliation guard. Never clamp, synthesize zero, recalculate a reported footer or use DOM business values.
5. Use a distinct raw-negative identity provenance rule. Keep original current-main operands under CurrentFormData and payload-level status/predecessor predicates under their actual Payload owner. An absent field is a presence fact, not a fabricated null source leaf. Do not blanket-reassign payload provenance to CurrentFormData.

**Conservative new admission prerequisite:** require an optional manifest-owned L7 lifetime fact for the new negative profile. Arm it only in the owned submitted-list interval before the inspected View, with no old L7 host (including hidden instances). Bind the original Document, single selected transition, attempt, record, source/detail URLs and unique corporate owner. Retain the actual newly observed L7 form/grid/table identity and refuse removal/replacement/duplication, even after reinsertion; sample final history inside the existing late-response seal fence. Recheck its enabled tab/panel/structure at both observation boundaries. No Angular debug state, checked state or business-value reads.

Use the existing capture-owned lifetime infrastructure/pattern where sound, but do not relabel its coarse Document/outer-owner fact as continuous L7 history. The new fact is absent on legacy captures. Missing/unavailable proof preserves negative fallback; present malformed, conflicting or cross-attempt proof follows the existing fatal custody rules. Bind/revalidate it during held replay; response descriptors or caller assertions must not override it. The history mechanism must have a fixed bounded relevant-structure budget and cleanup; unrelated long L3 row churn must not be misrepresented as L7 history or silently consume an unbounded observation budget. If a bounded proof cannot be established, keep this native branch disabled rather than weakening it.

This stricter continuous-child proof is the recommended admission choice, not something the completed run already provides. No replay clock, quiet timer or Scratch vendor bytes may fill it. Implementation approval covers this proof and the corresponding normal protected contract update; it does not authorize bypassing an edit refusal.

### B. DOM initial-loading diagnostics only

Instrument the existing table preparation/First reset without changing its actual clicks, wait selector, loading timeout, settling behavior, page limits or outcome. Preserve real global BlockUI and other-table loading; no behavioral repair is justified until a live observation distinguishes the cause.

- Retain the existing table/owner and a diagnostic-only Document/attempt identity; never search for a replacement owner. Report only fixed identity/connection/uniqueness/paginator-readiness categories.
- At preparation entry, size-action boundaries and First-action boundaries, record fixed action stages, bounded durations and selection-change/dispatched/unavailable categories. Keep the original shared table deadline; diagnostics must not create a fresh action budget.
- Observe actual original request objects passively for that preparation interval, independently of the sealed native ledger. No fetch/replay, authentication-header read, cache/storage access or raw body persistence. Only inspect the reviewed selected-grid/reference request shape transiently and within a finite size bound; classify all other traffic as other/unbound. Do not add a new request-identity enforcement/fatal path in the name of diagnostics; existing safety checks remain authoritative.
- Keep a hard-bounded temporary request-object set with observed/header/finished/failed/pending counters by action interval and reviewed endpoint class. Object identity, not temporal coincidence, establishes lifecycle overlap. Never emit raw request fields, offsets, routes, IDs, headers or bodies, and never treat temporal request classification as DOM ownership proof.
- Observe loading structurally with the same held owner: target datatable / other datatable / BlockUI / mixed / none / unavailable, including which category the current dynamic first match belongs to. A request-finished-but-still-loading observation does not prove reference or renderer causality.
- Register finite diagnostic events/enums and privacy tests. When diagnostics are OFF, do not install this extra request monitor or issue its extra structural RPCs. Diagnostic timeout/overflow is unavailable, never none or ready. Extra structural reads are at most 1000 ms and the original remaining table budget; any after-failure probe is independently at most 1000 ms, diagnostic-only, with no continuation-as-success. Never mask Stop/safety/original exceptions, and preserve existing later-panel recovery after PARTIAL. Remove listeners and release handles on every exit.

A characterization test of today's PARTIAL behavior is not a false RED-for-fix. Tests-first RED must demonstrate the new missing diagnostic itself; future loading behavior needs its own proved root cause and regression.

### Explicit exclusions

No L11-A/L11-C semantic expansion, PDF/OtherDocuments change, pin refresh, transport permission, broader POST/GET, retries, larger timeout/page/table budget, performance rewrite, synthetic tax data in live output, or automatic merge. Do not reopen the completed PDF fix.

## 6. Verification and acceptance

Local activity remains source/AST and authorized read-only data/hash analysis. No product imports or copied product-function execution. Private live payloads never enter Git/CI.

For L7, use tight hosted synthetic RED/GREEN at pure projection, real observer/adapter, manifest/held replay and saved/reopened workbook seams. Cover the exact narrow positive, duplicate/first-match preservation, every selector/encoding/absence/type variation, unsafe operands/intermediate sums, every reported-total mismatch, wrong/missing pins and lifetime facts, transient detach/reinsert/duplicate, changed Document/route, cross-attempt descriptor override and unchanged legacy nonnegative cases. Explicitly verify that a nonnegative `corporate-l7-v1` capture retains legacy admission when optional new history expires or exhausts its budget; malformed/conflicting supplied proof is a separate custody test, not an unavailable capability. A synthetic long unrelated L3 mutation stream must exercise bounded history and no false continuity claim.

For DOM diagnostics, model the pinned retained-page size change and one First click with explicitly controlled request/overlay lifecycle. Cover sequential versus overlapping/late dispatch, target/foreign/global masks, response-finished-but-still-loading, unchanged size, detached/ambiguous owner, unavailable/overflow, Stop/deadlines, cleanup and privacy sentinels. With diagnostics OFF, assert no extra listeners, retained handles or structural RPCs. Assert exactly unchanged action count, wait/refusal/PARTIAL behavior and sealed native evidence.

Require independent review and every exact-head selected check, including CodeQL, all Windows shards, coverage, packaging, uploaded-artifact readback and bootstrap for implementation. Docs-only routing is not product verification.

Application-owned exact-build live acceptance remains separate: new manifest-owned L7 proof, actual native eligibility, whole-record capture, mapping, declared COMPLETE PDF custody and final publication are independent. No source analysis, synthetic green or available artifact establishes `native_verified` or COMPLETE.

## 7. Approval checkpoint

Recorded decision: the operator selected **L7 ketat + diagnostik L3 + kontrak + CI** for the reviewed proposal at `e8bac59db9ceb90b621a39c231f104d10723ced1`. This approves A (strict L7 profile with its new owned proof), B (DOM diagnostics only), synthetic hosted tests-first CI and related normal protected contract edits. It does not authorize merge, a speculative loading repair, local product execution, private-data upload or a claim of native/live acceptance. Implementation must preserve these scope boundaries and the independent verification gates above.
