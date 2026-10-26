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

## Bounded repair after reproduced RED

- [ ] Retain a value-free reference to the actual committed Document. Permit
  additional notifications only with the identical active Document and the
  original authorized path/query. Missing or unreadable identity stays refused.
- [ ] Preserve post-commit request custody, pending-request limits, fresh markers,
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
