import itertools

import pytest
from bs4 import BeautifulSoup, Tag

from ttrpg_scribe.pf2e_compendium.foundry.enrich import enrich


@pytest.mark.parametrize(['text', 'result'], [
    ('@Damage[1d6[fire]]{ouch!}', 'ouch!'),
    ('@Damage[(1d6 + 3)[fire]]', [('1d6 + 3', 'fire')]),
    ('@Damage[5d6[acid],5d6[cold],5d6[fire]]',
     [('5d6', 'acid'), ('5d6', 'cold'), ('5d6', 'fire')]),
    ('@Damage[(2d6 + 4 + (2d6[precision]))[slashing]]',
     [('2d6 + 4', 'slashing'), ('2d6', 'precision slashing')]),
    ('@Damage[(5[splash])[fire]]', [('5', 'splash fire')]),
    ('@Damage[1d6[persistent,fire]]', [('1d6', 'persistent fire')]),
    ('@Damage[2d6[fire]|options:area-damage]', [('2d6', 'fire')]),
])
def test_damage_enricher(text: str, result: str | list[tuple[str, str]]):
    enriched = enrich(text)
    match result:
        case str():
            assert enriched == result
        case _:
            soup = BeautifulSoup(enriched, features='html.parser')
            assert len(soup) == 1, 'Expected 1 top level tag'
            [top] = soup
            assert isinstance(top, Tag), 'Expected top level tag'

            def extract(t) -> tuple[str, str]:
                amount, categories = t
                assert isinstance(amount, Tag), 'Expected amount tag'
                assert isinstance(categories, str), 'Expected categories str'
                return amount.text, categories.strip(' +')

            batches = itertools.batched(top.children, n=2)
            for actual, expected in zip(map(extract, batches), result):
                assert actual == expected
