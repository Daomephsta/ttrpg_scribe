import importlib.resources
import logging
import shutil
import zipfile
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

    @app.post('/clean', endpoint='clean')
    def clean_endpoint():
        clean(project_dir)
        return '', HTTPStatus.NO_CONTENT
    return app


def check_structure(project_dir: Path) -> bool:
    issues = []
    if not project_dir.exists():
        issues.append('Does not exist')
    else:
        if not (project_dir/'pages').exists():
            issues.append(f'{project_dir.absolute()}/pages does not exist')
        if not (project_dir/'config.py').exists():
            issues.append(f'{project_dir.absolute()}/config.py does not exist')
    if issues:
        print(f'{project_dir.absolute()} is not a valid dnd_scribe project:')
        for issue in issues:
            print(f'\t{issue}')
        return False
    return True


def start(args):
    if not check_structure(args.project):
        return
    app = make_app(args.project)
    logging.basicConfig(level=logging.INFO,
                        format='%(name)s @ %(levelname)s: %(message)s')
    host, port = '127.0.0.1', 48164
    if args.debug:
        app.jinja_env.auto_reload = True
        app.run(host, port, debug=True)
    else:
        waitress.serve(app, listen=f'{host}:{port}')


def clean(project_dir: Path):
    if not check_structure(project_dir):
        return
    signals.send_clean()
    if (project_dir/'_build').exists():
        shutil.rmtree(project_dir/'_build')


def new(project_dir: Path):
    if not project_dir.exists():
        project_dir.mkdir()
    with importlib.resources.path('dnd_scribe.all_in_one',
                                  'project_template.zip') as template:
        with zipfile.ZipFile(template) as template:
            template.extractall(project_dir)


def main():
    parser = ArgumentParser('dnd_scribe.all_in_one')
    parser.add_argument('-p', '--project', type=Path, default=Path.cwd())
    parser.set_defaults(subcommand=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    start_parser = subcommands.add_parser('start')
    start_parser.add_argument('--debug', action='store_true')
    start_parser.set_defaults(subcommand=start)

    clean_parser = subcommands.add_parser('clean')
    clean_parser.set_defaults(subcommand=lambda args: clean(args.project))

    new_parser = subcommands.add_parser('new')
    new_parser.set_defaults(subcommand=lambda args: new(args.project))

    args = parser.parse_args()
    args.subcommand(args)
