"""Shared test isolation.

The build-pin overlay lives under ``%LOCALAPPDATA%`` so a redeploy can
self-heal without a release. Tests must never touch the real profile: a
stray overlay there changes ``load_build_pins()``, and several modules read
it at *import* time into module-level constants (``CIT_SOURCE_SHA256``,
``BUILD_DIGESTS``, ``POST_SOURCE_PINS`` ...). A per-test fixture is too late
for those, so the profile is redirected once, at conftest import, before any
test module is imported.
"""
import atexit
import os
import shutil
import tempfile

_ISOLATED = tempfile.mkdtemp(prefix='spt-test-localappdata-')
os.environ['LOCALAPPDATA'] = _ISOLATED
atexit.register(shutil.rmtree, _ISOLATED, ignore_errors=True)