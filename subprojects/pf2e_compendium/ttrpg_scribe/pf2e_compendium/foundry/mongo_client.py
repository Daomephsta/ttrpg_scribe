import json
import logging
import os
from pathlib import Path
from typing import Any, Generator, Iterable, Literal, cast, overload

import plyvel
import pymongo
import pymongo.errors
from pymongo import IndexModel, InsertOne, MongoClient
from pymongo.synchronous.collection import _WriteOp
from slugify import slugify

from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import mongo_server

Document = dict[str, Any]
client: MongoClient[Document] = MongoClient(*mongo_server.start())
db = client.pf2e
_LOGGER = logging.getLogger(__name__)


@overload
def get_document(collection: str, doc_id: str, id_type: Literal['path', 'uuid'], optional: bool
                 ) -> Document | None:
    ...


@overload
def get_document(collection: str, doc_id: str) -> Document:
    ...


@overload
def get_document(collection: str, doc_id: str, id_type: Literal['path', 'uuid']) -> Document:
    ...


def get_document(collection: str, doc_id: str, id_type: Literal['path', 'uuid'] = 'path',
                 optional=False) -> Document | None:
    id_key: str = '_id' if id_type == 'path' else 'foundry_id'
    doc = db[collection].find_one({id_key: doc_id})
    if not optional and doc is None:
        raise KeyError(f'{doc_id} not found in {collection}')
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
    ops = list(ops)  # Resolve before submitting
    _LOGGER.info('Submitting bulk write')
    try:
        result = client.bulk_write(ops)
        _LOGGER.info(f'Inserted: {result.inserted_count} Upserted: {result.upserted_count} '
              f'Modified: {result.modified_count} Deleted: {result.deleted_count}')
    except pymongo.errors.ClientBulkWriteException as ex:
        _LOGGER.error(f'{type(ex).__name__} {json.dumps(ex.details, indent=2)}')


def _purge_world_content():
    for collection in get_collection_names():
        yield pymongo.DeleteMany({'volatile': True}, namespace=f'pf2e.{collection}')


def _open_db(path: Path) -> plyvel.DB:
    return plyvel.DB(path.as_posix())


def _db_iter(level_db: plyvel.DB) -> Generator[tuple[str, Any], None, None]:
    for key, doc in cast(Iterable[tuple[bytes, bytes]], level_db):
        yield key.decode(), json.loads(doc)


def _resolve_folder_paths(folder_docs: Iterable[Document]) -> dict[str, str]:
    folders_by_id: dict[str, Document] = {doc['_id']: doc for doc in folder_docs}

    def resolve_folder_path(doc: Document) -> str:
        segments = [doc['name']]
        while doc['folder'] is not None:
            doc = folders_by_id[doc['folder']]
            segments.insert(0, doc['name'])
        return '/'.join(segments)
    return {key: resolve_folder_path(doc) for key, doc in folders_by_id.items()}


def _import_db_from_path(db_path: Path, id_root: str, folder_paths: dict[str, str]
                         ) -> Generator[InsertOne[Document], None, None]:
    return _import_db(_open_db(db_path), id_root, folder_paths)


def _import_db(db: plyvel.DB, id_root: str, folder_paths: dict[str, str]
               ) -> Generator[InsertOne[Document], None, None]:
    IGNORED = {None, 'army', 'campaignFeature', 'character', 'familiar', 'script'}

    def resolve_id(db: plyvel.DB, prefix: str, content_id: str):
        return json.loads(db.get(f'!{prefix}!{content_id}'.encode()))

    def resolve_id_list(db: plyvel.DB, prefix: str,
                        parent_id: str, content_ids: list[str]):
        return [resolve_id(db, prefix, f'{parent_id}.{content_id}')
                for content_id in content_ids]

    def resolve_nested_documents(db: plyvel.DB, doc: Document):
        match doc['type']:
            case 'npc':
                doc['items'] = resolve_id_list(db, 'actors.items',
                                               doc['_id'], doc['items'])

    def import_doc(doc_id: str, doc: Document):
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

    with db:
        for key, doc in _db_iter(db):
            if not isinstance(doc, dict) or doc.get('type') in IGNORED:
                continue
            doc = cast(dict[str, Any], doc)
            try:
                _, kind, _ = key.split('!')
                if kind == 'folders' or '.' in kind:
                    continue  # Ignore nested documents and folders
                resolve_nested_documents(db, doc)
                id_parts = [id_root, doc['name']]
                if (folder := folder_paths.get(doc.get('folder', ''))) is not None:
                    id_parts.insert(1, folder)
                yield import_doc(doc_id='/'.join(map(slugify, id_parts)), doc=doc)
            except Exception as e:
                e.add_note(f'{doc['name']=}')
                raise e


def load_world_content(world: Path):
    with _open_db(world/'data/folders') as folders_db:
        folder_paths = _resolve_folder_paths(doc for _, doc in _db_iter(folders_db))

    def build_ops_batch():
        # Purge existing data
        yield from _purge_world_content()
        # Load data
        for content_type in (world/'data').iterdir():
            if content_type.stem not in ['actors', 'items']:
                continue
            yield from _import_db_from_path(content_type, world.stem, folder_paths)

    bulk_write(build_ops_batch())


def initialise():
    if (world := os.environ.get('PF2E_COMPENDIUM_FOUNDRY_WORLD')) is not None:
        load_world_content(Path(world))
    else:
        bulk_write(_purge_world_content())


def update():
    client.drop_database('pf2e')
    packs_dir = foundry.pf2e_dir/'packs'
    _LOGGER.info(f'Updating MongoDB from {packs_dir.as_posix()}')
    system_data: dict[str, Any] = json.loads((foundry.pf2e_dir/'system.json').read_text())
    from rich.progress import Progress

    def build_ops_batch():
        packs: list = system_data['packs']
        with Progress(*Progress.get_default_columns(), '{task.fields[pack]}') as bar:
            task = bar.add_task('Loading packs', total=len(packs), pack='?')
            for pack in packs:
                bar.update(task, pack=pack['name'])
                with _open_db(foundry.pf2e_dir/pack['path']) as content_db:
                    folder_paths = _resolve_folder_paths(doc for key, doc in _db_iter(content_db)
                                                         if '!folders!' in key)
                    yield from _import_db(content_db, pack['name'], folder_paths)
                bar.advance(task)

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
