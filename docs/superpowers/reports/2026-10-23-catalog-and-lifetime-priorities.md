# Catalog, current View and corporate lifetime priorities

[PR104](https://github.com/cepeter-job/spt-downloader/pull/104) merged as
`64a4ce3f794f2fa439397630502bde3ed1458c93`, tree
`ce7a05baec050c509f1125fd7f95917641a00fd5`.
[PR102](https://github.com/cepeter-job/spt-downloader/pull/102) then merged as
`e25aa5e88132c4f8aa03cd6e764dbd507160d816`, tree
`9d84692db85cf2b6fc69ef2b20ec1064fb987fcc`. These complete the reviewed catalog,
current-View, component-lifetime and saved L1-D layout prerequisites. Native
L1-D observation/dispatch continues separately in [PR105](https://github.com/cepeter-job/spt-downloader/pull/105).
The pure L1-D helper does not enable that branch by itself.

## Behavior and boundaries

Ordinary catalogs now apply the pinned consumer's ordering to the complete raw
Details list before grouping Code and selecting the active version. Literal
CodeDescription uses stable UTF-16 ordering. The first raw row alone can select
DisplayIndex ordering; only homogeneous safe integer or string keys qualify.
Unsupported/coercive keys remain unsupported. Original rows, source indices,
ParameterData, duplicates and response bytes remain unchanged.

An explicit catalog/detail language contradiction is fatal before unsupported
shape/order fallback, including when forms are unavailable. PPh21 and Unifikasi
ordinary duplicate-Code catalogs require positive proof of the exact loaded
vendor. Unique-Code compatibility remains, but any present proof must validate.
The observer requires an exact script provider, not merely a matching fetch or
preload resource. It hashes an already-loaded asset through the existing bounded
reader without forcing a missing asset to load. PERIOD/model ambiguity remains
unsupported. L7/L11-C accept the inspected literal `?view=true` route as well as
the legacy query-free route, with exact proof/frame equality and other query and
history rejection intact.

Optional manifest-owned `corporate-submitted-spa-v1` proof starts before the
inspected View click in an owned Service-Worker-blocked context. It retains the
Document, requires the exact submitted-list owner, one selected SPA transition
and the unique final corporate owner, then seals inside the late-response drain
fence. Known route/document/history contradictions are fatal; unavailable proof
does not establish eligibility. Live iteration and replay validate attempt,
record and source/detail bindings and reject descriptor overrides. Matrix URL
parameters are explicitly rejected. Handle ownership is established inside the
acquisition probe so cancellation can dispose it even at the post-probe boundary.
The exact financial replacement POST supplies a value-free veto only: no new
request admission, body/header access or replay permission was added.

The pure L1-D projector reconciles the source-proven 31 codes/35 slots, four
effective masks, explicit migration state and captured totals under safe ordered
integer reductions. The saved renderer inserts the missing account slot only
after exact ownership, headers, 35-slot sequence and original reference geometry
validate. It preserves account 5322, later headings, totals, merges and styles;
the approved binary resource is unchanged. Corporate Induk mapping, financial
PDFs and live acceptance retain independent gates.

## Tests-first and source review

Catalog ordering RED run39945716183 had108 intended failures. Follow-up
run39949738494 tested merge `538351e14e3643ab84f2402da283146ca12ebfb6`:
4,821 Windows cases, 4,767 passes and54 intended failures, zero errors/skips.
Script-provider run39952648748 tested merge
`69cec5698f0328789994b7f06ea2006d88cd4512`: 4,825 Windows cases, 4,821 passes
and four intended failures, zero errors/skips. Both corresponding JUnit archives
were read before each production increment was published.

L1-D pure-helper RED run39939119266 had28 missing-helper failures. Prerequisite
extension run39943608612 had45 failures across lifetime/route, masks and saved
layout. Review run39951546091 tested merge
`52f3008080027a15975d8cfae2228c5f2ae41ca7`: 4,719 Windows cases, 4,708 passes,
11 expected failures and zero errors/skips. The final correction addressed six
route/handle findings; three current-View cases and two saved-layout cases were
closed by their separately reviewed increments. Digest-matched JUnit readback
preceded production fixes/publication as recorded in the plans.

Fresh source reviews accepted ordering, locale/vendor dependency, script-provider
custody, current routes, L1-D geometry and lifetime cleanup. Combined review
verified the owning parents' critical functions unchanged and all tracked Python
files parsed. Preceding other-session PR101's seven changed files and finite
Authorization/rejection-diagnostic contracts were reviewed and preserved byte
for byte. Its independent live PDF evidence is not reused here.

## Final runner and package evidence

| Candidate | Head | Tested merge | Run, attempt 1 | Windows passes | Portable overlap |
| --- | --- | --- | --- | ---: | ---: |
| PR104 | `479a451d9c362f09206c5bcc7a8567db9010b0f2` | `be6031c602b14d4f004c8befad962d1206739701` | [39954698732](https://github.com/cepeter-job/spt-downloader/actions/runs/39954698732) | 4,825 (2,466 + 2,359) | 710 |
| PR102 combined | `e0e4aa11c0f5d4f9c89dccd52ebb87264b056a27` | `3431738fb3637e8470aba8cf8aa1e169794dcb6a` | [39955033389](https://github.com/cepeter-job/spt-downloader/actions/runs/39955033389) | 4,926 (2,514 + 2,412) | 710 |

Both runs have zero test failures/errors/skips. Downloaded JUnit and inventory
archives reconcile exact metadata, selected test universes and passing phases.
Windows shards are disjoint; portable cases overlap Windows. Combined evidence
contains both review-RED universes and all four script-provider controls, with
the two source-corrected dated expected-label node IDs mapped explicitly.
Required Actions and CodeQL checks passed. Before merging PR102 after PR104,
the latest-main merge tree was verified identical to its tested tree; actual
merge trees were then read back from GitHub.

| Downloaded package | Artifact ID | ZIP SHA256 |
| --- | ---: | --- |
| PR104 distribution | 12502249304 | `0ad8397c6209b5abec07227538cfd3bf9aabf6ec951bbc599710df7e813b59ea` |
| PR104 bootstrap | 12503430115 | `7f629a6073d2ff97a1e19719f1c076f685c13e35869d7453581bca9aec3ff650` |
| PR102 distribution | 12503530279 | `185a90092c0d225a2a6195a6d0309e2517dde86fa690799fe52ed573e61cdada` |
| PR102 bootstrap | 12503675810 | `730e994cdbb3f92df33b1b49f46c2362a915e6275a7700bba8ea6b987bc64149` |

Each package was downloaded by exact run/artifact ID and inspected without local
execution. Seven allowed members, manifests, build identity, SBOM/runtime lock,
all45 embedded worker sources and source/frozen self-test evidence match the
tested tree. Packaged cold setup, reuse, cancellation and owned cleanup evidence
also passed readback. Executable SHA256 is
`7d08720a970c284a9cb395bfefa14eb66b4d9a680bac8eb93b4fe84556fdc6e9`
for PR104 and
`becb22072b6b7b5127aff668c405180797d9ccf800e599f5dc58db4dea8f9cdf`
for PR102. CI provenance jobs were skipped under existing PR policy. These are
CI-verified PR packages, not an attested main release or installed application.
No CI, dependency lock, worker allowlist, resource or LICENSE change was needed.

The separately authorized same-return PPh21 live refresh on the combined tree
is recorded in [the period/benchmark report](2026-10-23-json-period-and-benchmark.md).
Private captures and generated workbooks remain outside version control.
