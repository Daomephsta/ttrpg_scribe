import pytest
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import packs


@pytest.fixture(scope='session')
def setup_mongo():
    foundry.check_for_updates()


@pytest.mark.usefixtures('setup_mongo')
def test_read_document(test_document):
    packs.read(test_document)
