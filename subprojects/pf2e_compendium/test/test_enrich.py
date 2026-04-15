import itertools

import pytest
from bs4 import BeautifulSoup, Tag

from ttrpg_scribe.pf2e_compendium.foundry.enrich import enrich

TEST_CONTEXT = {
    'actor': {
        'level': 3
    }
}


@pytest.mark.parametrize(['text', 'expected'], [
    ('@Damage[1d6[fire]]{ouch!}', ([('1d6', 'fire')], 'ouch!')),
    ('@Damage[(1d6 + 3)[fire]]', [('1d6 + 3', 'fire')]),
    ('@Damage[5d6[acid],5d6[cold],5d6[fire]]',
     [('5d6', 'acid'), ('5d6', 'cold'), ('5d6', 'fire')]),
    ('@Damage[(2d6 + 4 + (2d6[precision]))[slashing]]',
     [('2d6 + 4', 'slashing'), ('2d6', 'precision slashing')]),
    ('@Damage[(5[splash])[fire]]', [('5', 'splash fire')]),
    ('@Damage[1d6[persistent,fire]]', [('1d6', 'persistent fire')]),
    ('@Damage[2d6[fire]|options:area-damage]', [('2d6', 'fire')]),
    ('@Damage[(@actor.level)d6[fire]]', [(f'{TEST_CONTEXT['actor']['level']}d6', 'fire')])
])
def test_damage_enricher(text: str,
                         expected: tuple[list[tuple[str, str]], str] | list[tuple[str, str]]):
    enriched = enrich(text, TEST_CONTEXT)
    soup = BeautifulSoup(enriched, features='html.parser')
    assert len(soup) == 1, 'Expected 1 top level element'
    [top] = soup
    assert isinstance(top, Tag), 'Expected top element to be tag'
    match expected:
        case list() as damage, display:
            [damage_tag, display_text] = top.children
            assert isinstance(damage_tag, Tag), 'Expected first child to be tag'
            assert isinstance(display_text, str), 'Expected second child to be str'
            assert display_text == display
        case list() as damage:
            damage_tag = top
            assert isinstance(damage_tag, Tag), 'Expected child to be tag'

    def extract(t) -> tuple[str, str]:
        amount, categories = t
        assert isinstance(amount, Tag), 'Expected amount tag'
        assert isinstance(categories, str), 'Expected categories str'
        return amount.text, categories.strip(' +')

    batches = itertools.batched(damage_tag.children, n=2)
    for actual, expected_damage in zip(map(extract, batches), damage):
        assert actual == expected_damage
