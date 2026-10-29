# CLI failure recovery (issue #134, first implementation PR)

The reviewed issue authorizes small sequential PRs. Start with its confirmed CLI
error/interruption defect on main `54ab897b`: a second `save_output` failure or
resource cleanup failure can replace the original outcome. PR137's streamed MPN
proof, PR132's safe diagnostics and PR133-136 capture contracts stay intact.

Keep successful export unchanged. On failure/Stop, set the in-memory run PARTIAL
and attempt only the existing guarded atomic run.json checkpoint after normal
export-run and existing folder/physical-workbook/selected-JSON scope validation.
Never retry workbook publication from an error handler.
An invalid run or failed checkpoint leaves the prior durable bytes untouched.
Use fixed error messages and the existing sanitized exception diagnostics.

Own the driver, owned context and newly created page in a LIFO cleanup stack.
Attempt every registered close even if one fails. Ordinary cleanup errors cannot
replace an active failure or Stop; Stop still outranks ordinary failures. A
cleanup failure after successful work is an error, not a COMPLETE CLI result.
Retain exit 1 for error and 130 for KeyboardInterrupt/CaptureCancelled. Reused
browser contexts remain external; close only the CLI-created page and driver.

Approaches: guarding save_output would preserve the expensive and unsafe retry;
checkpoint-only recovery is the narrower issue-approved behavior. A whole CLI or
filesystem refactor is unnecessary. These implementation choices are the agent's
calls under the user's instruction to start issue134.

Prove real _main failure paths with synthetic browser-boundary doubles and real
filesystem/checkpoint writes. Include ENOSPC/permission/replace failures, invalid
scope, original error plus cleanup errors, Stop, normal cleanup errors, no-run
startup failures, reused context ownership and no recovery export. Product tests
and package execution stay runner-only. No live accounts or private data.
