# Submitted-list document custody repair

The newest operator run reached the submitted inventory but all selected detail
records stopped at the list-restoration ownership guard. The private log gives
the rejecting source line, without the individual guard state. Keep that limit
explicit: it identifies the failing boundary, not the precise live event.

The preceding PR115 treats every second main-frame `framenavigated` event as a
replacement. A same-document router `history.replaceState` can produce that
event at the same URL. Reproduce this candidate on isolated routed Edge before
changing production code; do not guess that the live request or login failed.

## Tests-first investigation

- [ ] Add real Edge cases for the unchanged route, same-URL replace/push, fragment
  and repeated notifications before/after the submitted-grid response.
- [ ] Keep same-URL reload and temporary route/query/taxpayer detours rejected,
  including detours which immediately return to the original URL.
- [ ] Publish tests and this plan only. Reconcile full runner evidence against
  the 5,842-case PR115 baseline before implementation. Expect only the eight
  same-document cases to fail at the current ownership guard.

The initial RED is accepted: [run 40261254624, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/40261254624),
tested merge `6950203ea53f60c23ade1492dd48463b4bde7d63`, exact tree
`3877a266f4f191f9f8b31272a12874deb58f0754`. All six archives reconcile 5,859 Windows cases with precisely
eight intended failures; all 5,842 baseline cases and 710 portable overlap pass.
Review adds nine deterministic protocol cases for identity availability,
acquisition reentrancy, Stop and handle release. Model actual Document identity
in the shared synthetic fixture, and make its existing extra-commit control
produce a replacement Document rather than an identical notification. The
original seventeen Edge cases remain unchanged. Before product edits, require
all 5,868 cases to reconcile with exactly sixteen intended failures.

The extended RED is accepted from all six archives of
[run 40263240018, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/40263240018),
tested merge `6520d1ceb3faf8f1ccd47cf98442db567b5493b3`, tree
`4b11b153316bfadf3added009e34d8a80e6e6be3`: 5,852 Windows passes and exactly
16 intended failures, all 5,842 baseline identities and 710 portable overlap
passing, with zero errors/skips. Full collection, phase outcomes, JUnit identities,
measurements, environment and archive SHA256/size checks reconcile. Only after
this gate is the retained-Document repair implemented; final GREEN is pending.

Fresh implementation review found two Important authorization gaps before merge:
the final identity probe can pump a fatal event after the earlier flag/route
read, and metadata/JSON preparation or cached-group reuse can occur after the
last wait without a View-boundary custody check. The first candidate is not
merge-ready. Add ten protocol cases with unchanged production code to reproduce
the nine expected failures and a valid same-document control, while all prior
5,868 cases remain passing. Require full 5,878-case RED reconciliation before
repairing either gap. Recheck the retained handle/latch/route after every probe;
check each record after metadata and inside View preparation, retaining the
actual inspected control rather than allowing locator rebinding on replacement.
The same post-probe rule also applies to a routed filter error delivered during
identity evaluation. Add that eleventh case with production still unchanged;
require 5,879 Windows cases, exactly ten intended failures and all previous
5,868 cases passing before repairing the state rereads and View boundary.

The 5,878-case run40266319370 is rejected as an acceptance gate: its actual
archives contain 5,808 Windows passes, 69 call failures and one teardown error.
Nine call failures reproduce the new authorization gaps; sixty affect prior
identities, including real-Edge unchanged-document controls. The teardown error
is retained separately and is not counted as a call failure. The initial repair
must also accommodate a navigation callback whose identity RPC yields before
goto returns. Add three deterministic suspended-greenlet cases for completion,
deadline and Stop with production unchanged, alongside the filter-error case.
Reconcile the full 5,882-case runner collection before the next product edit;
retain every prior failure/error and require all identities to pass in GREEN.
Extend those pending cases to reject late completion and stale acquisitions
after close/reset or a newer pending attempt, producing 5,886 total cases.
Pending identity expiry is a nonretryable ownership refusal, not a missing-list
response retry. Check deadline after a yielding completion, retain pending
through validation, and bind late completion/disposal to the original attempt.
Pending acquisition may be waited only inside the existing response deadline;
it never authorizes View or relaxes route/request/failure/cancellation gates.

## Bounded repair after reproduced RED

The target RED is independently accepted from all six archives of
[run40268648974, attempt1](https://github.com/cepeter-job/spt-downloader/actions/runs/40268648974),
tested83e236c8b69edba8ca833d016bf15e30803ac3c3/tree
df5b55da3e702117a12d07845b53b6a8af00d6ec:5,809 Windows passes,
77 call failures, zero errors/skips, and710 portable passes. Exactly17 target
regressions and60 known prior failures remain visible. All5,868 prior identities
are present; collection, phases, JUnit identities, measurements, environment,
hashes and sizes reconcile. This proves the target failures; the candidate is
still rejected until all5,886 identities pass after repair.

Review of cbe28b4 found two further Important gaps before acceptance: a stale
validation RPC can still invoke failure mutation on a newer attempt (also on a
repeated notification), and the acquisition deadline continues through the
independently bounded healthy idle wait after identity has settled. Add six
unchanged-product cases: four stale-validation failures, one slow-idle failure,
and one passing absent-response control. Require the full5,892 identities,
exactly five new failures and all preceding5,886 identities passing before
repairing these gaps. The previous candidate remains not merge-ready.
Actual run40270973008/attempt1, tested5a816182baf6e68425d5135dfc5c8e11b5f39295,
treecd7fe75da27787722eca57abdd6c971c561ec432, has5,885 passes/seven call failures,
zero errors/skips and710 portable passes. Five new failures reproduce the two
review findings. Two earlier JSON-preparation assertions access `sections`
unconditionally, although a pre-View partial record may validly omit that field;
both already prove refusal/no View/no DOM. Correct those assertions to require
no captured content with an absent field allowed, plus explicit PARTIAL/no PDF.
Keep all50 test identities and every other accepted test/helper byte unchanged.
The strict five-failure gate rejected this run; the separate observational
reader preserves all seven failures and claims only the five target proofs.
Full GREEN must remove both source and fixture failures before merge.

- [x] Retain a value-free reference to the actual committed Document. Permit
  additional notifications only with the identical active Document and the
  original authorized path/query. Missing or unreadable identity stays refused.
- [x] Preserve post-commit request custody, pending-request limits, fresh markers,
  one timeout-only retry, terminal errors, selected metadata/RecordId and Stop.
  Release handles on retry and close. Do not weaken another-document detection.
- [ ] Add fixed allowlisted diagnostic categories if the reproduced event cannot
  account for the live failure; never log URLs, taxpayer data or request material.
- [ ] Update AGENTS and architecture for the actual supported boundary. Run full
  Windows/portable suites, review exact artifacts/package and the latest merged
  other-session changes before integration. Keep L8 native admission separate.

All product execution stays on GitHub runners. Local operations are restricted
to source/AST/Git and artifact metadata inspection. No live retry is authorized
by this synthetic investigation, and no live recovery is claimed from CI alone.
