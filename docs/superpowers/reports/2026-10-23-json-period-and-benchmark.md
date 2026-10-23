# Literal JSON periods and matched PPh21 benchmark

The period and owned-browser environment repairs merged in [PR #95](https://github.com/cepeter-job/spt-downloader/pull/95)
as `9751650f14d4301c5b009849dc66fe508ad3b37c`, tree
`dc69f525e512d18649b7316da59adfb2571f6538`. Test-only [PR #97](https://github.com/cepeter-job/spt-downloader/pull/97)
is included and GitHub records it merged through the same commit. The installed
application and earlier taxpayer outputs were preserved.

## Repairs

Matching literal source periods such as `12122025` now bind directly to their
JSON detail alongside the already supported exact captions. Metadata stays
literal. Different raw periods, malformed periods and conflicting years remain
fatal even without native listing eligibility. Missing native identity fields
still prevent native eligibility.

The first live run after the period repair exposed a separate environment gate:
inherited en-US failed the reviewed PPh21 id-ID requirement. Application-owned
desktop and CLI contexts now explicitly use id-ID and Asia/Jakarta. Externally
reused contexts retain their checks and fallback. Authentication, challenge,
taxpayer, origin, Stop and owned cleanup contracts remain in force.

## Same-return live benchmark

The user authorized local execution for the same submitted **PPh Pasal 21/26,
December 2025, Normal** return. All four runs used the same saved selection and
literal metadata, fresh profiles and submitted inventories, separate outputs
and no checkpoint reuse. Verification for other work remains runner-only.
Taxpayer identifiers and values are excluded from this report.

| Order | Actual source | Total seconds | Details seconds | Forms | Capture and mapping |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | DOM | 89.887 | 42.266 | 5 | COMPLETE |
| 2 | JSON | 83.471 | 37.551 | 5 | COMPLETE |
| 3 | JSON | 85.878 | 38.377 | 5 | COMPLETE |
| 4 | DOM | 89.883 | 44.266 | 5 | COMPLETE |

Median total was **89.885 seconds for DOM** and **84.6745 seconds for JSON**:
JSON was **5.80% faster** on this return, a DOM/JSON ratio of 1.062. Total starts
at parent launch and ends after worker exit and completed owned cleanup. It
includes login, inventory, details, publication and independent output readback;
runtime preparation is excluded. Detail timings are inclusive and are not added
to total again. Two observations per mode establish no universal or statistically
established performance ratio. All runs ended exit 0, zero errors and completed
owned cleanup.

The unchanged 417-file source archive came from tested merge
`0a75593346748f0e0460f356c0c2e34cd1ccb7cb`, on main
`a15ea7bfd73298d6c10bccf52c3257669d43bd88`. Its tree matches the final merged
tree. The then-head `8a509ff5dd0623fd96167a54c4bd0700a13745dd` and later
merge-only head `25979dc2f80a51158bd72f74a6cdc0de0a2dd2ad` share that tree.
No tracing or harness environment override was used; locale/timezone came from
product code.

## Completeness and fidelity

Both modes retain five approved form sheets with complete mapping reports.
Each JSON trial additionally proves seven grids, including explicitly empty
grids, and 19 declared body rows. DOM and canonical table-value row counts use
different footer representations, so they are not compared as body coverage.

Each pair has 447 populated visible cells per mode: **445 exact matches** and
**two source-preserving whitespace differences**, at L-IB C8 and L-II C8. JSON
retains surrounding ASCII spaces in the original Name fields; DOM trims visible
text. Every difference was independently verified against its form/table/row
binding and original response bytes/hash. No source value was normalized to
force equality. There are zero unexplained differences. Formula text, styles,
merges, dimensions, row/column geometry, print setup and sheet sets match.
Outputs are identical within each mode.

Each JSON run publishes 14 declared evidence files, including the manifest,
under `json/` directly inside its final SPT output root. Original private
`returns/json/` captures remain for checkpoints. Both copies and all hashes were
checked; unrelated files are excluded. Workbook inspection read saved OOXML only,
without Excel recalculation, macros, refresh or edits. Private captures,
workbooks and detailed reports stay outside Git.

Earlier calibration attempts are preserved and excluded from these statistics:
the original period failure, a transient pre-View list restoration failure,
explicit DOM fallback under the inherited environment, and a traced environment
experiment. COMPLETE fallback does not count as native JSON acceptance.

## Exact runner evidence

[Run 39930497942, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/39930497942)
tests head 25979dc2 as merge `dd0751b4c3d7217652b8b91f1961d290240026a7`,
tree dc69f525. Required Actions and CodeQL checks passed. Inventories reconcile
4,437 distinct Windows passes in disjoint shards of 2,270 and 2,167, with zero
failures/errors/skips. The 710 portable passes overlap Windows. Prior identical
tree run 39926454688 also reconciled all 34 distinct intended RED nodes and both
L7 regressions to passing successors.

| Downloaded evidence | Artifact ID | SHA256 |
| --- | --- | --- |
| Windows shard 0 | 12492301462 | `fc677422c3d36a53faeb55d30f895070a59088b8223bc93e9be891c5e013a498` |
| Windows shard 1 | 12491383302 | `45127be5453b01a013817fc6048229202caa97350b7eeeb7297ac2f6025775d9` |
| Portable | 12491098287 | `ae03b7c40ecaafd661f7a8fdbfe315229f54eb6e2751077a736347ae97206551` |
| Distribution | 12492790020 | `dece8826d41b533bb49bf3a24e1e2dac3c18f28c24d375ae3dde160c9e576937` |
| Packaged bootstrap | 12492076619 | `d55cd940bc8174b02b4a74746d7589566d51aa5ffee106932d067ce103dc7261` |

ZIP hashes match API digests. Readback verifies the exact seven-file allowlist,
member manifest, external/embedded build identity, SBOM/runtime lock and all 45
explicit worker source files. Executable SHA256:
`c155091968c878e2c64fe3f2b3322fca10a322536c5510a8e9a3d100d03f99e4`.
Source/frozen no-account tests and packaged cold install, reuse, cancellation
and owned cleanup passed. Package reports have `live_scrape=false` and
`credentials_accessed=false`; the separate authorized source benchmark supplies
the live evidence above. This is CI-verified PR packaging, not an attested main
release or an installed distribution.

Fresh source reviews covered the period repair, environment increment and L7
regressions. The preceding other-session PR96's PDF, L8, layout and Audit changes
were reviewed and included. Strict latest-base rules initially refused merging;
a merge-only commit and full rerun satisfied those rules without CI changes.

## Remaining program

Native readiness PR85, dated references PR86 and L7/consolidation PR88 merged
through `8391dde2fa78afdbcc9f2ee07502d4f603fa15ee`; their original artifact
coordinates remain historical evidence. PR95/97 closes the new period/environment
repairs, matched PPh21 acceptance and deferred L7 tests, while broader corporate
semantic/native coverage and PPN final-choice branches retain separate gates.
[PR98](https://github.com/cepeter-job/spt-downloader/pull/98) merged the
[reviewed L11-C semantic branch](2026-10-23-corporate-l11c-semantic.md), and
[PR99](https://github.com/cepeter-job/spt-downloader/pull/99) merged
[PPN final-choice invariants and the narrow Normal branch](2026-10-23-ppn-choice-invariants.md).
Both have exact runner/package evidence and separate supported boundaries.
L1-D continues in draft [PR102](https://github.com/cepeter-job/spt-downloader/pull/102);
its pure helper and tests do not certify native eligibility. L3/L11-A, remaining
corporate semantic destinations and unproved PPN lifecycle branches retain
their own source/runner gates. Current-build live acceptance for other families
needs an explicitly selected scope. Missing consumer proof or live scope stays
open with truthful fallback/PARTIAL.
