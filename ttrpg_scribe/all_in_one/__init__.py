import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
# Imports used by single functions are at the top of said functions for autocomplete speed reasons


def make_app(project_dir: str | Path, config: Path | None = None, debug: bool | None = None):
    from http import HTTPStatus

    import ttrpg_scribe.core.typescript
    import ttrpg_scribe.dnd_bestiary.flask
    import ttrpg_scribe.encounter.flask.plugin
    import ttrpg_scribe.notes
    import ttrpg_scribe.npc.flask_app.plugin
    import ttrpg_scribe.pf2e_compendium.flask
    from ttrpg_scribe.core.plugin import Plugin
    from werkzeug.middleware.dispatcher import DispatcherMiddleware

    project_dir = Path(project_dir)
    app = ttrpg_scribe.notes.create_app(config or project_dir/'config.py', project_dir)
    if debug is not None:
        app.debug = debug
    app.jinja_options.update(
        lstrip_blocks=True,
        trim_blocks=True
    )

    PLUGIN_FACTORIES: dict[str, type[Plugin]] = {
        'dnd_5e': ttrpg_scribe.dnd_bestiary.flask.Dnd5ePlugin,
        'pf2e': ttrpg_scribe.pf2e_compendium.flask.Pf2ePlugin,
        'encounter': ttrpg_scribe.encounter.flask.plugin.EncounterPlugin,
        'npc': ttrpg_scribe.npc.flask_app.plugin.NpcPlugin,
    }
    active_plugins: list[tuple[str, type[Plugin]]] = [(id, PLUGIN_FACTORIES[id])
                                                      for id in app.config['PLUGINS']]

    plugin_apps = {}
    for _, plugin in active_plugins:
        plugin.configure(app)
    for id, plugin in active_plugins:
        plugin_app = plugin.create_app(project_dir, app.config)
        if plugin_app is not None:
            plugin_apps[f'/{id}'] = plugin_app
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, plugin_apps)

    if debug:
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


def start(project: Path, config: str | None, debug: bool):
    import waitress

    if not check_structure(project):
        return

    logging.basicConfig(level=logging.INFO,
                        format='%(name)s @ %(levelname)s: %(message)s')

    force_debug = True if debug else None
    config_dir: Path = project/'config'
    if config_dir.exists():
        if config is not None:
            app = make_app(project, config_dir/f'{config}.py', debug=force_debug)
        else:
            configs = ', '.join(path.stem for path in config_dir.glob('*.py'))
            _LOGGER.error('Multiconfig projects must specify --config\n'
                          f'Available configs: {configs}')
            return
    else:
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
                f'ttrpg_scribe.all_in_one.project_templates.{system}')) as template:
            shutil.copytree(template, project_dir, dirs_exist_ok=project_dir == Path.cwd())
    except ModuleNotFoundError:
        raise ValueError(f'No project template for {system} game system') from None


def pf2e_foundry(args):
    import sys

    from ttrpg_scribe.pf2e_compendium import foundry
    match args.foundry_command:
        case 'dir':
            sys.stdout.write(f'{foundry.pf2e_dir.as_posix()}\n')
        case 'mongo':
            from ttrpg_scribe.pf2e_compendium.foundry import mongo_server
            mongo_server.start()
            try:
                while True:  # Keep server alive until termination
                    pass
            except KeyboardInterrupt:
                print('Keyboard interrupt recieved')
                sys.exit(130)


def update(new_version: Path):
    import shutil
    import zipfile
    import tempfile
    import subprocess

    # Preconditions
    if not new_version.exists():
        raise ValueError(f'{new_version.as_posix()} does not exist')

    def is_wheel_zip(new_version: Path) -> bool:
        if new_version.suffix != '.zip':
            return False
        with zipfile.ZipFile(new_version) as zip:
            return any(f.startswith('ttrpg_scribe') and f.endswith('.whl') for f in zip.namelist())

    def is_source(new_version: Path):
        return (new_version/'assemble.sh').exists()

    # Locate or make zip
    if is_source(new_version):
        assemble = new_version/'assemble.sh'
        if (assemble := subprocess.call(assemble.as_posix(), cwd=new_version)) != 0:
            raise ValueError(f'assemble.sh exited with code {assemble}')
        [zip_path] = (new_version/'dist').glob('ttrpg_scribe-*.zip')
    elif is_wheel_zip(new_version):
        zip_path = new_version
    else:
        raise ValueError('Expected ttrpg_scribe source directory or a zip of ttrpg_scribe wheels')\
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
    start_parser.set_defaults(subcommand=lambda args: start(args.project, args.config, args.debug))

    clean_parser = subcommands.add_parser('clean')
    clean_parser.set_defaults(subcommand=lambda args: clean(args.project))

    new_parser = subcommands.add_parser('new')
    new_parser.add_argument('--system')
    new_parser.set_defaults(subcommand=lambda args: new(args.project, args.system))

    foundry_parser = subcommands.add_parser('pf2e_foundry')
    foundry_parser.add_argument('foundry_command', choices=['dir', 'mongo'])
    foundry_parser.set_defaults(subcommand=pf2e_foundry)

    update_parser = subcommands.add_parser('update')
    update_parser.add_argument('new_version', type=Path)
    update_parser.set_defaults(subcommand=lambda args: update(args.new_version))

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    args.subcommand(args)
