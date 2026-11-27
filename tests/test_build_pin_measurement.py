"""The build-pin re-measurement must read the assets the portal actually serves.

The reviewed MAIN chunk is above 4 MiB (see coretax_corporate._MEASURE_MAIN_PIN_JS
and tests/l7_observer_fixture.py), so a 4 MiB guard would refuse the one asset a
redeploy changes. These tests serve real over-4-MiB bodies from a local server
and measure them with the shipped scripts.
"""
import functools
import http.server
import threading

import pytest

from support_isolated_browser import browser as browser, isolated_context


SMALL = b'/* synthetic small chunk */'
# Above 4 MiB and below the 5 MiB reader bound, like the live MAIN bundle.
BIG = b'/* synthetic main chunk */' + b'x' * (4 * 1024 * 1024 + 512 * 1024)


@pytest.fixture
def origin(tmp_path):
    """A local origin serving one small and one over-4-MiB script."""
    serve = tmp_path / 'www'
    serve.mkdir()
    (serve / 'small.js').write_bytes(SMALL)
    (serve / 'main.js').write_bytes(BIG)
    # A retired chunk name serves the SPA shell: 2xx, but text/html.
    (serve / 'shell').write_bytes(b'<!doctype html><title>shell</title>')
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(serve))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d' % httpd.server_address[1]
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def test_small_asset_measures_with_the_default_reader(origin, browser):
    import coretax_corporate

    with isolated_context(browser) as context:
        page = context.new_page()
        page.goto(origin + '/small.js')
        digest = page.evaluate(coretax_corporate._MEASURE_PIN_JS, origin + '/small.js')
    assert isinstance(digest, str) and len(digest) == 64


def test_over_four_mib_asset_needs_the_main_reader(origin, browser):
    """The 4 MiB guard refuses the MAIN-sized body; the 5 MiB reader accepts it."""
    import coretax_corporate

    with isolated_context(browser) as context:
        page = context.new_page()
        page.goto(origin + '/small.js')
        refused = page.evaluate(coretax_corporate._MEASURE_PIN_JS, origin + '/main.js')
        measured = page.evaluate(coretax_corporate._MEASURE_MAIN_PIN_JS,
                                 origin + '/main.js')
    assert refused == 'too_large', 'the default reader must keep its 4 MiB bound'
    assert isinstance(measured, str) and len(measured) == 64


def test_retired_chunk_name_is_named_fallback_html(origin, browser):
    """A 2xx non-JS body is the retired-chunk shell, and must say so.

    This is the live 27 Nov case: the portal rolled new chunk names, so the
    pinned URL serves the SPA shell instead of a script.
    """
    import coretax_corporate

    with isolated_context(browser) as context:
        page = context.new_page()
        page.goto(origin + '/small.js')
        state = page.evaluate(coretax_corporate._MEASURE_PIN_JS, origin + '/shell')
    assert state == 'fallback_html'


def test_absent_asset_is_named_missing(origin, browser):
    """A non-2xx asset is 'missing', distinct from the retired-chunk shell."""
    import coretax_corporate

    with isolated_context(browser) as context:
        page = context.new_page()
        page.goto(origin + '/small.js')
        state = page.evaluate(coretax_corporate._MEASURE_PIN_JS, origin + '/absent.js')
    assert state == 'missing'