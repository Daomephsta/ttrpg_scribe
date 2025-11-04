from dataclasses import dataclass

from ttrpg_scribe.pf2e_compendium.actor import DetailedValue


@dataclass
class PF2Spell:
    name: str
    rank: int
    rarity: str
    traits: list[str]
    traditions: list[str]
    time: str
    cost: str | None
    requirements: str | None
    range: str | None
    area: DetailedValue[str] | None
    targets: str | None
    defense: str | None
    duration: str | None
    description: str

    @property
    def spell_type(self):
        if 'cantrip' in self.traits:
            return 'cantrip'
        if 'focus' in self.traits:
            return 'focus'
        return 'spell'

    @property
    def level(self):
        return self.rank
