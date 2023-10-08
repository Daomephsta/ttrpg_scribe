from dataclasses import dataclass

from . import Creature
from .ability import Ability


@dataclass
class Spellcasting:
    level: int
    ability: Ability
    spell_list: str
    at_will: list[str]
    levelled: dict[int, tuple[int, list[str]]]

    def __call__(self, creature: Creature) -> tuple[str, str]:
        def level_ordinal(level: int) -> str:
            match level:
                case 1: return '1st'
                case 2: return '2nd'
                case 3: return '3rd'
                case _: return f'{level}th'
        save_dc = 8 + creature.prof + self.ability.mod(creature)
        spell_attack = creature.prof + self.ability.mod(creature)
        desc = f"{creature.name} is a {level_ordinal(self.level)}-level spellcaster \
            who uses {self.ability.name} for spellcasting \
            (spell save DC {save_dc}; {spell_attack:+d} to hit with spell attacks). \
            {creature.name} knows the following spells from the {self.spell_list}'s spell list:"
        if self.at_will:
            desc += f"\n\nAt will: {', '.join(self.at_will)}"
        for level, (slots, spells) in self.levelled.items():
            desc += f"\n\n{level_ordinal(level)} level ({slots} slots): {', '.join(spells)}"
        return ('Spellcasting', desc)
