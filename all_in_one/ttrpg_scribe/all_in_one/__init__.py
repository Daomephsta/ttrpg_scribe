import logging
from pathlib import Path

# Imports used by single functions are at the top of said functions for autocomplete speed reasons


def make_app(project_dir: str | Path):
    from http import HTTPStatus

    from werkzeug.middleware.dispatcher import DispatcherMiddleware

    import ttrpg_scribe.encounter.flask
    import ttrpg_scribe.encounter.flask.extension
    import ttrpg_scribe.notes
    import ttrpg_scribe.npc.flask_app
    import ttrpg_scribe.npc.flask_app.extension

    project_dir = Path(project_dir)
    app = ttrpg_scribe.notes.create_app(project_dir)
    ttrpg_scribe.encounter.flask.extension.extend(app, '/encounter_extension')
    ttrpg_scribe.npc.flask_app.extension.extend(app, '/npc_extension')
    app.config['TOOLS'] = [
        ('/encounter', 'Launch Encounter', {'method': 'post'}),
        ('/npc/gui', 'NPC Generator', {}),
        ('/clean', 'Clean _build', {'method': 'post'}),
    ]
    match app.config.get('SYSTEM'):
        case 'dnd_5e':
            from ttrpg_scribe.dnd_bestiary.flask import Dnd5eSystem
            system = Dnd5eSystem()
        case 'pf2e':
            from ttrpg_scribe.pf2e_compendium.flask import Pf2eSystem
            system = Pf2eSystem()
        case _ as system:
            raise ValueError(f'Unknown game system {system}')
    app.jinja_env.globals['system'] = system
    app.register_blueprint(system.bestiary_blueprint)
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/encounter': ttrpg_scribe.encounter.flask.create_app(project_dir, system),
        '/npc': ttrpg_scribe.npc.flask_app.create_app(project_dir)
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
        print(f'{project_dir.absolute()} is not a valid ttrpg_scribe project:')
        for issue in issues:
            print(f'\t{issue}')
        return False
    return True


def start(args):
    import waitress

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
    import shutil

    from ttrpg_scribe.core import signals

    if not check_structure(project_dir):
        return
    signals.send_clean()
    if (project_dir/'_build').exists():
        shutil.rmtree(project_dir/'_build')


def new(project_dir: Path, system: str):
    import importlib.resources
    import zipfile

    if not project_dir.exists():
        project_dir.mkdir()
    with importlib.resources.path('ttrpg_scribe.all_in_one.project_templates',
                                  f'{system}.zip') as template:
        if not template.exists():
            raise ValueError(f'No project template for {system} game system')
        with zipfile.ZipFile(template) as template:
            template.extractall(project_dir)


def main():
    from argparse import ArgumentParser

    import argcomplete

    parser = ArgumentParser('ttrpg_scribe')
    parser.add_argument('-p', '--project', type=Path, default=Path.cwd())
    parser.set_defaults(subcommand=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    start_parser = subcommands.add_parser('start')
    start_parser.add_argument('--debug', action='store_true')
    start_parser.set_defaults(subcommand=start)

    clean_parser = subcommands.add_parser('clean')
    clean_parser.set_defaults(subcommand=lambda args: clean(args.project))

    new_parser = subcommands.add_parser('new')
    new_parser.add_argument('--system')
    new_parser.set_defaults(subcommand=lambda args: new(args.project, args.system))

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    args.subcommand(args)
