import pytest

from ttrpg_scribe.pf2e_compendium.foundry import mongo_client, packs


def all_documents():
    for collection in mongo_client.get_collection_names():
        for document in mongo_client.get_collection_content(collection):
            yield document


@pytest.mark.parametrize('document', all_documents(), ids=lambda doc: doc['_id'])
def test_read_document(document):
    packs.read(document)
