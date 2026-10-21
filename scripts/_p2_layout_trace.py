"""Read-only synthetic diagnosis of redundant Configure scheduling."""
import _tkinter
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--historical', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32'
    sys.path.insert(0, str(Path(args.source).resolve()))
    spec = importlib.util.spec_from_file_location('probe', Path(args.historical).resolve())
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    rows = []
    for kind in ('selection', 'overwrite'):
        with probe.session(probe.payload_for(kind, 3)) as (root, app, controller):
            events = []
            started = time.perf_counter_ns()
            def record(frame, event, arg):
                code = frame.f_code
                if event not in ('call', 'return') or code.co_name not in ('reflow', 'request_reflow'):
                    return
                if Path(code.co_filename).name != 'app.py' or not any(x in code.co_qualname for x in ('selection_dialog', 'overwrite_dialog')):
                    return
                values = frame.f_locals
                dialog, canvas = values.get('dialog'), values.get('canvas')
                if not dialog or not canvas:
                    return
                incoming = values.get('event')
                interaction = app._interaction
                events.append({'function': code.co_name, 'phase': event,
                    'ms': (time.perf_counter_ns() - started) / 1e6,
                    'layout_ready': values.get('layout_ready'),
                    'dialog_size': [dialog.winfo_width(), dialog.winfo_height()],
                    'canvas_size': [canvas.winfo_width(), canvas.winfo_height()],
                    'mapped': bool(canvas.winfo_ismapped()),
                    'incoming': None if incoming is None else {
                        'widget': 'dialog' if incoming.widget is dialog else 'canvas' if incoming.widget is canvas else 'other',
                        'width': str(getattr(incoming, 'width', '')), 'height': str(getattr(incoming, 'height', ''))},
                    'pending': interaction.get('layout_after') if interaction else None})
            try:
                sys.setprofile(record)
                app.on_event(probe.event(controller, kind))
                dialog = app._interaction['dialog']
                flags = _tkinter.WINDOW_EVENTS | _tkinter.IDLE_EVENTS | _tkinter.DONT_WAIT
                deadline, quiet = time.monotonic() + 2, 0
                while time.monotonic() < deadline:
                    pending = root.tk.dooneevent(flags)
                    root.update_idletasks()
                    viewport = probe.named(dialog, 'body_viewport')
                    if not pending and viewport.winfo_width() > 1 and viewport.winfo_ismapped():
                        quiet += 1
                        if quiet == 3:
                            break
                    else:
                        quiet = 0
                    time.sleep(.001)
            finally:
                sys.setprofile(None)
            rows.append({'kind': kind, 'events': events, 'owned_pending': app._interaction['layout_after'],
                         'final_canvas_size': [viewport.winfo_width(), viewport.winfo_height()],
                         'synthetic': True})
    path = Path(args.out);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print('Recorded native mapping and deferred-token transitions; no fix applied.')


if __name__ == '__main__':
    main()
