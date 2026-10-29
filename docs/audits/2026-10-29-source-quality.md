# Issue 130 source quality audit (2026-10-29)

This replaces historical estimates with an explicit current source inventory. Baseline is the integrated CLI tree `d1eb08c20090c493e61032ae6c59b919143a4a5f`; subsequent changes are bounded to startup cleanup, fixed detail error categories, documentation and same-owner list restoration extraction. Public API and function tables are source inventories; they make no runtime or live-account claim.

The refreshed tables describe commit `f120c668a927da59453a9c054ef2c3fdefafeb93`, equivalent production source to PR #140, including the final diagnostic comments. `--revision` resolves a commit before listing/reading bytes; dirty, deleted and untracked working files cannot change the named snapshot.

Final production recount also inspected immutable commit
`b5bcab9a05a1050d9496d1cfc3dfc82036fb0d85`, exact tree
`6697739a47f16d2b17cca12ad23446f1c605c1eb` shared by PR142 head
`bf69d3e7b3a73b044af1660459576fa321662b17`. After typing/security and coverage
integration, production totals remain851functions,46spans>80,254AST decisions>10,
211public top-level entrypoints and99without docstrings. There are105non-test
broad-catch sites and27skip/xfail call sites repository-wide. Detailed tables keep
their original named snapshot and line numbers; later source-local Bandit
comments do not change those classifications. CI-only gate helpers are outside
the explicitly defined production metric, without being omitted from coverage.

## Definitions and reproduction

`python scripts/quality_inventory.py --output <scratch>/quality.json` uses stdlib AST on `git ls-tree` / `git show` at an explicitly resolved commit, never product imports. Production scope is root `coretax*.py` and `spt_desktop/*.py`. Each sync/async function is counted separately, including methods/nested functions. Span is physical `end_lineno-lineno+1`, including docstrings. Complexity is a documented AST decision count: 1 + if/for/async-for/while/except/conditional/comprehension clauses + additional boolean operands + match cases; nested function/class/lambda bodies belong to their own scope. It is not claimed to equal Radon/McCabe. Public module entrypoints are top-level functions without a leading underscore; methods/nested functions remain in the full function table. Documentation counts indicate presence, not quality.

| Measure | Baseline | Updated source |
| --- | ---: | ---: |
| Production functions | 850 | 851 |
| Physical span >80 | 46 | 46 |
| AST decisions >10 | 253 | 254 |
| Public top-level entrypoints | 211 | 211 |
| Entry points without docstring | 107 | 99 |

Baseline `collect_details`: 201 physical lines, 48 AST decisions.

Updated `collect_details`: 176 physical lines, 36 AST decisions.

## Decisions

Extracted `_restore_inventory_page` in the existing browser module: one cohesive owned-list restoration stage returns the actual observer response. Original page-size/paginator operations, offsets, Stop checks, module monkeypatch namespace and call order are preserved. Caller still installs the original filter, checks selected identity/metadata, prepares JSON and rechecks immediately before held View. Existing protocol, restore, ownership, metadata and real browser regressions remain unchanged. No new module/worker resource or broad filesystem/source-reader refactor is introduced.

Improved fourteen substantial public contracts: inventory/detail/checkpoint, inventory JSON adaptation, export validation/workbook/split export, MPN validation/provenance/custody, worker terminal result, publication, authentication and runtime setup. Their docstrings describe input/output, refusal, ownership and independent completion gates. Trivial presentation/render helpers do not receive mandatory ceremonial docstrings. The table retains every module entrypoint, including those intentionally left as implementation helpers.

See [exception decisions](2026-10-29-exception-inventory.md), [all production functions](2026-10-29-quality-functions.md), [public entrypoints](2026-10-29-public-api.md), and [test skip register](../test-graveyard.md). The source inspector adds no product dependency and is absent from the explicit worker resource allowlist.

## Runner evidence

RED runner [40802024409](https://github.com/cepeter-job/spt-downloader/actions/runs/40802024409), attempt1, observed eight intended failing cases: four raw-detail-message/stringification cases, one obsolete runtime skip, and three startup-acquisition cases. The other 157 selected cases passed. Pinned tool baseline [40801804002](https://github.com/cepeter-job/spt-downloader/actions/runs/40801804002): Bandit1.9.4 found30 sites in2.963s; mypy2.4.1 found15 errors in the two selected stdlib modules in0.845s. These are baseline results, not passing gates. GREEN/full suite/review evidence is recorded only after actual execution. No live Coretax or interactive Excel validation is implied.
