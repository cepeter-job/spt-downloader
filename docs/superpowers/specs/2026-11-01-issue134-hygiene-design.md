# Issue 134 configuration and import hygiene

Baseline: main `8971bbcb8a981c98e7990a81dd2b7467d4a47231`, after PR165.
The user chose EXE distribution with commit/run identity; pyproject is tooling
configuration, not a request to add a Python package distribution.

## Approach

Remove unused PEP517/project declarations rather than invent a semantic version
or add an SCM packaging dependency. Keep the existing build-info, locks, SBOM,
worker allowlist and EXE distribution contract. Pytest/mypy settings retain
their current values; coverage remains owned by `.coveragerc`.

Use the pinned Ruff0.17.2 baseline from runner41327572683, artifact13091039618.
It reports135F401 and127Bugbear findings. Fixture registration and compatibility
exports are behavior, even when Ruff cannot see their consumers. Make those
exports explicit with same-name aliases; remove only reviewed dead imports.
Enable F401 across the repository without per-file exclusions or autofix.

Triage Bugbear findings by their actual owner and consumption lifetime.
Adopt the zero-baseline mutable-default/control-flow checks B006/B012/B016/
B018/B020 incrementally. Do not change zip truncation, synchronous callback
lifetimes, immutable fixture defaults or PyInstaller attribute access merely
to satisfy the remaining warnings. Record every disposition in the audit.

Add compact AGENTS navigation and replace its current worker-count claims with
the explicit WORKER_FILES owner; historical commit/run reports stay unchanged.

## Verification and boundaries

Only source/AST/TOML/diff and artifact inspection execute locally. A separate
runner probe records baseline/candidate lint and actual negative diagnostics.
The unchanged full Windows/portable, quality, coverage, packaging and bootstrap
gates remain mandatory. Verify exact head/tested tree/run/attempt/artifacts,
review preceding merged PR165 and recheck latest main before merging.

No capture, financial, publication, filesystem or authentication behavior is
part of this change. Conditional helper extraction remains a separate decision
under issue134. Do not rewrite private workbooks or retain real taxpayer data.
