"""Isolate semantic binding at original reference coordinates.

These helpers suppress only final presentation so legacy binding/style tests
retain stable coordinates. test_masa_compact_export tests the actual saved
exporter without these helpers; no production option or CI selector is changed.
"""
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def reference_geometry():
    with patch('coretax_pph21._compact_layout'), patch('coretax_masa_templates._compact_layout'):
        yield


def render_pph21_binding(*args, **kwargs):
    from coretax_pph21 import render_template_form
    with reference_geometry():
        return render_template_form(*args, **kwargs)
