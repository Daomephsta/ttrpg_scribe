import subprocess
from pathlib import Path

import flask

_pf2e_pack = None


def pf2e_pack_dir() -> Path:
    global _pf2e_pack
    if _pf2e_pack is not None:
        return _pf2e_pack
    root = Path(flask.current_app.instance_path)\
        if flask.current_app else Path.cwd()
    _pf2e_pack = (root/'_build/pf2e_foundry').absolute()
    if not _pf2e_pack.exists():
        subprocess.run([
            'git', 'clone', '--depth', '1',
            'https://github.com/foundryvtt/pf2e',
            _pf2e_pack.as_posix()])
    return _pf2e_pack


def pf2e_pack_open(path: str):
    return (pf2e_pack_dir()/path).open(encoding='utf8')
