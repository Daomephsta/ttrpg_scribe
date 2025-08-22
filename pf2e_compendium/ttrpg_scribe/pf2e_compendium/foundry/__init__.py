import json
import logging
import shutil
import subprocess

import platformdirs

VERSION = '7.4.1'
data_dir = (platformdirs.user_data_path('ttrpg_scribe') / 'pf2e_compendium/data').absolute()
pf2e_dir = (data_dir / 'foundryvtt/pf2e').absolute()
_LOGGER = logging.getLogger(__name__)


def check_for_updates():
    if pf2e_dir.exists():
        system_data = json.loads((pf2e_dir/'static/system.json').read_text())
        if system_data['version'] == VERSION:
            _LOGGER.info(f'PF2e system already compatible ({VERSION})')
            return
        else:
            _LOGGER.info(f'Replacing {system_data['version']} with {VERSION}')
            shutil.rmtree(pf2e_dir)
            create = True
    else:
        create = True

    if create:
        from ttrpg_scribe.pf2e_compendium.foundry import mongo_client
        subprocess.run([
            'git', 'clone',
            '--depth', '1',
            '--branch', VERSION,
            'https://github.com/foundryvtt/pf2e',
            pf2e_dir.as_posix()])
        mongo_client.update()
