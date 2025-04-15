import atexit
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import platformdirs
import pymongo
from pymongo import MongoClient

VERSION = '6.11.1'
_MONGO_IP, _MONGO_PORT = '127.0.0.1', 48165
_data_dir = (platformdirs.user_data_path('ttrpg_scribe') / 'pf2e_compendium/data').absolute()
_pf2e_dir = (_data_dir / 'foundryvtt/pf2e').absolute()
client: MongoClient[dict[str, Any]]


def pf2e_dir() -> Path:
    return _get_or_create_pf2e_dir()


def _get_or_create_pf2e_dir():
    if not _pf2e_dir.exists():
        subprocess.run([
            'git', 'clone',
            '--depth', '1',
            '--branch', VERSION,
            'https://github.com/foundryvtt/pf2e',
            _pf2e_dir.as_posix()])
        update()
    return _pf2e_dir


def open_pf2e_file(path: str):
    return (pf2e_dir()/path).open(encoding='utf8')


def get_document(collection: str, path: str):
    return db[collection].find_one({'_id': path})


def get_collections():
    return db.list_collection_names()


def update():
    if _pf2e_dir.exists():
        package_data = json.loads((_pf2e_dir/'package.json').read_text())
        if package_data['version'] == VERSION:
            print(f'PF2e system already compatible ({VERSION})')
            return
        else:
            print(f'Replacing {package_data['version']} with {VERSION}')
            shutil.rmtree(_pf2e_dir)
    _get_or_create_pf2e_dir()
    _update_mongo()


def _update_mongo():
    packs_dir = pf2e_dir()/'packs'

    def build_ops_batch():
        TYPE_TO_COLL: dict[str, str] = {t: 'equipment' for t in
                        ['armor', 'backpack', 'consumable', 'kit', 'shield', 'treasure', 'weapon']}
        IGNORED = {None, 'army', 'campaignFeature', 'character', 'familiar', 'script'}
        for directory, _, files in packs_dir.walk():
            relative_dir = directory.relative_to(packs_dir)
            print(f'Gathering documents from {relative_dir}')

            for filename in files:
                doc_id = (relative_dir/filename).with_suffix('').as_posix()
                with open_pf2e_file(f'packs/{doc_id}.json') as file:
                    doc: dict[str, Any] = json.load(file)
                if not isinstance(doc, dict) or (doc_type := doc.get('type')) in IGNORED:
                    continue
                assert isinstance(doc_type, str)
                collection = TYPE_TO_COLL.get(doc_type, doc_type)
                doc['_id'], doc['foundry_id'] = doc_id, doc['_id']
                doc['path'] = {}
                [doc['path']['pack'], *subfolders, doc['path']['stem']] = doc_id.split('/')
                doc['path']['subpath'] = '/'.join(subfolders)
                yield pymongo.ReplaceOne({'_id': doc_id}, doc, upsert=True,
                                         namespace=f'pf2e.{collection}')

    print('Submitting bulk write')
    result = client.bulk_write(list(build_ops_batch()))
    print(f'Inserted: {result.inserted_count} Upserted: {result.upserted_count} '
          f'Modified: {result.modified_count} Deleted: {result.deleted_count}')
    for name in db.list_collection_names():
        db[name].create_index('foundry_id')
        db[name].create_index('path')


def start_mongo_server():
    (mongo_dir := _data_dir/'mongod').mkdir(parents=True, exist_ok=True)
    (db_data := mongo_dir/'data/db').mkdir(parents=True, exist_ok=True)
    (logs := mongo_dir/'logs/').mkdir(parents=True, exist_ok=True)
    mongod = shutil.which('mongod')
    assert mongod, 'mongod is not installed'
    server = subprocess.Popen([
        mongod,
        '--dbpath', db_data.as_posix(),
        '--logpath', (logs/'mongo-log.json').as_posix(),
        '--bind_ip', _MONGO_IP,
        '--port', str(_MONGO_PORT)
    ], env={'GLIBC_TUNABLES': 'glibc.pthread.rseq=0'})

    def stop():
        print('Stopping mongo server')
        server.terminate()
    atexit.register(stop)
    global client, db
    client = MongoClient(_MONGO_IP, _MONGO_PORT)
    db = client.pf2e


start_mongo_server()
update()

if __name__ == '__main__':
    _update_mongo()
