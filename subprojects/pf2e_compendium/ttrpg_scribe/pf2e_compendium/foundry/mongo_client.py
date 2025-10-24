import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Iterable, cast, overload

import pymongo
from pymongo import IndexModel, MongoClient
from pymongo.synchronous.collection import _WriteOp

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


def unionOf(collections: list[str]):
    yield {'$documents': []}
    for c in collections:
        yield {
            '$unionWith': {
                'coll': c,
                'pipeline': [{'$addFields': {'doc_type': c}}]
            }
        }


def bulk_write(ops: Iterable[_WriteOp]):
    _LOGGER.info('Submitting bulk write')
    result = client.bulk_write(list(ops))
    _LOGGER.info(f'Inserted: {result.inserted_count} Upserted: {result.upserted_count} '
          f'Modified: {result.modified_count} Deleted: {result.deleted_count}')


def _import_doc(doc_id: str, doc: Document):
    TYPE_TO_COLL: dict[str, str] = {t: 'equipment' for t in
                    ['armor', 'backpack', 'consumable', 'kit', 'shield', 'treasure', 'weapon']}
    doc_type = doc.get('type')
    assert isinstance(doc_type, str)
    collection = TYPE_TO_COLL.get(doc_type, doc_type)
    doc['_id'], doc['foundry_id'] = doc_id, doc['_id']
    doc['path'] = {}
    [doc['path']['pack'], *subfolders, doc['path']['stem']] = doc_id.split('/')
    doc['path']['subpath'] = '/'.join(subfolders)
    return pymongo.InsertOne(doc, namespace=f'pf2e.{collection}')


def load_world_content(world: Path):
    import json

    import plyvel

    def slug(s: str) -> str:
        return re.sub(r'[^a-z0-9/\-]', '', s.lower().replace(' ', '-'))

    def db_iter(level_db: plyvel.DB):
        for key, doc in cast(Iterable[tuple[bytes, bytes]], level_db):
            key = key.decode()
            doc = json.loads(doc)
            yield key, doc

    def resolve_id(content_db: plyvel.DB, prefix: str, content_id: str):
        return json.loads(content_db.get(f'!{prefix}!{content_id}'.encode()))

    def resolve_id_list(content_db: plyvel.DB, prefix: str,
                        parent_id: str, content_ids: list[str]):
        return [resolve_id(content_db, prefix, f'{parent_id}.{content_id}')
                for content_id in content_ids]

    def resolve_nested_documents(content_db: plyvel.DB, doc: Document):
        match doc['type']:
            case 'npc':
                doc['items'] = resolve_id_list(content_db, 'actors.items',
                                               doc['_id'], doc['items'])

    with plyvel.DB((world/'data/folders').as_posix()) as folders_db:
        folders: dict[str, Document] = {doc['_id']: doc for _, doc in db_iter(folders_db)}

        def resolve_folder_path(doc: Document) -> str:
            segments = [doc['name']]
            while doc['folder'] is not None:
                doc = folders[doc['folder']]
                segments.insert(0, doc['name'])
            return '/'.join(segments)

        folder_paths = {key: resolve_folder_path(doc) for key, doc in folders.items()}

    def build_ops_batch():
        # Purge existing data
        for collection in get_collection_names():
            yield pymongo.DeleteMany({'volatile': True}, namespace=f'pf2e.{collection}')

        # Load data
        for content_type in (world/'data').iterdir():
            if content_type.stem not in ['actors', 'items']:
                continue
            with plyvel.DB(content_type.as_posix()) as content_db:
                for key, doc in db_iter(content_db):
                    _, kind, _ = key.split('!')
                    if '.' in kind:
                        continue  # Ignore nested documents
                    resolve_nested_documents(content_db, doc)
                    doc['volatile'] = True
                    id_parts = [world.stem, doc['name']]
                    if doc['folder'] is not None:
                        id_parts.insert(1, folder_paths[doc['folder']])
                    yield _import_doc(doc_id=slug('/'.join(id_parts)), doc=doc)

    bulk_write(build_ops_batch())


def initialise():
    if (world := os.environ.get('PF2E_COMPENDIUM_FOUNDRY_WORLD')) is not None:
        load_world_content(Path(world))


def update():
    client.drop_database('pf2e')
    packs_dir = foundry.pf2e_dir/'packs'
    _LOGGER.info(f'Updating MongoDB from {packs_dir.as_posix()}')

    def build_ops_batch():
        for directory, _, files in packs_dir.walk():
            relative_dir = directory.relative_to(packs_dir)
            _LOGGER.info(f'Gathering documents from {relative_dir}')

            for filename in files:
                doc_id = (relative_dir/filename).with_suffix('').as_posix()
                with (packs_dir/f'{doc_id}.json').open(encoding='utf8') as file:
                    doc: dict[str, Any] = json.load(file)
                IGNORED = {None, 'army', 'campaignFeature', 'character', 'familiar', 'script'}
                if not isinstance(doc, dict) or doc.get('type') in IGNORED:
                    continue
                yield _import_doc(doc_id, doc)

    bulk_write(build_ops_batch())
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
