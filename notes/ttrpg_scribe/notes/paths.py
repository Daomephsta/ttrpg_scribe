from functools import cache
from pathlib import Path

import flask


@cache
def project_dir():
    return Path(flask.current_app.instance_path)


@cache
def pages():
    return project_dir()/'pages'


@cache
def assets():
    return project_dir()/'assets'


@cache
def templates():
    return project_dir()/'templates'


@cache
def config():
    return project_dir()/'config.py'


@cache
def build():
    return project_dir()/'_build'


@cache
def built_assets():
    return build()/'assets'
