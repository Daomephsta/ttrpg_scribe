import atexit
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import overload

import flask
from werkzeug.exceptions import NotFound

_IS_DEV = 'site-packages' not in __file__


def ensure_compiled(instance_dir: Path):
    if not _IS_DEV:
        return
    (logs_dir := instance_dir/'logs').mkdir(parents=True, exist_ok=True)
    (build_dir := instance_dir/'_build').mkdir(parents=True, exist_ok=True)

    rollup = shutil.which('rollup')
    if rollup is None:
        logging.warning('rollup not installed')
        return
    subprojects = Path('/home/david/TTRPGs/ttrpg_scribe/subprojects')
    for subproject in subprojects.iterdir():
        if not (subproject/'rollup.config.mjs').exists():
            continue
        watch_log = (logs_dir/f'rollup_watch_{subproject.name}.log').open('w')
        watcher = subprocess.Popen(
            [
                rollup, '-c', '--dir', build_dir/subproject.name,
                '--watch', '--no-watch.clearScreen'
            ],
            cwd=subproject,
            stdout=watch_log, stderr=subprocess.STDOUT,
            env={**os.environ, 'NO_COLOR': '1'}
        )
        atexit.register(lambda: watcher.terminate())


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
    if not _IS_DEV or scaffold.static_folder is None:
        return

    @scaffold.get('/static/<path:filename>.js')
    def static_javascript(filename: str):
        assert scaffold.static_folder is not None
        if not filename.endswith('.js'):
            filename = f'{filename}.js'
        reload = flask.current_app.debug and 'site-packages' not in __file__
        if reload:
            assert __file__.endswith('core/ttrpg_scribe/core/typescript.py'), __file__
            root_project = Path(__file__.removesuffix('core/ttrpg_scribe/core/typescript.py'))
            root_relative = Path(scaffold.static_folder).relative_to(root_project)
            try:
                return flask.send_from_directory(
                    Path(flask.current_app.instance_path)/'_build'/root_relative,
                    filename
                )
            except NotFound:
                return flask.send_from_directory(scaffold.static_folder, filename)
        else:
            return flask.send_from_directory(scaffold.static_folder, filename)
