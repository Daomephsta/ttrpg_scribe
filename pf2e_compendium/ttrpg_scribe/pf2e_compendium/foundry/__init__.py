import json
import shutil
import subprocess

import platformdirs

from ttrpg_scribe.pf2e_compendium.foundry import mongo

VERSION = '6.11.1'
data_dir = (platformdirs.user_data_path('ttrpg_scribe') / 'pf2e_compendium/data').absolute()
pf2e_dir = (data_dir / 'foundryvtt/pf2e').absolute()


def update():
    if pf2e_dir.exists():
        package_data = json.loads((pf2e_dir/'package.json').read_text())
        if package_data['version'] == VERSION:
            print(f'PF2e system already compatible ({VERSION})')
            return
        else:
            print(f'Replacing {package_data['version']} with {VERSION}')
            shutil.rmtree(pf2e_dir)
            create = True
    else:
        create = True

    if create:
        subprocess.run([
            'git', 'clone',
            '--depth', '1',
            '--branch', VERSION,
            'https://github.com/foundryvtt/pf2e',
            pf2e_dir.as_posix()])
        update()
        mongo.update()


update()
