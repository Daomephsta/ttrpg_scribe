import atexit
import json
import re
import shutil
import subprocess
from typing import Any, overload

import pymongo
import pymongo.database
from pymongo import MongoClient

from pf2e_compendium.ttrpg_scribe.pf2e_compendium import foundry

_IP, _PORT = '127.0.0.1', 48165
Document = dict[str, Any]
client: MongoClient[Document]
db: pymongo.database.Database[Document]


@overload
def get_document(collection: str, path: str, optional: bool) -> Document | None:
    ...


@overload
def get_document(collection: str, path: str) -> Document:
    ...


def get_document(collection: str, path: str, optional=False) -> Document | None:
    doc = db[collection].find_one({'_id': path})
    if not optional and doc is None:
        raise KeyError(f'{path} not found in {collection}')
    return doc


def get_collection_names() -> list[str]:
    return db.list_collection_names()


def get_pack_names(doc_type: str) -> list[str]:
    return db[doc_type].distinct('path.pack')


def get_pack_content(doc_type: str, pack: str, subpath: str):
    return db[doc_type].find({'path.pack': pack, 'path.subpath': subpath}, {'name': True})


def get_pack_subpaths(doc_type: str, pack: str):
    return db[doc_type].distinct('path.subpath', {'path.pack': pack, 'path.subpath': {'$ne': ''}})


def get_collection_content(name: str):
    return db[name].find()


def search_by_path(query: str, doc_types: list[str] = []):
    pattern = re.compile(query)
    if len(doc_types) == 0:
        doc_types = get_collection_names()
    for doc_type in doc_types:
        yield from db[doc_type].find({'path.stem': pattern}, {'name': True, 'doc_type': doc_type})


def update():
    packs_dir = foundry.pf2e_dir/'packs'

    def build_ops_batch():
        TYPE_TO_COLL: dict[str, str] = {t: 'equipment' for t in
                        ['armor', 'backpack', 'consumable', 'kit', 'shield', 'treasure', 'weapon']}
        IGNORED = {None, 'army', 'campaignFeature', 'character', 'familiar', 'script'}
        for directory, _, files in packs_dir.walk():
            relative_dir = directory.relative_to(packs_dir)
            print(f'Gathering documents from {relative_dir}')

            for filename in files:
                doc_id = (relative_dir/filename).with_suffix('').as_posix()
                with (packs_dir/f'{doc_id}.json').open(encoding='utf8') as file:
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
    (mongo_dir := foundry.data_dir/'mongod').mkdir(parents=True, exist_ok=True)
    (db_data := mongo_dir/'data/db').mkdir(parents=True, exist_ok=True)
    (logs := mongo_dir/'logs/').mkdir(parents=True, exist_ok=True)
    mongod = shutil.which('mongod')
    assert mongod, 'mongod is not installed'
    server = subprocess.Popen([
        mongod,
        '--dbpath', db_data.as_posix(),
        '--logpath', (logs/'mongo-log.json').as_posix(),
        '--bind_ip', _IP,
        '--port', str(_PORT)
    ], env={'GLIBC_TUNABLES': 'glibc.pthread.rseq=0'})

    def stop():
        print('Stopping mongo server')
        server.terminate()
    atexit.register(stop)
    global client, db
    client = MongoClient(_IP, _PORT)
    db = client.pf2e


start_mongo_server()

if __name__ == '__main__':
    update()
