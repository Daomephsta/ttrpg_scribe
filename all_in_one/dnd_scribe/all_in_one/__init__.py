import logging
import shutil
from argparse import ArgumentParser
from http import HTTPStatus
from pathlib import Path

import waitress
from werkzeug.middleware.dispatcher import DispatcherMiddleware

import dnd_scribe.encounter.flask
import dnd_scribe.encounter.flask.extension
import dnd_scribe.notes
import dnd_scribe.npc.flask_app
import dnd_scribe.npc.flask_app.extension
from dnd_scribe.core import signals


def make_app(project_dir: str | Path):
    project_dir = Path(project_dir)
    app = dnd_scribe.notes.create_app(project_dir)
    dnd_scribe.encounter.flask.extension.extend(app, '/encounter_extension')
    dnd_scribe.npc.flask_app.extension.extend(app, '/npc_extension')
    app.config['TOOLS'] = [
        ('/encounter', 'Launch Encounter', {'method': 'post'}),
        ('/npc/gui', 'NPC Generator', {}),
        ('/clean', 'Clean _build', {'method': 'post'}),
    ]
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/encounter': dnd_scribe.encounter.flask.create_app(project_dir),
        '/npc': dnd_scribe.npc.flask_app.create_app(project_dir)
    })
    @app.post('/clean', endpoint = 'clean')
    def clean_endpoint():
        clean(project_dir)
        return '', HTTPStatus.NO_CONTENT
    return app

def start(args):
    app = make_app(args.project_dir)
    logging.basicConfig(level=logging.INFO,
                        format='%(name)s @ %(levelname)s: %(message)s')
    waitress.serve(app, listen='127.0.0.1:48164')

def clean(project_dir: Path):
    signals.send_clean()
    if (project_dir/'_build').exists():
        shutil.rmtree(project_dir/'_build')

def main():
    parser = ArgumentParser('dnd_scribe.all_in_one')
    parser.add_argument('project_dir', type=Path)
    subcommands = parser.add_subparsers()

    start_parser = subcommands.add_parser('start')
    start_parser.set_defaults(subcommand = start)

    clean_parser = subcommands.add_parser('clean')
    clean_parser.set_defaults(subcommand = lambda args: clean(args.project_dir))
    args = parser.parse_args()
    args.subcommand(args)
