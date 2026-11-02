# Shared literal capture-mode contract

The user authorized main-package verification, dependency assessment and a
bounded follow-up to issue134. Baseline is merged main39c7de577d74a45092127ab0d3e33582836a97b7.

The GUI controller imports coretax_json only for validate_detail_source;
its other eager local dependencies do not require the tax adapter. Worker,
collector and resume already need the backend. The bounded benefit is removing
the unnecessary GUI-to-adapter import edge. This is not a startup timing,
memory, EXE-size or recovery-decoupling claim. A fresh runner process must prove
the baseline loads the adapter and that the candidate GUI imports with it blocked.

Use a small stdlib-only coretax_detail_source owner for the unchanged validator.
Keep exact type(value) is str, only literal dom/json-first, original return
object and exact ValueError text. Keep coretax_json.validate_detail_source as
an explicit same-object export. Only controller changes its import source;
its local name, App forwarding, all call sites and backend import paths remain.
Add the module to the explicit worker resource tuple; retain the other resources,
build identity, hash/cache validation and dependency locks.

Keeping the current owner avoids a file but retains that unnecessary dependency.
Moving filesystem/recovery/hash helpers together would broaden the contracts
without evidence of a benefit and is outside this change. Recovery still imports
coretax and output. No helper move grants capture, native, PDF, MPN, publication,
Stop/PARTIAL or live-acceptance permission.

Tests must show a genuine baseline failure when a fresh GUI process refuses tax
adapter/backend imports, preserve public binding identity and local controller
patch injection, reject coercible/subclass/nonliteral values, and preserve the
existing mode/GUI/backend behavior suites. Execution stays on GitHub runners.
Before merge require whole-branch review, exact-head full CI/artifact readback,
latest-main and preceding-other-session PR review, then reconcile issue134.
