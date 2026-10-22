"""Synthetic build reports helpers; no collected tests or shared mutable test state."""
from spt_desktop.runtime import WORKER_FILES, python_version


def report(profile='production'):
    return {'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
        'diagnostics': {'schema': 1, 'safe_logging': True},
        'bugreport_footer': {'text': 'bugreport : sharmila@kemenkeu.go.id', 'bottom_right': True},
        'automatic_login_controls': {'origin_selector_present': False,
            'credential_origin': 'satu', 'account_forwarded': True},
        'selection_sorting_control': sorting_report(),
            'python': python_version(profile), 'python_implementation': 'CPython',
            'free_threaded': False, 'tcl': '8.6.15', 'tk': '8.6.15',
            'worker_python': python_version(), 'worker_resources': list(WORKER_FILES),
            'credential_check_controls': False, 'gui_controls': ['Simpan', 'Hapus login', 'Tutup'],
            'personal_use_labels': ['Coretax → Excel · for personal use only'],
            'ui_text': {'title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
                        'background': 'jalankan proses sedot di background',
                        'results': 'Hasil Sedot berada di folder Downloads Windows'},
            'credentials_accessed': False, 'live_scrape': False}


def sorting_report():
    return {'heading': 'Jenis pajak', 'directions': ['Jenis pajak ▲', 'Jenis pajak ▼'],
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
