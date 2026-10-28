# MPN ownership refusal diagnosis

The latest saved live job used PR126 and failed at `_source_finished`'s
completion-time ownership guard before response/body access. The saved event
does not distinguish its six predicates. The read-only IAB observation of the
same ledger supplied one main-frame document, same-route router notification,
and GET script requests for both providers. It did not reproduce the product
worker failure or establish which predicate failed. Do not claim a live fix.

Preserve the ownership predicates, their evaluation order, request admission,
sticky refusals, first-error semantics and all body/source/completion gates.
Add only a fixed diagnostic reason for the first false ownership predicate:
navigation, frame, method, page_route, request_url or resource_kind. Never log
the compared values, identifiers, request material or arbitrary exception text.
Non-ownership refusals must not acquire a misleading ownership reason.

All product imports/tests/builds run on GitHub runners. Reuse the existing
managed worktree, preserve private captures, and deliver a verified diagnostic
package for a new authorized live run. Root-cause repair remains pending that
evidence; no speculative relaxation or missing-inventory COMPLETE is allowed.
