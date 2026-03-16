import atexit
import logging
import shutil
import subprocess

from ttrpg_scribe.pf2e_compendium import foundry

_LOGGER = logging.getLogger(__name__)
CONNECTION_ARGS = '127.0.0.1', 48165


def start():
    IP, PORT = CONNECTION_ARGS

    (mongo_dir := foundry.data_dir/'mongod').mkdir(parents=True, exist_ok=True)
    (db_data := mongo_dir/'data/db').mkdir(parents=True, exist_ok=True)
    (logs := mongo_dir/'logs').mkdir(parents=True, exist_ok=True)

    def rotate(keep: int):
        last = keep - 1
        (logs/f'mongo-log-{last}.json').unlink(missing_ok=True)
        for i in reversed(range(keep)):
            mongo_log = logs/f'mongo-log-{i}.json'
            if mongo_log.exists():
                mongo_log.rename(logs/f'mongo-log-{i + 1}.json')
        return logs/'mongo-log-0.json'

    mongod = shutil.which('mongod')
    assert mongod, 'mongod is not installed'
    server = subprocess.Popen([
        mongod,
        '--dbpath', db_data.as_posix(),
        '--logpath', rotate(5),
        '--bind_ip', IP,
        '--port', str(PORT)
    ], env={'GLIBC_TUNABLES': 'glibc.pthread.rseq=0'})
    _LOGGER.info(f'Starting MongoDB at {IP}:{PORT}')

    def stop():
        _LOGGER.info('Stopping mongo server')
        server.terminate()
    atexit.register(stop)
