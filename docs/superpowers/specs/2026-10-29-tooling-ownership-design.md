# Tooling configuration ownership

Issue #130 item 2 and the configuration follow-up in #134 require one owner for
each tool's effective policy. At main `54ab897b`, CI explicitly uses
`.coveragerc`, including `${RUNNER_TEMP?}/.coverage-portable`. The duplicate
`[tool.coverage.*]` blocks in `pyproject.toml` omit that data-file boundary.

Remove only those duplicate blocks. Keep pytest defaults/project metadata in
`pyproject.toml`, lint policy in `ruff.toml`, and coverage policy in `.coveragerc`.
Keep all CI commands, thresholds, omissions, dependency locks and product files
unchanged. Document the supported ownership in contributor guidance and AGENTS.

Migrating coverage into TOML would require changing CI and reproducing its
environment semantics; it conflicts with the explicit #134 direction. Keeping
both policies perpetuates drift. Ruff migration and package-version metadata
policy remain separate follow-ups.

Verification uses a runner-only before/after probe with the pinned coverage
library: compare effective default/explicit coverage settings and the runner
data-file boundary, demonstrate the historical alternate TOML policy, verify
that TOML no longer supplies a competing policy, and prove all other TOML
settings/configuration bytes are unchanged. Existing full Windows/portable
tests and package/provenance gates remain authoritative. This configuration
cleanup adds no permanent test that merely checks removed source text.

The user's standing autonomous-execution instruction applies. Work reuses the
existing isolated worktree; actual test/tool execution stays on GitHub runners.
Review preceding other-session changes, especially PR138 if merged, before merge.
