import json
import logging
import shutil
from io import BytesIO
from zipfile import ZipFile

import platformdirs
import requests
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

VERSION = '7.11.2'
data_dir = (platformdirs.user_data_path('ttrpg_scribe') / 'pf2e_compendium/data').absolute()
pf2e_dir = (data_dir / 'foundryvtt/pf2e').absolute()
initialised = False
_LOGGER = logging.getLogger(__name__)


def system_data(key: str):
    global _system
    system_json = pf2e_dir/'system.json'
    if system_json.exists():
        with system_json.open() as file:
            _system = json.load(file)
    if '_system' in globals():
        return globals()['_system'][key]
    raise RuntimeError('system.json loading failed')


def initialise(force_rebuild: bool = False):
    global initialised
    if initialised:
        return
    from ttrpg_scribe.pf2e_compendium.foundry import mongo_client, mongo_server

    def check_for_updates():
        if pf2e_dir.exists():
            if system_data('version') == VERSION:
                _LOGGER.info(f'PF2e system already compatible ({VERSION})')
                create = False
            else:
                _LOGGER.info(f'Replacing {system_data('version')} with {VERSION}')
                shutil.rmtree(pf2e_dir)
                create = True
        else:
            create = True

        def progress():
            return Progress(
               '{task.description}',
               BarColumn(),
               TimeRemainingColumn(compact=True, elapsed_when_finished=True),
               TextColumn('{task.fields[subdesc]}'),
            )

        if create:
            url = f'https://github.com/foundryvtt/pf2e/releases/download/pf2e-{VERSION}/system.zip'
            with BytesIO() as buffer, progress() as bar:
                task = bar.add_task(f'Downloading foundryvtt/pf2e-{VERSION}',
                                    total=None, subdesc='')
                response = requests.get(url, stream=True)
                response.raise_for_status()
                bar.update(task, total=int(response.headers['Content-Length']))
                chunk: bytes
                for chunk in response.iter_content(chunk_size=4 * 1024):
                    buffer.write(chunk)
                    bar.advance(task, len(chunk))
                with ZipFile(buffer) as zip:
                    zip.extractall(pf2e_dir)
                mongo_client.update(bar)
        elif force_rebuild:
            mongo_client.update(progress())

    mongo_server.start()
    mongo_client.initialise()
    check_for_updates()
    initialised = True
