"""Temporary paired native evidence; exact commits, synthetic controllers only."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

BASELINE = 'df8e7589fe6550d639142971483c65beef4b37d9'
CANDIDATE = 'd59a019c9c7cfc24af617ace824c69d7ede58d53'


def revision(path):
    return subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def load_probe(path):
    spec = importlib.util.spec_from_file_location('historical_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile(args):
    source = Path(args.source).resolve()
    assert revision(source) == args.revision
    sys.path.insert(0, str(source))
    probe = load_probe(Path(args.historical).resolve())
    rows = []
    for kind, count in [('selection', 1), ('selection', 1000), ('overwrite', 101)]:
        with probe.session(probe.payload_for(kind, count)) as (root, app, controller):
            observations, timings, calls, layout_events = {}, [], {}, []
            original = app._new_interaction
            started = time.perf_counter_ns()
            def instrumented_new(*values, **keywords):
                interaction = original(*values, **keywords)
                dialog = interaction['dialog']
                for sequence, name in [('<Map>', 'first_native_map_ms'), ('<Expose>', 'first_native_expose_ms')]:
                    def observed(event, label=name):
                        if event.widget is dialog and label not in observations:
                            observations[label] = (time.perf_counter_ns() - started) / 1e6
                    dialog.bind(sequence, observed, add='+')
                return interaction
            app._new_interaction = instrumented_new
            def trace(frame, event, arg):
                code = frame.f_code
                if (code.co_name not in ('reflow', 'request_reflow', 'update_scrollregion')
                        or not code.co_filename.endswith('app.py')
                        or not any(x in code.co_qualname for x in ('selection_dialog', 'overwrite_dialog'))):
                    return
                if event in ('call', 'return') and code.co_name in ('reflow', 'request_reflow'):
                    values = frame.f_locals
                    interaction = app._interaction
                    canvas = values.get('canvas')
                    dialog = interaction.get('dialog') if interaction else None
                    if canvas is not None and dialog is not None:
                        incoming = values.get('event')
                        token = interaction.get('layout_after')
                        token_kind = str(root.tk.call('after', 'info', token)[-1]) if token else None
                        layout_events.append({'function':code.co_name,'phase':event,
                            'ms':(time.perf_counter_ns()-started)/1e6,
                            'canvas':[canvas.winfo_width(),canvas.winfo_height()],
                            'dialog':[dialog.winfo_width(),dialog.winfo_height()],
                            'mapped':bool(canvas.winfo_ismapped()),
                            'layout_size':values.get('layout_size'),
                            'token':token,'token_kind':token_kind,
                            'incoming':None if incoming is None else {
                                'widget':'dialog' if incoming.widget is dialog else 'canvas' if incoming.widget is canvas else 'other',
                                'width':str(getattr(incoming,'width','')), 'height':str(getattr(incoming,'height',''))}})
                if event == 'call':
                    calls[id(frame)] = time.perf_counter_ns()
                elif event == 'return':
                    start = calls.pop(id(frame), None)
                    if start is not None:
                        timings.append({'function': code.co_name,
                            'duration_ms': (time.perf_counter_ns() - start) / 1e6})
            try:
                sys.setprofile(trace)
                app.on_event(probe.event(controller, kind))
                handler_ms = (time.perf_counter_ns() - started) / 1e6
                settled_ms = probe.settle(root, app, started)
            finally:
                sys.setprofile(None)
                app._new_interaction = original
            rows.append({'revision': args.revision, 'dialog': kind, 'inventory_size': count,
                'instrumented': True, 'not_primary_benchmark': True,
                'map_and_expose_are_observed_events_not_photon_latency': True,
                'handler_ms': handler_ms, 'settled_ms': max(handler_ms, settled_ms),
                'callback_counts': dict(collections.Counter(t['function'] for t in timings)),
                'callbacks': timings, 'layout_events': layout_events, **observations,
                'environment': probe.environment(root, app._interaction['dialog'], args.revision)})
    out = Path(args.out);out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding='utf-8')


def compare(args):
    historical = Path(args.historical).resolve()
    baseline, candidate = Path(args.baseline).resolve(), Path(args.candidate).resolve()
    assert revision(baseline) == BASELINE and revision(candidate) == CANDIDATE
    out = Path(args.out).resolve();out.mkdir(parents=True, exist_ok=True)
    probe = load_probe(historical)
    # Only source identities change; retain the original timing/settlement method.
    probe.BASELINE, probe.CANDIDATE = BASELINE, CANDIDATE
    probe.orchestrate(argparse.Namespace(baseline=str(baseline), candidate=str(candidate), out=str(out)))
    for label, source, sha in [('baseline', baseline, BASELINE), ('candidate', candidate, CANDIDATE)]:
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--profile', '--source', str(source),
            '--revision', sha, '--historical', str(historical), '--out', str(out / f'{label}-instrumented.json')],
            cwd=source, check=True, timeout=180)
    pairing = []
    for folder in sorted(out.glob('baseline-*')):
        if not folder.is_dir() or not (folder / 'evidence.json').exists():
            continue
        left = json.loads((folder / 'evidence.json').read_text(encoding='utf-8'))
        right = json.loads((out / folder.name.replace('baseline-', 'candidate-') / 'evidence.json').read_text(encoding='utf-8'))
        assert left['revision'] == BASELINE and right['revision'] == CANDIDATE
        assert len(left['timings']) == len(right['timings']) == 10
        for before, after in zip(left['timings'], right['timings']):
            for key in ('dialog', 'inventory_size', 'operation', 'payload_sha256'):
                assert before[key] == after[key], key
            assert len(before['samples_ms']) == len(after['samples_ms']) == 10
            pairing.append({'dialog': before['dialog'], 'inventory_size': before['inventory_size'],
                'operation': before['operation'], 'baseline_median_ms': before['median_ms'],
                'candidate_median_ms': after['median_ms'], 'candidate_p95_ms': after['p95_ms'],
                'candidate_cancel_max_ms': max(after['cancel_service_ms'])})
    assert len(pairing) == 10
    (out / 'paired-summary.json').write_text(json.dumps({'baseline': BASELINE, 'candidate': CANDIDATE,
        'historical_probe_sha256': hashlib.sha256(historical.read_bytes()).hexdigest(),
        'timing_method_unchanged': True, 'synthetic_only': True, 'pairs': pairing}, indent=2), encoding='utf-8')
    print(json.dumps(pairing), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline')
    parser.add_argument('--candidate')
    parser.add_argument('--historical', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--source')
    parser.add_argument('--revision')
    args = parser.parse_args()
    assert sys.platform == 'win32', 'Product execution is GitHub Windows runner only'
    profile(args) if args.profile else compare(args)


if __name__ == '__main__':
    main()
