# Native Windows trust for the owned Playwright driver

Status: implementation choice under the operator's instruction to fix the latest
live failures. No new catalog endpoint, GET allowance, proxy or TLS bypass.
Base main: 97f5784d988724420a9e744599c43e04d76ad2ca.

## Evidence and choice

The latest build reaches the correct original unfiltered MPN list, then raises
the fixed acquisition transport refusal before accepting a catalog. The old
log cannot identify the original transport error. Independent handshake-only
diagnostics on the operator machine establish a trust-path difference:

- Windows SslStream validation succeeds.
- Standard Node TLS fails with UNABLE_TO_VERIFY_LEAF_SIGNATURE.
- The same Node handshake with its system-CA option succeeds.
- Zero HTTP requests, no credentials, no certificate installation or TLS
  verification bypass were used in these diagnostics.

The installed pinned Playwright driver executable reports Node 24.22.1 by PE
version metadata. Node supports NODE_USE_SYSTEM_CA=1 from 24.6.0/22.19.0; its
official documentation states that this adds the existing trusted system CAs
alongside bundled and explicitly configured extra CAs:
https://nodejs.org/api/cli.html#node_use_system_ca1

Use that supported option only while starting a new owned driver on Windows.
Keep the existing context.request.get and all approved source/context/Document/
scope/endpoint/deadline/size/redirect/retry/custody gates. This is narrower than
replacing acquisition with browser fetch and adding new Request attribution.
Do not export certificates, import real roots, modify OS trust, disable TLS,
change proxies, read cache/credentials, or add a request/retry.

## Implementation boundary

Add a stdlib-only coretax_transport owner exposing system_ca_manager(manager).
It wraps only the context-manager entry: under an RLock, temporarily default
NODE_USE_SYSTEM_CA to 1 on Windows if the variable is absent, call the original
manager.__enter__, and restore the owned default on success/error/Stop. Preserve
all pre-existing explicit values and changes to a different value. A write of
the same temporary value during entry cannot be distinguished and is restored
as part of the owned default. Forward __exit__ arguments and result
unchanged. Nested/concurrent starts must not inherit a disappearing default.

CLI still calls its local sync_playwright and registers contained __exit__
before __enter__, preserving partially acquired transport cleanup. Desktop
still calls its local playwright_factory. Register the new module in the
explicit worker allowlist and verify frozen/managed resources. GUI import
boundaries and all existing patch namespaces remain intact.

## Verification

First observe runner RED for startup environment and both entrypoints. A real
Windows-runner HTTPS fixture temporarily trusts only a generated synthetic
certificate, compares a fresh driver with default trust against the wrapped
driver, and confirms hostname mismatch still fails. It owns and removes its
exact temporary certificate entries and never exports private material as an
artifact. All product imports/tests/builds remain GitHub-runner-only.

Review the whole branch, refresh latest main/preceding other-session merges,
require exact-head CI, merge, and verify/deliver the exact main package.
Handshake evidence is not build-matched full MPN acceptance. L3-B remains an
independent repair requiring live overlay/dispatch evidence; do not increase
its caps/deadline or remove readiness checks speculatively.
