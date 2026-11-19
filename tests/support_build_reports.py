"""Synthetic build reports helpers; no collected tests or shared mutable test state."""
from spt_desktop.runtime import WORKER_FILES, python_version
from spt_desktop.ui_copy import copy_text


def report(profile='production'):
    return {'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
        'diagnostics': {'schema': 1, 'safe_logging': True},
        'bugreport_footer': {'text': copy_text('app.bugreport'), 'bottom_right': True},
        'automatic_login_controls': {'origin_selector_present': False,
            'credential_origin': 'satu', 'account_forwarded': True},
        'selection_sorting_control': sorting_report(),
            'python': python_version(profile), 'python_implementation': 'CPython',
            'free_threaded': False, 'tcl': '8.6.15', 'tk': '8.6.15',
            'worker_python': python_version(), 'worker_resources': list(WORKER_FILES),
            'credential_check_controls': False, 'gui_controls': [copy_text('settings.widget.simpan'), copy_text('settings.delete'),
                             copy_text('settings.widget.tutup')],
            'personal_use_labels': [copy_text('app.subtitle')],
            'ui_text': {'title': copy_text('app.title'),
                        'background': copy_text('settings.background.label'),
                        'results': copy_text('results.location_hint')},
            'credentials_accessed': False, 'live_scrape': False}


def sorting_report():
    return {'heading': 'Jenis pajak', 'directions': [copy_text('selection.table.type') + ' ▲',
                                             copy_text('selection.table.type') + ' ▼'],
            'hierarchy': ['type', 'year', 'month', 'model'],
            'default_ordered_ids': [
                'synthetic-badan-two', 'synthetic-badan-one', 'synthetic-21', 'synthetic-unifikasi',
                'synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
                '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb'],
            'ordered_ids': [
                ['synthetic-badan-two', 'synthetic-badan-one', 'synthetic-21', 'synthetic-unifikasi',
                 'synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
                 '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb'],
                ['synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
                 '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb',
                 'synthetic-unifikasi', 'synthetic-21', 'synthetic-badan-two', 'synthetic-badan-one']],
            'selection_preserved': True,
            'confirmed_ids': ['::synthetic {return}; [literal] / id', 'synthetic-badan-two']}
