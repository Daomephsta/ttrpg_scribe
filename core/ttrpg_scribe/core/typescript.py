import atexit
import logging
import shutil
import subprocess
from pathlib import Path
from typing import overload

import flask
from werkzeug.exceptions import NotFound


def ensure_compiled(instance_dir: Path):
    (logs_dir := instance_dir/'logs').mkdir(parents=True, exist_ok=True)
    (build_dir := instance_dir/'_build').mkdir(parents=True, exist_ok=True)

    tsc = shutil.which('tsc')
    if tsc is None:
        npx = shutil.which('npx')
        if npx is None:
            logging.warning('npm not installed')
            return
        if subprocess.check_output(['npm', 'list', 'typescript', '--parseable']).strip() == '':
            logging.warning('Neither tsc or npx tsc installed')
            return
        else:
            tsc = ['npx', 'tsc']
    else:
        tsc = ['tsc']
    with (logs_dir/'tsc_watch.log').open('w') as tsc_watch_log:
        tsc = subprocess.Popen(
            [*tsc, '--watch', '--outDir', build_dir, '--pretty', 'false'],
            stdout=tsc_watch_log, stderr=subprocess.STDOUT
        )
        atexit.register(lambda: tsc.terminate())


@overload
def extend(scaffold: flask.Blueprint) -> flask.Blueprint:
    ...


@overload
def extend(scaffold: flask.Flask) -> flask.Flask:
    ...


def extend(scaffold: flask.Blueprint | flask.Flask):
    static_javascript_patch(scaffold)
    return scaffold


def static_javascript_patch(scaffold: flask.Blueprint | flask.Flask):
    if scaffold.static_folder is None:
        return

    assert __file__.endswith('core/ttrpg_scribe/core/typescript.py')
    root_project = Path(__file__.removesuffix('core/ttrpg_scribe/core/typescript.py'))
    root_relative = Path(scaffold.static_folder).relative_to(root_project)

    @scaffold.get('/static/<path:filename>.js')
    def static_javascript(filename: str):
        assert scaffold.static_folder is not None
        if not filename.endswith('.js'):
            filename = f'{filename}.js'
        if flask.current_app.debug:
            try:
                return flask.send_from_directory(
                    Path(flask.current_app.instance_path)/'_build'/root_relative,
                    filename
                )
            except NotFound:
                return flask.send_from_directory(scaffold.static_folder, filename)
        else:
            return flask.send_from_directory(scaffold.static_folder, filename)
