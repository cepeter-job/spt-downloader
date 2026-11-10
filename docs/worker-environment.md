# Owned process environment policy

The packaged SPT Downloader GUI is the trusted owner of its isolated Python
worker and uv bootstrap commands. The parent shell or corporate desktop may
contain startup, preload, debugging or interpreter-selection settings unrelated
to those operations. Those settings must not be inherited by the authenticated
worker or its Playwright/Node driver.

## Entrypoints

- `spt_desktop.runtime.worker_environment()` constructs the environment for
  `spt_desktop.controller.JobController` to pass to the owned worker process.
- `spt_desktop.runtime.bootstrap_environment(root)` constructs the environment
  for owned uv invocations and managed Python probes. The same base allowlist
  is used for both, with additional **owned** uv storage/config keys.
- `spt_desktop.runtime._inherited_process_environment()` is the only point
  where parent environment variables are read for subprocess inheritance.
  The allowlist matches names case-insensitively on Windows while preserving
  the variable spellings/values (including lower-case proxy spellings).
- Do not copy `os.environ` or add a new direct inheritance path to a worker
  launcher, test helper, or build/bootstrap tool.

## Supported settings

The allowlist preserves the Windows system/shell search environment,
application/profile/temporary directory locations and the common
`PROGRAMFILES`/system variables. Supported proxy configuration:
`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, including their
lowercase variants. Corporate HTTPS/SOCKS proxy addresses may be preserved
exactly as supplied, including passwords embedded in URL values; such values
are never put in diagnostic events or printed to CI logs.

Supported custom CA/trust environment variables:
`SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`,
`CURL_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS`. The existing
`coretax_transport.system_ca_manager` sets the safe Windows
`NODE_USE_SYSTEM_CA=1` default around owned Playwright driver startup
rather than inheriting a potentially hostile external override. The uv-only
trust flags `UV_NATIVE_TLS` and `UV_SYSTEM_CERTS` are allowed for
bootstrap, not the application worker.

The launcher owns `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`,
`PYTHONNOUSERSITE=1`, and `PYTHONBREAKPOINT=0`. The uv bootstrap also
owns `UV_NO_CONFIG=1`, `UV_PYTHON_INSTALL_DIR`, and `UV_CACHE_DIR`.
No unreviewed parent setting may supersede these choices.

## Exclusions and security boundary

Environment keys not explicitly allowlisted are dropped. In particular,
`NODE_OPTIONS`, `NODE_PATH`, `NODE_DEBUG`,
`NODE_TLS_REJECT_UNAUTHORIZED`, `NODE_USE_SYSTEM_CA` (inherited),
`ELECTRON_RUN_AS_NODE`, `PWDEBUG`, `DEBUG`, `PLAYWRIGHT_*`,
`PYTHONPATH`, `PYTHONHOME`, `PYTHONINSPECT`, `PYTHONSTARTUP`,
`PYTHONWARNINGS`, `VIRTUAL_ENV`, untrusted `PIP_*` and unreviewed
`UV_*` overrides do not reach the worker or uv. The owned
`PYTHONBREAKPOINT=0` deliberately replaces any parent value.

This is **defense in depth**, not a sandbox or protection against an attacker
already controlling the parent process, the Windows account, DLL search
directories, source tree or trusted proxy/CA files. Adding a new inherited
variable requires a documented compatibility need and synthetic validation;
never broadly forward `NODE_*`, `PYTHON*`, `PLAYWRIGHT_*`, or `UV_*`.

## Verification

Portable tests inject malicious startup hooks and verify the exact allowlist
without starting a live Coretax session. Windows GUI tests inspect the
environment supplied to a synthetic owned `ProcessJob.spawn`. Existing
runtime bootstrap tests check pinned uv flags, proxy/CA forwarding, managed
Python setup and isolation from user uv configuration. Required Windows
integration CI and packaged worker startup remain acceptance gates.

Do not log environment dictionaries, proxy URLs, CA path values, or credentials
as a diagnostic shortcut. Record only fixed event names and bounded,
non-sensitive status fields.
