import sys
from pathlib import Path

import flask


class Paths:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.pages = project_dir/'pages'
        self.assets = project_dir/'assets'
        self.templates = project_dir/'templates'
        self.config = project_dir/'config.py'
        self.build = project_dir/'_build'
        self.built_assets = self.build/'assets'
        if not self.pages.exists():
            print(f'{project_dir} is not a dnd_scribe project')
            sys.exit(-1)

def initialise(app: flask.Flask, project_dir: Path):
    app.config['dnd_scribe.notes.paths'] = Paths(project_dir)

def for_app(app: flask.Flask) -> Paths:
    return app.config['dnd_scribe.notes.paths']

def current() -> Paths:
    return for_app(flask.current_app)

def project_dir():
    return current().project_dir

def pages():
    return current().pages

def assets():
    return current().assets

def templates():
    return current().templates

def config():
    return current().config

def build():
    return current().build

def built_assets():
    return current().built_assets