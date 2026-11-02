# Literal mode dependency assessment (#134)

Baseline: main39c7de577d74a45092127ab0d3e33582836a97b7. Its completed
main run41333816255 and artifact readback are recorded in issue134 separately
from PR166 evidence. This assessment authorizes no new capture or publication.

## Observed benefit and decision

The controller's only coretax_json import is validate_detail_source. Its eager
GUI dependency path does not otherwise require the adapter. The adapter itself
uses stdlib at import time; corporate projectors are imported inside adapters.
Removing this edge does not remove a proven eager Playwright/openpyxl/projector
load, and no startup time, memory or frozen-size improvement is claimed.

The fresh-process Windows Python3.14.8 baseline probe
[41364082282](https://github.com/cepeter-job/spt-downloader/actions/runs/41364082282),
attempt1, observed coretax_json loaded after importing App, with coretax_browser,
Playwright and openpyxl absent. Probe b61c8d803fb0975ca8b9e96c6de16cba7931c2a7
contains the unchanged main production bytes plus tests/design/isolated workflow.
Original artifact13106541741 SHA256
`a86ef093d97fa69928698cbfe4940ba25428fb0e16b0699a174f5e4be81d18d4`
was downloaded/read back:40passes and exactly one intended failure, the fresh
GUI import refusal for coretax_json; no errors/skips. The actual new boundary
test blocks backend imports before loading the GUI, rather than inspecting text.

Decision: use coretax_detail_source as a tiny common owner and switch only the
controller's import source. Keep the exact validator body and original public
coretax_json export. This removes a concrete unnecessary GUI-to-adapter dependency
without moving backend guards. Final GREEN/head/tree/artifact evidence belongs
in the PR and issue; baseline RED evidence above remains an immutable snapshot.

## Consumer and patch namespace audit

| Consumer | Local binding / behavior retained | Decision |
| --- | --- | --- |
| coretax_json | validate_detail_source public name | Same-object explicit export from common owner |
| controller.JobController.start | controller.validate_detail_source before scope/spawn | Change import source only; real local-patch refusal test prevents worker launch |
| app.load_preferences/save_preferences | App module's imported validator; old defaults and saved-file refusal | Existing forwarding and mode tests unchanged |
| worker.run_job | worker.validate_detail_source before job/browser setup | Keep original import and call site; shared-object test |
| coretax_resume._selected/persist_selection/load_resume_inventory | coretax_resume.validate_detail_source before selection/checkpoint use | Keep original namespace and mode/identity gates |
| browser.read_detail_checkpoint/collect_details | coretax_browser.validate_detail_source before reuse/detail capture | Keep original namespace and literal mode gates |

All production references and repository patch strings were searched. Existing
tests do not patch the legacy coretax_json validator. The changed controller
binding is exercised through its own namespace; backend/App bindings remain
where their callers look them up. No promise is made that patching a source
module after a from-import changes another module's already bound alias.
Public identity, return identity, exact ValueError text, invalid literals,
non-strings and coercion/string-subclass tripwires run alongside existing mode
tests. No existing assertions or fixture imports are removed.

## Resource and remaining-work boundaries

Append only the new owner to the explicit WORKER_FILES tuple; retain every prior
resource in order. Existing fingerprints, managed setup, frozen source and
bootstrap checks must include it. Dependencies, coverage policy and CI workflow
are unchanged; the isolated probe workflow never enters the product PR.

Publication recovery still imports coretax and output. Moving filesystem
primitives requires a separate design for DirectoryGuard, reparse/case rejection,
fsync, atomic replace, owned-temp cleanup, interrupts and actual caller patch
injection. Hash readers retain different script-provider/initiator and size
policies. Neither refactor is implemented or certified by the mode owner change.
