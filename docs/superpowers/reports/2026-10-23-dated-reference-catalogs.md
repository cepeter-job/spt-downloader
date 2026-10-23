# Dated JSON reference catalogs: verified slice

Status: implemented and runner-verified on 2026-10-23 in draft [PR #86](https://github.com/cepeter-job/spt-downloader/pull/86), dependent on native-readiness [PR #85](https://github.com/cepeter-job/spt-downloader/pull/85). This closes the dated grid-reference workstream in the approved [JSON program](../specs/2026-10-23-json-mode-completion-design.md); corporate semantic projection, PPN final lifecycle and live acceptance retain their own gates.

## Result and source contract

PPh21 and Unifikasi grid labels can use the inspected active-version selector when one source row is selected throughout the owned browser-clock interval. Source order matters: first own null/empty `ValidTo`; otherwise first future `ValidTo`; otherwise latest valid `ValidFrom` with stable ties; otherwise first candidate. Every cutoff within the interval is checked, including a possible A -> B -> A selection with equal endpoints. Model and PERIOD dropdowns keep their distinct-code rules.

Source proof is the unauthenticated pinned `main.cccfdb820c20596c.js`, 4,357,138 bytes, SHA256 `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd`. `getActiveReferenceDataValue` at UTF-16 offset 3017141 supplies the ordered selector. The source was inspected as text; that inspection is not live execution evidence.

The producer samples browser epoch milliseconds/timezone before View and after final response drain. Optional version-1 manifest metadata binds the same attempt, record/scope and response custody. Live iteration and checkpoint replay carry the validated interval without consulting the replay machine's clock. Original response bytes and descriptor hashes remain unchanged. Missing or unavailable sampling leaves new calendar-dependent branches unsupported; malformed recorded metadata, mixed/missing packet evidence within an attempt, descriptor-local clocks and mismatched attempts are rejected before projection/fallback.

Final environment sampling can pump network events. A newly admitted request leaves the attempt PARTIAL, including an excluded-MIME reply that has already left the pending set. Earlier drain-timeout counts survive, newly unresolved replies add to them, late bodies remain unread, and repeated drain returns its cached result. Stop and binding checks surround both samples. Clock metadata cannot authorize an incomplete native capture.

Candidate Code/CodeDescription/ValidFrom/ValidTo paths, the selected row/rule and required clock evidence remain in provenance. The deliberate parser subset accepts full `YYYY-MM-DD` dates and second-resolution ISO datetimes with optional three-digit milliseconds and Z/numeric offsets, years 1970..9999. Date-only UTC and offset-free Asia/Jakarta datetime behavior follow [ECMAScript Date.parse](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-date.parse). Calendar normalization, `24:00`, expanded years, historic local offsets and other spellings are unsupported. Integer millisecond arithmetic avoids floating timestamp rounding.

No endpoint, POST permission, source pin, worker module/allowlist, dependency, workbook resource or workflow changed. The six product files are existing capture, packet, catalog and projection modules.

## Exact final verification

| Evidence | Coordinates |
| --- | --- |
| Preserved upstream `main` | `dabcbdfb4a8887da842e04db54af2bc262fc5d3d` |
| Final code/test PR head | `9997c80bc9011b9d5768998b215dd0b7269d8369` |
| Tested PR merge | `c099aab8f95ba4cb98f7448ea2e0b994ae98d32b` |
| Tested merge tree | `7e73f1b4c9146594ebc7c2835233dec94c66057e` |
| Local recovery with identical tree | `6025cc506976d9e374b6719e694ebfb11fd96a25` |
| GREEN run / attempt | [39884865149](https://github.com/cepeter-job/spt-downloader/actions/runs/39884865149) / 1 |
| Windows shard 0 JUnit | artifact `12472517374`: 2,097 passed |
| Windows shard 1 JUnit | artifact `12472294075`: 1,986 passed |
| Complete Windows inventory | 4,083 distinct cases, zero failures/errors/skips; all 4,015 baseline and 68 new dated-reference cases passed |
| Portable JUnit | artifact `12472277330`: 696 passed, zero failures/errors/skips; overlaps Windows |
| Distribution | artifact `12472746609`, production CPython 3.14.8 x64/GIL |
| Packaged bootstrap | artifact `12473110134`: cold install, reuse, cancellation and owned cleanup passed |

Routing/actionlint, dependency audit, both Windows partitions, portable tests, combined validation and Windows package succeeded. PR provenance and completed-branch cleanup were intentionally skipped by existing policy. This is a CI-verified PR artifact, not an attested `main` release or real-account acceptance.

Downloaded ZIP hashes matched GitHub's artifact digests:

| Artifact | SHA256 |
| --- | --- |
| Windows shard 0 `12472517374` | `99242891a649349cd3e28cbc2c701853d681f45bc06ee938de6af488a848be32` |
| Windows shard 1 `12472294075` | `ea91012f63a2e78a2a2195f251f1846738e4c08c2e69e8170ada45fcbb8c6bca` |
| Portable `12472277330` | `16d5bf49094f2e7cb44377cd0cc17cead0df3aa6ef860c2d4cff310c52846e8e` |
| Distribution `12472746609` | `e5616b4173219b05d8557390a6774ff1eaad471c0c28fbf893629c5caec6ee92` |
| Bootstrap `12473110134` | `1522cadeae951320468861729a31d7a8fcc8095f41fab560ae49c1fea146727b` |

Archive inspection verified the exact seven-file distribution allowlist and every SHA256SUMS entry. Executable SHA256 is `1106005bebba02544ee736cbc3040d808db33fc6f4590b4819f4586b8ff5b287`. External and embedded build identities, SBOM application/run/runtime-lock metadata, bootstrap executable/artifact identity and all 44 explicitly allowed worker source files match the tested merge/run/attempt. Frozen self-test reports production 3.14.8, x64/GIL, successful GUI/worker checks, `credentials_accessed=false` and `live_scrape=false`. Local inspection read archive, AST and hash metadata only; no product imports or executable runs occurred locally.

## Regression evidence and review

Authoritative corrected tests-only RED was head `30315c9914730c322047d87e57b32ccb317da4dd`, merge `3fc1da30bc3f9fae6a19630102edae17d0cd091a`, tree `e24dfa3ed187c94c1787373cd1c0872cb0b2f309`, [run 39877496900](https://github.com/cepeter-job/spt-downloader/actions/runs/39877496900), attempt 1. Digest-matched artifacts `12469891197` and `12468899986` contained 4,075 Windows cases and 52 new failures, zero errors/skips. All 4,015 prior cases and eight new availability/safety cases passed. Corresponding producer, checkpoint-tamper, Stop, packet-clock, selector, full native and workbook failures were read before product edits.

An earlier packet fixture paired a generic 2024 scope with Masa 2025 packets. It was corrected before packet production implementation. Those wrong-scope negative passes are not safety proof.

The first implementation [run 39879168027](https://github.com/cepeter-job/spt-downloader/actions/runs/39879168027), head `b1bf20b504eb267553922ba26cc7fdaf2c4aae1a`, merge `21cd5a95fda78aace0a87ce30ccaa723fda5fb7f`, tree `f87e9aefadc4f17e560b009773114ff754972147`, had 4,078 cases and five new failures. Two exposed accepted `24:00` outside the documented subset and led to explicit hour/minute/second bounds. Three were fixture errors: an interval that did not actually change the chosen row, and two Unifikasi workbook cases using placeholder geometry and an intentionally omitted PaymentMethod display. Corrections use an actual cutoff, approved headers, canonical assertions for all four labels and workbook assertions for the three displayed bindings. Existing PaymentMethod omission policy and full source retention remain intact.

Fresh-context whole-slice review found a late excluded-MIME COMPLETE bypass. Tests-only review regressions at head `40dfc4ec8a62f10913f1f2c2034b09faa0cd349c`, merge `bfdcecddc5e94b47fc19fa04798b36b705ccafe0`, tree `3497b2a7102b034a4293ec47b3d2cc92d404f41a`, [run 39880814143](https://github.com/cepeter-job/spt-downloader/actions/runs/39880814143), proved both excluded-text/missing-MIME completion errors and both date-hour rejection errors. Artifacts `12471395339` and `12470807066` contained 4,080 cases and four new failures. Source correction snapshots admitted-request count before the final sample.

Follow-up review identified replacement of an earlier pending count after a normal drain timeout. Three combined deadline/late-reply cases were added. Their initial wrapper-signature failures in run `39882253810` were fixture errors, not production RED. The corrected tests-only head `79d30babc8d3f6117cde91deb47af6f932872a5e`, merge `4fd5f06cfbf27f5b230b5f894368fc4c6b343656`, tree `58cc68c377f531d9956f125e37eb834ef2749810`, [run 39883507395](https://github.com/cepeter-job/spt-downloader/actions/runs/39883507395), produced three actual pending-count failures in digest-matched artifacts `12472302079` and `12472276603`: JSON `1 != 2`, excluded text/missing MIME `0 != 1`. The one-line accumulation correction followed that evidence. The reviewer confirmed both findings addressed with no remaining blocker.

All 57 distinct authoritative failing nodes from these RED runs have passing successors in the final suite. Full native/saved-workbook cases preserve source bytes, label provenance, explicit fallback, literal model/period, approved clean layout and DOM value getter traps.

Automated review alerts were checked against their source coordinates. Missing `clock_interval` parameter alerts link the initial tests-only tree; current signatures include it. The `finish` fixture keyword was corrected and rerun. Tuple-length alerts count the two syntactic elements of a starred tuple return; the validated `(ordinal, row)` pair expands with the rule to three values, exercised by legacy and dated catalog tests. The mixed module/from import note is minor and intentional so the deadline fixture replaces only the module's time binding.

## Remaining program

Corporate L1-D/L3/L7/L11-A/L11-C coverage and semantic projection into approved layouts remain separate work; the focused L7 source proof and test preparation do not yet grant native eligibility. PPN Normal and remaining AskedTo branches still need their complete final lifecycle proof. This clock implementation alone does not close those consumers.

No exact authorized live taxpayer/year scope was selected, no real-account capture was performed, and no distribution was installed or published by this slice. Current-build live acceptance and paired DOM/JSON timing remain open. Later documentation commits may extend this report; execution and package evidence belong to the exact code/test tree in the table.
