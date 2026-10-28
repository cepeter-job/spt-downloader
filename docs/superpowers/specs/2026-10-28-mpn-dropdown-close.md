# Accounting dropdown close readiness

Normal full-job validation reproducibly stops before inventory when the second
dropdown's `No` locator sees multiple options. The same pinned source has only
one Yes/No pair per panel. A slower instrumented probe succeeds; removing its
post-dropdown diagnostic RPCs reproduces the refusal. Sanitized frames bind the
failure to `_dropdown` / `_ready_one` duplicate readiness; after those RPCs one
panel remains. This is the preceding panel's asynchronous close overlapping
the next inspected open action.

After selecting an inspected option, wait for visible dropdown panels to close
before returning to the caller. Use the same shared 45-second preparation
deadline, value-free structure, Stop and retained Document/source/observer
checks. Probe in short bounds and reconcile callback failures before any next
action. Never repeat an actual click, sleep a fixed settling interval, read a
selected value or relax duplicate-option refusal. A stuck panel remains PARTIAL.
No source pins, queries, native eligibility or output contracts change.

Runner tests reproduce delayed panel removal and a stuck panel, preserving
single actions and the supported ordinary immediate-close case. Local live
validation remains the operator's already authorized same-job exception.
