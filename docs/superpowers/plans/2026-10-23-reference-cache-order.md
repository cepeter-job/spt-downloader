# Reference cache ordering repair

The pinned main bundle (`696ac66d…`) sorts catalog Details before the active
version consumer reads them. Existing native PPh21, Unifikasi and corporate
COUNTRY_CODE projectors incorrectly group the raw response order first. Duplicate
open-ended codes can therefore select a different label and original source row.

Reproduce only the source-proved ordinary catalog ordering: ascending literal
CodeDescription under JavaScript UTF-16 relational ordering, stable on ties. The
first raw catalog row globally switches the key to parsed ParameterData.DisplayIndex
only when its string contains the exact `"DisplayIndex":` spelling. Support
homogeneous safe integer keys or homogeneous literal string keys; unproved key
types, malformed triggered metadata and coercive mixtures stay unsupported.
Preserve original raw rows, duplicates and source indices. Group the sorted
index/row pairs, then apply the existing attempt-clock version selector. PERIOD
and model dropdown uniqueness gates remain strict and separate.

The source chain is cache.add at main UTF-16 offset3008210, Details assignment
3008441, applyReferenceDataOrderBy3006443, getSingleReferenceData3018067 and
getActiveReferenceDataValue3017141. Vendor (`1de6335b…`) Lodash orderBy460288,
an427348, Np427715 and Bp432292 establish relational keys and stable original
index ties. COUNTRY_CODE has no direct raw-response bypass. No browser cache
inspection or extra catalog requests are authorized by this repair.

1. Publish source-bound regressions and correct the earlier raw-order expected
   dated result. Read intended failing assertions from GitHub runners before
   implementing the repair. Strengthen existing native/saved PPh21 and Unifikasi
   regressions by reversing the raw version order.
2. Add one shared bounded ordering helper and use it in the three ordinary label
   projectors, retaining ParameterData evidence and original selected paths.
3. Run the full unchanged Windows/portable/package workflows, inspect exact
   artifacts, obtain fresh source review, review preceding other-session merge
   and latest main, then merge the repair with an exact head lease.

This is synthetic/source validation. The completed matched PPh21 benchmark keeps
its original tested tree and private evidence; it is not silently rebound to a
later build. Corporate native/capture/PDF/mapping gates remain independent.

## Catalog RED readback

Final tests-first head `6f8231babd4c9a9ac94d4e25abed0069e7433141`, tested merge
`b05ce2087bb863053112e246285962e709021e98`, tree
`453d5d403e74c11e7f7ec475ea29c2d544410459`, run
[39945716183](https://github.com/cepeter-job/spt-downloader/actions/runs/39945716183),
attempt1, produced4,696 disjoint Windows cases:4,588 passed and108 intended
failures, zero errors/skips. All101 new catalog cases failed, along with seven
strengthened/corrected existing dated cases; all4,588 untouched baseline cases
passed. Two parameter node IDs change only because the corrected expected label
is included in their name; reconciliation maps those two explicit names.
Portable710 overlaps Windows and passed.

The exact JUnit ZIP digests matched GitHub artifact metadata:

| Artifact | SHA256 |
| --- | --- |
| Windows0 `12498772579` | `a9d7b34dc98f85a91322dd65406ea690d31adf8f6dee0f4a04e937bf9bf64c1b` |
| Windows1 `12499350043` | `bad6413a4eb9a62768feab481da8136d2e1ccab2a85cea90073cbf2df456b06a` |
| Portable `12498620559` | `bb78350924ce703e073419fb5cb9ce2bf99464cee2dcf5dca58e8ce78e040b06` |

The first completed Windows shard's54 intended failures were read before the
shared ordering helper was written; the remaining54 were read before publication.
Earlier superseded tests runs are not full-suite verification. Static review
corrected the initial test helper's catalog ownership before this final run.
The repair uses original ordinal/row pairs, retains raw candidate evidence order,
records ParameterData and the selected ordering rule, then applies the existing
clock selector. Full GREEN/package readback and final source review remain open.

## Review follow-up and latest main

Fresh implementation review found two additional boundaries. An unsupported
ordering key must not mask an explicitly contradictory catalog/detail language,
including when form observation is unavailable. Preflight the exact admitted
reference payload before projection/fallback, and preserve the same rule in
pure projectors. Mixed-defect tests use valid JSON with unsupported keys so a
separate parsing/privacy failure cannot conceal the locale check.

The comparator is supplied by the separately reviewed vendor bundle. Preserve
legacy unique-Code compatibility, but require positive optional Induk
`reference_order_build` evidence for every ordinary duplicate-Code catalog in
PPh21/Unifikasi. Pure projectors declare `requires_vendor`; they do not claim
that an asset was loaded. Observers hash the exact already-loaded vendor through
the existing bounded public-source reader; omit unavailable/wrong proof and
never force a missing asset to load. Validate any present proof and preserve it
with selected-value provenance. Corporate L11-C already requires this vendor.
PERIOD/model ambiguity stays unsupported even with positive proof.

Tests-first follow-up adds80 cases:54 mixed-defect pure/packet cases with/without
form observation, six pure dependency declarations, fourteen native gate and
dropdown controls, and six real Edge observer digest/changed/missing controls.
Existing dated positive fixtures now supply the required dependency proof, with
an actually loaded synthetic vendor for the full native PPh21 saved export.
The follow-up production guards are not implemented in this tests-first commit.

Preceding other-session [PR101](https://github.com/cepeter-job/spt-downloader/pull/101)
merged as `f45ba79f26eaa923c3afc017eab0458d8be66328`. Reviewed all seven changed
files, including finite Authorization budget, exact one-request replay,
first-rejection diagnostics, allowlisted categories and23 synthetic cases.
It changes no catalog/projection code or source pins. The local integration
preserves its source/tests/docs and their independent live/PDF claims; this
JSON work does not reuse the other session's live authorization. The latest-main
baseline now has4,618 Windows cases; combined follow-up expects4,821.

## Submitted corporate View integration

The same priority repair includes a separate two-line route compatibility fix:
the pinned submitted-list View navigates to the exact selected corporate route
with `?view=true`, while L7/L11-C semantic lifecycle checks accepted only the
query-free spelling. Both already require proof/frame equality. Preserve that
equality and permit only those two exact route spellings; retain shared identity
checks and the semantic query/history rejection.

The identical six unit regressions were first run in the L1-D tests-first slice,
head `3795ad1296ad4efddb4bfb438bb99d5856c23d5b`, tested merge
`2829c946fa7169cef3c726882227b8122a78d6f3`, tree
`eeba64f3a1fbf5ebd396dfb86e9df31cbfa2ab0f`, run
[39943608612](https://github.com/cepeter-job/spt-downloader/actions/runs/39943608612).
Digest-matched JUnit artifacts `12497533505`/`12496999056` showed both current-query
cases failing at their semantic submitted-lifecycle checks, while the two legacy
and two proof/frame mismatch controls passed. All4,595 baseline cases passed;
the other43 failures belong to separate lifetime/metadata/layout extensions.
The route tests here are AST-identical copies of those six regressions, plus four
native Edge-to-saved-workbook cases for Normal/amendment and popup/same-page
navigation. Fresh source review found no blocker and requested matching-proof
negative controls; twelve cases cover duplicate/additional/encoded queries,
case changes and history paths for both forms. This work does not enable
undispatched L1-D semantic projection.
