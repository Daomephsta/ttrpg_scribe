import importlib
import logging
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path
from typing import Callable

_LOGGER = logging.getLogger(__name__)
# Imports used by single functions are at the top of said functions for autocomplete speed reasons


def make_app(project_dir: str | Path, debug: bool | None = None):
    from http import HTTPStatus

    from werkzeug.middleware.dispatcher import DispatcherMiddleware

    import ttrpg_scribe.core.typescript
    import ttrpg_scribe.notes
    from ttrpg_scribe.core.plugin import Plugin

    project_dir = Path(project_dir)
    app = ttrpg_scribe.notes.create_app(project_dir)
    if debug is not None:
        app.debug = debug
    app.jinja_options.update(
        lstrip_blocks=True,
        trim_blocks=True
    )

    PLUGIN_FACTORIES: dict[str, tuple[str, str]] = {
        'dnd_5e': ('ttrpg_scribe.dnd_bestiary.flask', 'Dnd5ePlugin'),
        'pf2e': ('ttrpg_scribe.pf2e_compendium.flask', 'Pf2ePlugin'),
        'encounter': ('ttrpg_scribe.encounter.flask.plugin', 'EncounterPlugin'),
        'npc': ('ttrpg_scribe.npc.flask_app.plugin', 'NpcPlugin'),
    }

    def create_plugin(plugin_id: str) -> type[Plugin]:
        package, type = PLUGIN_FACTORIES[plugin_id]
        module = importlib.import_module(package)
        return getattr(module, type)

    active_plugins: list[tuple[str, type[Plugin]]] = [(id, create_plugin(id))
                                                      for id in app.config['PLUGINS']]

    plugin_apps = {}
    for _, plugin in active_plugins:
        plugin.configure(app)
    for id, plugin in active_plugins:
        plugin_app = plugin.create_app(project_dir, app.config)
        if plugin_app is not None:
            plugin_apps[f'/{id}'] = plugin_app
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, plugin_apps)

    if app.debug:
        ttrpg_scribe.core.typescript.ensure_compiled(Path(app.instance_path))

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
        _LOGGER.error(f'{project_dir.absolute()} is not a valid ttrpg_scribe project:\n'
                      f'{'\n'.join(f'\t{issue}' for issue in issues)}')
        return False
    return True


def start(project: Path, debug: bool):
    import dotenv
    import waitress

    dotenv.load_dotenv(project/'local.env')

    if not check_structure(project):
        return

    logging.basicConfig(level=logging.INFO,
                        format='%(name)s @ %(levelname)s: %(message)s')

    force_debug = True if debug else None
    app = make_app(project, debug=force_debug)

    host, port = '127.0.0.1', 48164
    if debug:
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
                f'ttrpg_scribe.cli.project_templates.{system}')) as template:
            shutil.copytree(template, project_dir, dirs_exist_ok=project_dir == Path.cwd())
    except ModuleNotFoundError:
        raise ValueError(f'No project template for {system} game system') from None


def pf2e_foundry(parent: _SubParsersAction):
    def start_mongo(rebuild: bool):
        from ttrpg_scribe.pf2e_compendium.foundry import mongo_server

        logging.basicConfig(level=logging.INFO,
                            format='%(name)s @ %(levelname)s: %(message)s')
        mongo_server.start()
        if rebuild:
            from ttrpg_scribe.pf2e_compendium.foundry import mongo_client
            mongo_client.update()
        logging.info('Mongo server ready')
        try:
            while True:  # Keep server alive until termination
                pass
        except KeyboardInterrupt:
            print('Keyboard interrupt recieved')
            sys.exit(130)

    def print_dir():
        from ttrpg_scribe.pf2e_compendium import foundry
        sys.stdout.write(f'{foundry.pf2e_dir.as_posix()}\n')

    parser: ArgumentParser = parent.add_parser('pf2e_foundry')
    subparsers = parser.add_subparsers()

    add_subcommand(subparsers, 'dir', lambda _: print_dir())

    mongo_parser = add_subcommand(subparsers, 'mongo',
                                  lambda args: start_mongo(rebuild=args.rebuild))
    mongo_parser.add_argument('--rebuild', action='store_true')


def update(update_package: Path | None):
    import shutil
    import subprocess
    import tempfile
    import zipfile

    def is_wheel_zip(update_package: Path) -> bool:
        if update_package.suffix != '.zip':
            return False
        with zipfile.ZipFile(update_package) as zip:
            return any(f.startswith('ttrpg_scribe') and f.endswith('.whl') for f in zip.namelist())

    def is_source(update_package: Path):
        return (update_package/'assemble.py').exists()

    def install(update_package: Path):
        # Locate or make zip
        if is_source(update_package):
            assemble = update_package/'assemble.py'
            if (assemble := subprocess.call(assemble.as_posix(), cwd=update_package)) != 0:
                raise ValueError(f'assemble.py exited with code {assemble}')
            [zip_path] = (update_package/'dist').glob('ttrpg_scribe-*.zip')
        elif is_wheel_zip(update_package):
            zip_path = update_package
        else:
            raise ValueError('Expected ttrpg_scribe source directory or '
                'a zip of ttrpg_scribe wheels')\
                from None

        # Installation
        with tempfile.TemporaryDirectory() as extracted:
            with zipfile.ZipFile(zip_path) as zip:
                zip.extractall(extracted)

            pip = shutil.which('pip')
            assert pip is not None, 'pip is not installed'
            wheels = Path(extracted).glob('ttrpg_scribe*.whl')
            subprocess.call([pip, 'install', '--upgrade', '--force-reinstall',
                             *(f.as_posix() for f in wheels)])

    if update_package is None:
        with tempfile.TemporaryDirectory() as clone_destination:
            git = shutil.which('git')
            assert git is not None, 'git is not installed'
            subprocess.call([
                git, 'clone',
                '--depth', '1',
                'https://github.com/Daomephsta/ttrpg_scribe',
                clone_destination
            ])
            install(Path(clone_destination))
    else:
        if not update_package.exists():
            raise ValueError(f'{update_package.as_posix()} does not exist')
        install(update_package)


def main():
    import argcomplete

    parser = ArgumentParser('ttrpg_scribe')
    parser.add_argument('-p', '--project', type=Path, default=Path.cwd())
    parser.set_defaults(subcommand=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    start_parser = add_subcommand(subcommands, 'start',
                                  lambda args: start(args.project, args.debug))
    start_parser.add_argument('--debug', action='store_true')

    add_subcommand(subcommands, 'clean', lambda args: clean(args.project))

    new_parser = add_subcommand(subcommands, 'new',
                                lambda args: new(args.project, args.system))
    new_parser.add_argument('--system')

    pf2e_foundry(subcommands)

    update_parser = add_subcommand(subcommands, 'update',
                                   lambda args: update(args.new_version))
    update_parser.add_argument('new_version', type=Path, nargs='?')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    args.subcommand(args)


def add_subcommand(subcommands: _SubParsersAction, name: str,
                   subcommand: Callable[[Namespace], None]) -> ArgumentParser:
    subparser: ArgumentParser = subcommands.add_parser(name)
    subparser.set_defaults(subcommand=subcommand)
    return subparser
