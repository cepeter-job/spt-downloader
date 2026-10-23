# Native JSON readiness: verified first slice

Status: implemented and runner-verified on 2026-10-23; merged [PR #85](https://github.com/cepeter-job/spt-downloader/pull/85). This report closes shared native panel readiness and guarded pagination. It does not close the complete [JSON program](../specs/2026-10-23-json-mode-completion-design.md).

## Result

Corporate, PPN, PPh21 and Unifikasi observers now follow the current owned tab binding through the existing bounded `_wait_tab_panel` helper. `_native_panel` carries pre-click controlled identity, clicks once, and preserves inspected href, caption, direct ownership, duplicate-target and final source-URL checks. An initially unbound tab may use exactly one visible owned panel. A binding gap after a controlled binding cannot authorize a different form.

The native `_turn_grid` walker uses the inspected table-owner paginator controls. Pointer interception retains the previously reviewed guarded click policy. Reset and forward traversal each require a changed marker; repeated/no-advance states, unavailable controls and page limits refuse native coverage. The page budget is checked before opening another page. Stop propagates through panel retries and grid traversal.

No endpoints, source pins, workbook resources, worker allowlist, dependencies or workflows changed. Unsupported native structure retains whole-record fallback; identity/privacy/authorization failures and Stop keep their existing exception contracts.

## Exact verification coordinates

| Evidence | Coordinates |
| --- | --- |
| Upstream `main` preserved | `dabcbdfb4a8887da842e04db54af2bc262fc5d3d` |
| Final code/test PR head | `64e851a9fbbc2b5d6b565725fdeebd5e7b1c837d` |
| Tested PR merge | `c44cef728e6fd80db07e43b71006b8a72b69ba57` |
| Tested merge tree | `6e670ad1a047b005c4571490b6c9aee8bde1491c` |
| Local recovery with identical tree | `c6725f95d0313acb7f4d76ec8166cdec7e5b753b` |
| GREEN run / attempt | [39874749518](https://github.com/cepeter-job/spt-downloader/actions/runs/39874749518) / 1 |
| Windows shard 0 JUnit | artifact `12468103553`: 2,061 passed, zero failures/errors/skips |
| Windows shard 1 JUnit | artifact `12468865761`: 1,954 passed, zero failures/errors/skips |
| Complete Windows inventory | 4,015 distinct cases; all 54 new native cases passed |
| Portable JUnit | artifact `12468191565`: 696 passed, zero failures/errors/skips; overlaps Windows |
| Distribution | artifact `12468885307`, production CPython 3.14.8 x64/GIL |
| Packaged bootstrap | artifact `12468651269`: cold install, reuse, cancellation and owned cleanup passed |

Routing/actionlint, locked dependency audit, both Windows partitions, portable tests, package and combined validation succeeded. PR provenance/branch-cleanup jobs were intentionally skipped by existing policy; this is a CI-verified PR artifact, not an attested `main` release.

Downloaded artifact ZIP SHA256 values matched their GitHub API digests:

| Artifact | SHA256 |
| --- | --- |
| Windows shard 0 `12468103553` | `efa262665c535dee346b2d270ec399c06d5befa839a98bff93a12ac55af0784c` |
| Windows shard 1 `12468865761` | `8a081f6bfdda5e236c1967aa2bbf0c2aa2efee2d7ed88a4f0da738f2b09c5f35` |
| Portable `12468191565` | `f3e41253bf5d92da53666da535b4a6cad90f3a9ef3f36287d6b7c2ab5c356ebd` |
| Distribution `12468885307` | `55d4344b26e319f87637a494e41dcd1dce834bb73d1702fa77b890dae2d97f52` |
| Bootstrap `12468651269` | `571d58b4906a575c0c225c7a4d026c59d6835e4089a55c61ba9c78c70960c77c` |

Archive inspection verified the exact seven-file distribution allowlist and every SHA256SUMS entry. The executable hash is `27085c5703aecb0c36d123de7725178b291a722f2b61df6c1c00df69a41c1c9d`. External and embedded build identities match the tested merge/run/attempt; SBOM metadata binds that identity and executable. All 44 explicit worker resources in the frozen CArchive match the tested source bytes. Frozen self-test reports production 3.14.8, x64/GIL, successful GUI/worker checks, `live_scrape=false` and `credentials_accessed=false`. The separate bootstrap report binds the same executable and distribution artifact ID. Local inspection read archive/AST/hash metadata only; it did not run the executable or import product modules.

## Regression and review evidence

Tests-only head `1b82115a3a77f9e441fd817e49efb48ce56a41e8` was tested as merge `7037c51ad7a7e82219ffc34dc945fd33c9bbf165`, tree `99b1e8f0baa679a28605c8be42a7f0a755f32389`, in [RED run 39871715792](https://github.com/cepeter-job/spt-downloader/actions/runs/39871715792). Its 4,003 Windows cases had 16 failures, all in the 42 new contracts; 3,961 prior cases and 26 new safety cases passed. Production edits followed this observed RED. All 16 failing nodes have passing successors in the final 4,015-case suite.

Fresh-context source review found no production defect and identified one Important fixture gap: the initial synthetic rebinding occurred before the click. The original cases were retained, and 12 additional family-specific cases now prove a real stale post-click read/timeout/retry, physical `li` reordering behind live `nth()`, and Stop after the first readiness wait failure. Corporate uses its four-form fixture with grids. The reviewer confirmed the gap was addressed without further findings, and all corrected cases passed on the final tree.

The suite preserves native DOM value getter traps and checks expected form counts, one intended click per tab, refused unsafe targets, unchanged request scope, explicit capture completion, and no later traversal after Stop.

## Remaining JSON program

- Corporate L1-D/L3/L11-A/L11-C source coverage and semantic projection into approved form layouts remain separate work. Root-property discovery alone does not prove final values, dependent predecessor data or recomputed totals.
- PPN Normal/AskedTo branches still require the pinned final lifecycle proof, including later subscriptions and calendar conditions.
- Dated reference catalog/clock custody contracts merged through [PR #86](https://github.com/cepeter-job/spt-downloader/pull/86); they are not part of this verified artifact.
- Five historical JSON guides were reconciled to merged implementation evidence while retaining historical RED/PARTIAL and scope-specific live boundaries.
- This historical slice performed no real-account capture or installation. The later [matched PPh21 benchmark](2026-10-23-json-period-and-benchmark.md) closes current-build acceptance for the selected December 2025 Normal return; other families retain their own scope and acceptance gates. L7 semantic coverage and its deferred regressions are also merged.

Later documentation-only commits may extend this report and plan. The package and execution evidence above belong specifically to the code/test tree shown in the table.
