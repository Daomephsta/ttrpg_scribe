import pytest
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import packs


@pytest.fixture(scope='session')
def setup_mongo():
    foundry.initialise()


_BUGS: dict[str, tuple[type[Exception], str]] = {
    'lost-omens-bestiary/shining-kingdoms/lamp-blighter': (
        KeyError, 'rituals'
    ),
    **{key: (ValueError, r'^Unknown skill') for key in [
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-envy',
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-wrath',
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-pride',
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-lust',
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-greed',
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-gluttony',  # noqa: E501
        'revenge-of-the-runelords-bestiary/book-1-lord-of-the-trinity-star/risen-runelord-sloth',
    ]}
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
