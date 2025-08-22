import json
import logging
import re
from typing import Any, overload

import pymongo
from pymongo import IndexModel, MongoClient

from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import mongo_server

Document = dict[str, Any]
client: MongoClient[Document] = MongoClient(*mongo_server.start())
db = client.pf2e
_LOGGER = logging.getLogger(__name__)


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
    return db.list_collection_names(filter={
        # Filter out system collections and views
        'name': {'$regex': r'^(?!system\.)'}, 'type': 'collection'})


def get_pack_names(doc_type: str) -> list[str]:
    return db[doc_type].distinct('path.pack')


def get_pack_content(doc_type: str, pack: str, subpath: str):
    return db[doc_type].find({'path.pack': pack, 'path.subpath': subpath}, {'name': True})


def get_pack_subpaths(doc_type: str, pack: str):
    return db[doc_type].distinct('path.subpath', {'path.pack': pack, 'path.subpath': {'$ne': ''}})


def get_collection_content(name: str):
    return db[name].find()


def search_by_name(query: str, doc_types: list[str] = []):
    pattern = re.compile(query, re.IGNORECASE)
    if len(doc_types) == 0:
        doc_types = get_collection_names()
    for doc_type in doc_types:
        yield from db[doc_type].find({'name': pattern}, {'name': True, 'doc_type': doc_type})


def update():
    client.drop_database('pf2e')
    packs_dir = foundry.pf2e_dir/'packs'
    _LOGGER.info(f'Updating MongoDB from {packs_dir.as_posix()}')

    def build_ops_batch():
        TYPE_TO_COLL: dict[str, str] = {t: 'equipment' for t in
                        ['armor', 'backpack', 'consumable', 'kit', 'shield', 'treasure', 'weapon']}
        IGNORED = {None, 'army', 'campaignFeature', 'character', 'familiar', 'script'}
        for directory, _, files in packs_dir.walk():
            relative_dir = directory.relative_to(packs_dir)
            _LOGGER.info(f'Gathering documents from {relative_dir}')

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

    ops = list(build_ops_batch())
    _LOGGER.info('Submitting bulk write')
    result = client.bulk_write(ops)
    _LOGGER.info(f'Inserted: {result.inserted_count} Upserted: {result.upserted_count} '
          f'Modified: {result.modified_count} Deleted: {result.deleted_count}')
    for name in db.list_collection_names():
        db[name].create_indexes([
            IndexModel('foundry_id'),
            IndexModel('path.pack'),
            IndexModel('path.subpath'),
            IndexModel('name'),
        ])

    [base, *rest] = db.list_collection_names()
    db.command('create', 'all', viewOn=base, pipeline=[{'$unionWith': c} for c in rest])


if __name__ == '__main__':
    _LOGGER.info('Dropping and reconstructing database')
    update()
