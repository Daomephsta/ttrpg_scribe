import atexit
import logging
import shutil
import subprocess

from ttrpg_scribe.pf2e_compendium import foundry

_LOGGER = logging.getLogger(__name__)


def start():
    IP, PORT = '127.0.0.1', 48165

    (mongo_dir := foundry.data_dir/'mongod').mkdir(parents=True, exist_ok=True)
    (db_data := mongo_dir/'data/db').mkdir(parents=True, exist_ok=True)
    (logs := mongo_dir/'logs/').mkdir(parents=True, exist_ok=True)
    mongod = shutil.which('mongod')
    assert mongod, 'mongod is not installed'
    server = subprocess.Popen([
        mongod,
        '--dbpath', db_data.as_posix(),
        '--logpath', (logs/'mongo-log.json').as_posix(),
        '--bind_ip', IP,
        '--port', str(PORT)
    ], env={'GLIBC_TUNABLES': 'glibc.pthread.rseq=0'})
    _LOGGER.info(f'Starting MongoDB at {IP}:{PORT}')

    def stop():
        _LOGGER.info('Stopping mongo server')
        server.terminate()
    atexit.register(stop)
    return IP, PORT
