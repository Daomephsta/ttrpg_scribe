import sys
from dataclasses import dataclass
from typing import Any, Self

from dnd_scribe.pf2e_bestiary.foundry.enrich import enrich

type Json = dict[str, Any]


@dataclass
class Action:
    name: str
    cost: int
    traits: list[str]

    def kind(self):
        return self.__class__.__name__


@dataclass
class SimpleAction(Action):
    desc: str


@dataclass
class Melee(Action):
    bonus: int
    damage: list[tuple[str, str]]
    effects: list[str]

    def attack_maluses(self):
        if 'agile' in self.traits:
            return [0, 4, 8]
        return [0, 5, 10]


@dataclass
class PF2Creature:
    name: str
    alignments: list[str]
    size: str
    traits: list[str]
    perception: int
    senses: list[str]
    skills: list[tuple[str, int]]
    abilities: dict[str, int]
    interactions: list[str]
    ac: int
    saves: dict[str, int]
    max_hp: int
    immunities: list[str]
    weaknesses: list[tuple[str, int]]
    defenses: list[str]
    speeds: dict[str, int]
    actions: list[Action]

    @classmethod
    def from_json(cls, data) -> Self:
        ALIGNMENTS = {'good', 'neutral', 'evil', 'lawful', 'chaotic'}

        def sort_alignment(alignment: str) -> int:
            match alignment:
                case 'lawful' | 'good':
                    return -1
                case _:
                    return 0

        SIZES = {'sm': 'small', 'med': 'medium'}

        system: Json = data['system']
        attributes: Json = system['attributes']
        traits: Json = system['traits']
        simple_traits: list[str] = traits['value']
        alignments = sorted((x for x in simple_traits if x in ALIGNMENTS),
                            key=sort_alignment)
        for a in alignments:
            simple_traits.remove(a)

        skills = []
        interactions = []
        defenses = []
        actions = []
        for item in data['items']:
            match item['type']:
                case 'action':
                    name = item['name']
                    desc = enrich(item['system']['description']['value'])
                    match item['system']['category']:
                        case 'interaction':
                            interactions.append((name, desc))
                        case 'defensive':
                            defenses.append((name, desc))
                        case 'offensive':
                            cost = item['system']['actions']['value']
                            if cost is None:
                                cost = 0
                            actions.append(SimpleAction(
                                name, cost,
                                item['system']['traits']['value'],
                                desc))
                case 'lore':
                    skills.append((
                        item['name'],
                        item['system']['mod']['value']))
                case 'melee':
                    actions.append(Melee(
                        item['name'],
                        1,
                        item['system']['traits']['value'],
                        item['system']['bonus']['value'],
                        [(v['damage'], v['damageType'])
                         for v in item['system']['damageRolls'].values()],
                        item['system']['attackEffects']['value']
                            if 'attackEffects' in item['system'] else []
                    ))
                case _ as unknown:
                    print(f"Ignored item {item['name']} with type {unknown}",
                          file=sys.stderr)

        speeds = [(speed['type'], speed['value'])
                  for speed in attributes['speed']['otherSpeeds']]
        speeds.insert(0, ('walk', attributes['speed']['value']))

        return PF2Creature(
            name=data['name'],
            alignments=alignments if alignments else ['neutral'],
            size=SIZES[traits['size']['value']],
            traits=simple_traits,
            perception=attributes['perception']['value'],
            senses=traits['senses']['value'].split(', '),
            skills=skills,
            abilities={k: v['mod'] for k, v in system['abilities'].items()},
            interactions=interactions,
            ac=attributes['ac']['value'],
            saves={k: v['value'] for k, v in system['saves'].items()},
            max_hp=attributes['hp']['max'],
            immunities=[x['type'] for x in attributes.get('immunities', [])],
            weaknesses=[(x['type'], x['value'])
                        for x in attributes.get('weaknesses', [])],
            defenses=defenses,
            speeds=dict(speeds),
            actions=actions
        )
