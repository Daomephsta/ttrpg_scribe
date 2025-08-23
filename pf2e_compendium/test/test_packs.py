import pytest
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import packs


@pytest.fixture(scope='session')
def setup_mongo():
    foundry.check_for_updates()


_BUGS: dict[str, tuple[type[Exception], str]] = {
    'lost-omens-bestiary/shining-kingdoms/lamp-blighter': (
        KeyError, 'rituals'
    )
}


@pytest.mark.usefixtures('setup_mongo')
def test_read_document(test_document):
    match _BUGS.get(test_document['_id'], None):
        case ex_type, pattern:
            with pytest.raises(ex_type, match=pattern):
                packs.read(test_document)
            pytest.xfail('Foundry PF2e system bug')
        case None:
            packs.read(test_document)
