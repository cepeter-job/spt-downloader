"""Temporary instrumented profile; not the uninstrumented performance benchmark."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--historical', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32'
    source = Path(args.source).resolve()
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == args.revision
    sys.path.insert(0, str(source))
    spec = importlib.util.spec_from_file_location('historical_probe', Path(args.historical).resolve())
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    results = []
    for kind, count in [('selection', 1), ('selection', 1000), ('overwrite', 101)]:
        with probe.session(probe.payload_for(kind, count)) as (root, app, controller):
            events = []
            start = time.perf_counter_ns()
            original = app._new_interaction
            binding = None
            def created(key, title):
                nonlocal binding
                interaction = original(key, title)
                dialog = interaction['dialog']
                def exposed(event):
                    if event.widget is dialog:
                        events.append({'event': 'native_expose', 'ms': (time.perf_counter_ns() - start) / 1e6})
                binding = dialog.bind('<Expose>', exposed, add='+')
                return interaction
            app._new_interaction = created
            watched = {'selection_dialog', 'overwrite_dialog', 'configure_dialog', 'request_reflow',
                       'reflow', 'update_scrollregion', 'filter_records'}
            def profile(frame, event, arg):
                if event not in ('call', 'return') or frame.f_code.co_name not in watched:
                    return
                filename = Path(frame.f_code.co_filename)
                if filename.name not in ('app.py', 'ui_theme.py'):
                    return
                qualname = frame.f_code.co_qualname
                if filename.name == 'app.py' and not any(name in qualname for name in ('selection_dialog', 'overwrite_dialog')):
                    return
                row = {'event': event, 'function': qualname, 'ms': (time.perf_counter_ns() - start) / 1e6}
                if frame.f_code.co_name == 'request_reflow':
                    row['content_request'] = frame.f_locals.get('event') is None
                if event == 'return' and app._interaction:
                    row['owned_layout_pending'] = app._interaction.get('layout_after') is not None
                events.append(row)
            try:
                sys.setprofile(profile)
                app.on_event(probe.event(controller, kind))
                handler = (time.perf_counter_ns() - start) / 1e6
                stable = probe.settle(root, app, start)
            finally:
                sys.setprofile(None)
                app._new_interaction = original
            dialog = app._interaction['dialog']
            if binding:
                dialog.unbind('<Expose>', binding)
            results.append({'dialog': kind, 'inventory_size': count,
                'instrumented_handler_ms': handler, 'instrumented_settled_ms': stable,
                'events': events, 'environment': probe.environment(root, dialog, actual)})
    output = {'source_revision': actual, 'synthetic': True, 'portal_accessed': False,
        'instrumented': True, 'timings_are_not_primary_benchmark': True,
        'visibility_measure': 'first observed native Expose event, not compositor first-pixel timing',
        'results': results}
    path = Path(args.out); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps([{k: r[k] for k in ('dialog', 'inventory_size', 'instrumented_handler_ms', 'instrumented_settled_ms')} for r in results]))


if __name__ == '__main__':
    main()
