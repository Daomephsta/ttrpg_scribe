import json
import shutil
import subprocess
from pathlib import Path

import platformdirs

VERSION = '6.3.0'
_pf2e_dir = (platformdirs.user_data_path('ttrpg_scribe') /
                'pf2e_compendium/data/foundryvtt/pf2e').absolute()


def pf2e_dir() -> Path:
    return _get_or_create_pf2e_dir()


def _get_or_create_pf2e_dir():
    if not _pf2e_dir.exists():
        subprocess.run([
            'git', 'clone',
            '--depth', '1',
            '--branch', VERSION,
            'https://github.com/foundryvtt/pf2e',
            _pf2e_dir.as_posix()])
    return _pf2e_dir


def open_pf2e_file(path: str):
    return (pf2e_dir()/path).open(encoding='utf8')


def update():
    if _pf2e_dir.exists():
        package_data = json.loads((_pf2e_dir/'package.json').read_text())
        if package_data['version'] == VERSION:
            print(f'PF2e system already compatible ({VERSION})')
            return
        else:
            print(f'Replacing {package_data['version']} with {VERSION}')
            shutil.rmtree(_pf2e_dir)
    _get_or_create_pf2e_dir()
