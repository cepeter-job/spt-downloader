# L10-D original custody and continuous history: joint-final integration pending

Date: 2026-11-17. Baseline: `f5e40a2a4e02f0b03dcec6126a6416b5e10b3bbe`.
Independent implementation follow-up to docs-only PR #279. **Not native L10-D
acceptance, a worksheet projection, or permission to merge either PR.**

## Approved decision

The operator explicitly chose **keep L10-B/L10-D absent from new workbooks;
continue proving non-display custody**. The display exclusion is not reopened.
No template/resource, historical proof/index namespace, old workbook or old
checkpoint is rewritten. The protected AGENTS.md contract is a separate parent
review deliverable; this report does not complete or substitute for that edit.

## Implemented original-only subset

`coretax_corporate_l10d` owns a separately versioned, finite
`corporate-l10d-originals-v1` candidate. It is deliberately **not** a native
capability. The observer optionally offers it only for an owned enabled L10-D
form after Induk, with the existing current Document/component lifetime and
positive loaded-script equality to all three reviewed pins. The provider check
and hash read happen in the same bounded asset evaluation; fetch/preload-only
entries are not providers. Missing pins cannot pass as `None == None`.
No new API/catalog route, source pin, business-value/checked-state read, Angular
state read or private browser cache access is introduced.

The adapter separately validates a strict current-only submitted ordinary-rupiah
profile: ICT_RCIT/ICT_RCITR, Normal/NORMAL, literal selected `?view=true` route,
preceding Induk, explicitly null PreviousFormData and LastSubmittedFormData,
and original numeric-literal `1` (not boolean/string/1.0/default) on both outer
and current MainFormData IsObligationTransferPricing owners. Existing packet,
privacy, selected identity, snapshot, clock, source coverage and final-drain
checks run first. Explicit malformed/misplaced original-custody bindings are
rejected at the binding boundary, including disabled/path-plus/projection or
request-bearing variants. No new capture manifest fact is invented.

The supported root is an original object whose keys are exactly:

- MasterDocumentary1..5 and LocalDocumentary1..5, each a present JSON boolean;
- MasterDocumentAvailableDate and LocalDocumentAvailableDate, each explicitly
  present as null or a supported literal string.

The original-string subset is ASCII YYYY-MM-DD, optionally followed by
T00:00:00, optional .000, and optional Z or +07:00, with a valid source date in
1970..2100. These are **original string syntax checks only**, not a date
renderer, calendar value equivalence, JS Date conversion, timezone assertion or
permission borrowed from L3/L11-A. Other/missing/malformed/date profiles remain
unsupported; their complete unchanged original response still stays in private
capture evidence. No missing leaf is manufactured as null or false.

The candidate retains all twelve child leaves plus **outer Payload.TIN and
Payload.PeriodYear**, with exact JSON type, presence, original value/numeric
lexeme, response sequence, original container and path. Root object type and
original key order are retained separately, so [{}], {}, and {Body: []} cannot
masquerade as one empty leaf. It additionally retains both original selection
flags and every predecessor/status/model operand used by this finite predicate,
bound to the actual response hash/sequence/attempt.

The local date's dependency explicitly retains **both** date operands under
`pinned-local-date-guarded-by-master-originals-only`. The pinned source really
uses MasterDocumentAvailableDate to guard LocalDocumentAvailableDate. A null
master does not erase a populated original local date. No checkbox caption,
rendered date, source repair, placeholder field, fabricated zero or replacement
root is emitted. Full accepted original response bytes remain authoritative.

## Historical original-only blocker (head 42c5bb7)

The original producer could prove only current enabled-owner boundaries and the
existing coarse retained Document/component lifetime. It could not independently
prove final Induk selection, uninterrupted original L10-D child lifetime, and
absence of a later selection/source-changing callback through final drain.
Equal saved outer/current flags and a currently enabled tab do not prove those
facts. Rechecking a snapshot twice or waiting a quiet timer would not close it.

Consequently every successfully collected candidate explicitly carries:

- `native_admission: false`;
- `blocker: unverified_corporate_l10d_final_selection_custody`.

The adapter retains the typed candidate in private
`detail_source.json.non_display_originals`, returns that exact unsupported
reason, and selects whole-record DOM fallback. It does not mark coverage
complete, manufacture `fields`, replace the original dump table with an empty
presentation, or add a display-exclusion exception to the dump gate.
`has_audit_dump_tables` and the hybrid source-selection gate remain unchanged.
Without the optional offer, old evidence-leaf adapter/replay behavior remains
readable and the same existing dump gate still refuses native selection.

**Native supported subset: none yet.** Original-only custody is useful evidence,
not final semantic admission. A later reviewed version must add an actual
capture-owned continuous child/selection capability, bound to loaded pins,
attempt, record and literal routes, rechecked within the final late-response
fence and independently validated by both live and held readers. Unknown,
missing, mixed, malformed and forged facts cannot be promoted from observer
hints. Identity/privacy/known snapshot contradictions stay fatal. The protected
combined contract review and application-owned build-matched operator acceptance
remain outstanding independently of this PR's synthetic CI result.

## Verification boundary

Tests are written before their implementation slices; local RED was verified
by source absence, not by executing product code. Local checks are AST/source/
diff only. All product imports, pytest, protocol/browser/Tk tests, self-tests,
builds and EXEs run only on GitHub runners.

The hosted regressions cover ten explicit true/false controls; complete typed
source-root/header/date custody; guarded-but-not-displayed local dates; missing,
null, wrong-type and extra leaves; exact positive pins and missing-pin/missing-
asset refusal; strict current/source profiles; actual observer dispatch into
DetailJsonCapture, adapter and whole-record DOM fallback; held-byte replay
without a browser; Stop; identity/privacy/changed-snapshot fatality; unchanged
dump refusal; saved/reopened workbook exclusion of both B and D; and checkpoint
preservation. Protocol doubles are synthetic ownership tests, **not a live
browser or operator acceptance claim**. Existing presentation, dump-gate,
manifest, export and publication regressions remain in the full CI inventory.

## Follow-through: independently reviewed callback invariant

The following are public-source offsets in the independently hashed, unchanged
corporate provider `525.32c49782948fc5ef.js`, SHA-256
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
MAIN (`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`)
and VENDOR (`6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`)
cached bytes were independently hashed against the same configured loader too.
Cached source inspection is not positive loaded-provider evidence; the real
observer still requires the existing provider/hash conjunction.

| Source chain | Source offset / bounded result |
| --- | --- |
| Parent `mapFormData` | `2649929`: reads original CurrentFormData.MainFormData; the sole `l10dFormData` assignment at `2651248` reads original L10dFormData. Callback accumulators are distinct inputs. |
| Induk `Ec` | `2778983..2856188`: the flag occurs only in its constructor and the explicit `setFormData` copy at `2795110`. None of its other 69 `mainForm.patchValue` sites writes this selector; there is no `mainForm.setValue/reset` call. Disabled submitted controls exclude the ordinary user writer. |
| Induk lifecycle/output | `2789364`: only changed original `formData` re-enters setFormData. `2812391` subscribes to mainForm.valueChanges; `2844201` returns getRawValue with unrelated income/SignBy overrides. Delayed arithmetic/reference callbacks can still fire, but do not write the selector. This is an invariant, not a quiet-timer argument. |
| Parent MainForm callback | `2695011`: patches the accumulator, then calls setShowAttachment10d with that same output selector. `2705579` has only the numeric1 show / numeric0 hide-and-clear branches. |
| D renderer/output | `2623703`: conditional panel `Km` receives original `l10dFormData` and emits onCallbackForm(L10DForm,...). `78114` emits D getFormData on its own valueChanges. The parent has no D switch arm and no output-to-input/selection feedback assignment. D output changes neither the saved input nor Induk selector. |

Thus the strict original numeric1/numeric1, submitted current-only profile can
use the named source rule `submitted-immutable-induk-selection-v1` **only when**
the original root, Induk child and D child are independently continuous and the
exact enabled D tab/panel remains bound through the final joint snapshot. This
does not assert that callbacks cease, nor infer a final selection from equal
saved flags. A changed original primary remains fatal at the existing typed
snapshot gate. The original twelve D leaves, both date operands, outer headers,
raw response and generic dump remain unchanged.

## Implemented D-specific history and reader boundary

`coretax_corporate_l10d.L10DHistory` now owns a separate before-View structural
history on the retained Document. It refuses an initially occupied root/main/D,
adopts each unique original node once, and retains their ancestry, exact D
tab/panel/view/li identities and controlled-panel binding. Replacement,
detach/reinsert, duplicate/foreign children, panel reparenting and a transient
disable/control-binding change are sticky; restoring the final DOM is not a
repair. Relevant structural candidates spend the finite 4096 budget; unrelated
table-row churn is not charged. No values/checked-state, Angular/cache reads,
active requests, timers or DOM writes are added by the history.

The real DetailJsonCapture arms and cleans this owner; the real observer binds
its actual form/tab/panel at both boundaries. Newly returned history/element
handles are retained before the post-RPC Stop check, and cleanup preserves Stop
and known safety failures. `accept_sample` accepts only the exact three boolean
keys, latches unavailability and raises on known change even after optional
unavailability. A boundary candidate is expressly not a final capability.

The separate optional `corporate_l10d_lifetime` manifest schema is validated by
the D owner and both `iter_bodies` and `checkpoint_bodies`. It requires the exact
parent lifetime/attempt/record/literal routes, the source rule, fresh/stable
root/main/child, enabled boundaries and a true final_joint_snapshot. Descriptors
cannot override it, even with an equal value. The packet reader validates it
before structural fallback; its fingerprint includes absence, so mixed evidence
is fatal. Replay never probes a browser or invents missing proof. Schema tests
explicitly inject and rehash a synthetic manifest: they prove reader semantics,
**not independent final production or native acceptance**.

## Exact shared integration still required (not implemented by this D owner)

The B safety owner owns the reviewed shared final-snapshot repair. This branch
does not copy its work or append a D end RPC after a stale L7/B sample. The
existing `drain` deliberately emits **no D capability**. Parent integration must:

1. Validate component/Document first; include `_l10d_history.handle` whenever
   `_l10d_history.requested` in the same synchronous final browser evaluation as
   every other offered/requested child. Call its `sample()` there, after all
   preceding RPCs, and return the exact `{available,changed,complete}` state.
   Do not follow that snapshot with any browser RPC.
2. Locally run `_l10d_history.accept_sample(state)`. Missing/malformed/unavailable
   state grants no capability; changed state stays fatal. Preserve the original
   pending latch, sequence fence, sticky source/route flags and Stop afterward.
3. Produce the exact D manifest fact from that accepted joint state and already
   validated parent; call `validate_lifetime` before persistence. Only this
   actual producer may set final_joint_snapshot, never an observer hint.
4. Add the strict source-specific admission/report and raw-dump exemption tied
   to independently reconstructed original report/primary sequence, retaining
   the dump and no-sheet rule. No generic display-filter exemption. Add a real
   populated capture -> adapter -> both held readers -> saved/reopened no-B/no-D
   native positive, plus cross-child changes during the final RPC, late
   responses (including excluded MIME), Stop and descriptor negatives.

Until those exact combined tests and producer exist, `native_admission: false`
and `unverified_corporate_l10d_final_selection_custody` remain correct. Protected
contract approval and application-owned live acceptance remain independent.
