import pytest

from ttrpg_scribe.pf2e_compendium.foundry import mongo_client


def pytest_addoption(parser: pytest.Parser, pluginmanager):
    parser.addoption("--sample-size", action="store", default=None, type=int)


def pytest_generate_tests(metafunc: pytest.Metafunc):
    if 'test_document' in metafunc.fixturenames:
        sample: int | None = metafunc.config.getoption("--sample-size")
        metafunc.parametrize('test_document', sample_documents(sample), ids=lambda doc: doc['_id'])


def sample_documents(sample: int | None):
    [base, *rest] = mongo_client.get_collection_names()
    pipeline: list[dict] = [{'$unionWith': c} for c in rest]
    if sample is not None:
        pipeline.append({'$sample': {'size': sample}})
    yield from mongo_client.db[base].aggregate(pipeline)
