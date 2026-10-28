# Capture failure privacy and recovery

PR132 must preserve best-effort diagnostics: a failed home/workspace lookup,
including RuntimeError, cannot prevent the CLI from running, even with logging
OFF. Keep the existing closed exception-type/frame sanitizer; it reads no
exception message, args, locals or chain. Never serialize arbitrary class names.

Capture checkpoints and inventory progress use only the fixed failure messages
`capture_timeout`, `capture_safety_refusal`, and `capture_failed`. Classify the
actual caught Playwright TimeoutError and JsonSafetyError by type, never by text.
Sanitized diagnostic frames identify the failing owned operation. Existing
PARTIAL, filter/snapshot refusal, Stop, later-panel recovery and financial PDF
gates remain unchanged. Old checkpoints remain readable.

Tests must invoke actual capture_detail/collect_inventory and the real bounded
logger against isolated synthetic pages. No mirrored exception handler or source
comment assertion establishes behavior. Retain the PR's independent table dxfId
repair, inspected request-shape handling and opt-in pre-commit configuration.
No new module, dependency or worker allowlist entry is needed.

Product tests/builds run on GitHub runners. The operator's prior local exception
is limited to the same-job MPN diagnosis/validation, not these regression tests.
Review preceding other-session merged PR128 and latest main before merging.
