import logging
import sys
from pathlib import Path

# Imports used by single functions are at the top of said functions for autocomplete speed reasons


def make_app(project_dir: str | Path, config: Path | None = None):
    from http import HTTPStatus

    from werkzeug.middleware.dispatcher import DispatcherMiddleware

    import ttrpg_scribe.encounter.flask
    import ttrpg_scribe.encounter.flask.extension
    import ttrpg_scribe.notes
    import ttrpg_scribe.npc.flask_app
    import ttrpg_scribe.npc.flask_app.extension

    project_dir = Path(project_dir)
    app = ttrpg_scribe.notes.create_app(config or Path('config.py'), project_dir)
    ttrpg_scribe.encounter.flask.extension.extend(app, '/encounter_extension')
    ttrpg_scribe.npc.flask_app.extension.extend(app, '/npc_extension')
    app.config['TOOLS'] = [
        ('/encounter', 'Launch Encounter', {'method': 'post'}),
        ('/encounter/party/configure', 'Configure Party', {}),
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
            app.config['TOOLS'].insert(-1, ('/compendium', 'Compendium', {}))
        case _ as system:
            raise ValueError(f'Unknown game system {system}')
    app.jinja_env.globals['system'] = system
    app.register_blueprint(system.compendium_blueprint)
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/encounter': ttrpg_scribe.encounter.flask.create_app(project_dir, system, app.config),
        '/npc': ttrpg_scribe.npc.flask_app.create_app(project_dir, app.config)
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
        if not (project_dir/'config.py').exists() and not (project_dir/'config').exists():
            issues.append(f'Neither {project_dir.absolute()}/config.py '
                          f'nor {project_dir.absolute()}/config exist')
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
    config_dir: Path = args.project/'config'
    if config_dir.exists():
        if args.config:
            app = make_app(args.project, config_dir/f'{args.config}.py')
        else:
            print('Multiconfig projects must specify --config', file=sys.stderr)
            print(f'Available configs: {', '.join(path.stem for path in config_dir.glob('*.py'))}',
                  file=sys.stderr)
            return
    else:
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
    import shutil

    try:
        with importlib.resources.as_file(importlib.resources.files(
                f'ttrpg_scribe.all_in_one.project_templates.{system}')) as template:
            shutil.copytree(template, project_dir, dirs_exist_ok=project_dir == Path.cwd())
    except ModuleNotFoundError:
        raise ValueError(f'No project template for {system} game system') from None


def pf2e_foundry(args):
    from ttrpg_scribe.pf2e_compendium import foundry
    match args.foundry_command:
        case 'update':
            foundry.update()
        case 'dir':
            print(foundry.pf2e_dir().as_posix())


def main():
    from argparse import ArgumentParser

    import argcomplete

    parser = ArgumentParser('ttrpg_scribe')
    parser.add_argument('-p', '--project', type=Path, default=Path.cwd())
    parser.set_defaults(subcommand=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    start_parser = subcommands.add_parser('start')
    start_parser.add_argument('--debug', action='store_true')
    start_parser.add_argument('-c', '--config', type=str)
    start_parser.set_defaults(subcommand=start)

    clean_parser = subcommands.add_parser('clean')
    clean_parser.set_defaults(subcommand=lambda args: clean(args.project))

    new_parser = subcommands.add_parser('new')
    new_parser.add_argument('--system')
    new_parser.set_defaults(subcommand=lambda args: new(args.project, args.system))

    foundry_parser = subcommands.add_parser('pf2e_foundry')
    foundry_parser.add_argument('foundry_command', choices=['dir', 'update'])
    foundry_parser.set_defaults(subcommand=pf2e_foundry)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    args.subcommand(args)
