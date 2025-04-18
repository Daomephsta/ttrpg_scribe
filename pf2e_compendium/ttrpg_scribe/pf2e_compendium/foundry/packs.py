import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from ttrpg_scribe.core.dice import SimpleDice
from ttrpg_scribe.core.json_path import JsonPath
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import (PF2Creature, Sense, Skill,
                                                   Spellcasting)
from ttrpg_scribe.pf2e_compendium.foundry import mongo
from ttrpg_scribe.pf2e_compendium.foundry.enrich import enrich
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

type Json = dict[str, Any]


def creature(id: str):
    try:
        return _read_creature(mongo.get_document('npc', id))
    except Exception as e:
        e.add_note(f'Reading creature {id}')
        raise


def creatures(*ids: str):
    return map_ids(creature, *ids)


def _read_creature(json: Json) -> PF2Creature:
    ALIGNMENTS = {'good', 'neutral', 'evil', 'lawful', 'chaotic'}

    SIZES = {'tiny': 'tiny', 'sm': 'small', 'med': 'medium',
             'lg': 'large', 'huge': 'huge', 'grg': 'gargantuan'}

    system = JsonPath('system')
    attributes = system.attributes

    senses = [Sense(sense['type'], sense.get('range'), sense.get('acuity'))
              for sense in system.perception.senses(json)]

    def read_skill(name: str, info: Json) -> Skill:
        special: dict[str, int] = {note['label']: note['base'] for note in info.get('special', [])}
        return Skill(name, info['base'], special)

    skills: list[Skill] = [read_skill(name, info)
                           for name, info in system.skills(json, _or={}).items()]
    interactions: list[tuple[str, str]] = []
    defenses: list[SimpleAction] = []
    actions: list[Action] = []
    inventory: dict[str, int] = {}

    @dataclass
    class SpellcastingBuilder:
        name: str
        tradition: str
        dc: int
        attack: int
        spells: dict[int, list[str]] = field(default_factory=dict)

        def add_spell(self, item):
            level = system.level.value(item)
            if level not in self.spells:
                self.spells[level] = []
            self.spells[level].append(item['_id'])
            # Replace ids with names
            for spells in self.spells.values():
                for i in range(len(spells)):
                    if spells[i] == item['_id']:
                        spells[i] = item['name']

        def add_prepared(self, level: int, spell_ids: list[str]):
            self.spells[level] = spell_ids

        def build(self):
            return Spellcasting(self.name, self.dc, self.attack, self.spells)

    spellcasting_lists: dict[str, SpellcastingBuilder] = {}

    for i, item in enumerate(json['items']):
        try:
            match item['type']:
                case 'action':
                    name = item['name']
                    desc = enrich(system.description.value(item))
                    match system.category(item):
                        case 'interaction':
                            interactions.append((name, desc))
                        case 'defensive':
                            defenses.append(_read_simple_action(item))
                        case 'offensive':
                            actions.append(_read_simple_action(item))
                case 'lore':
                    skills.append(Skill(
                        item['name'],
                        system.mod.value(item),
                        [x['label'] for x in system.variants(item, _or={}).values()]
                    ))
                case 'melee':
                    actions.append(_read_strike(item))
                case 'weapon' | 'armor' | 'consumable' | 'equipment' |\
                     'treasure' | 'shield' | 'backpack':
                    inventory[item['name']] = system.quantity(item)
                case 'spellcastingEntry':
                    spellcasting_lists[item['_id']] = builder = SpellcastingBuilder(
                        item['name'], system.tradition.value(item),
                        system.spelldc.dc(item), system.spelldc.value(item)
                    )
                    casting_type = system.prepared.value(item)
                    for level, slot_data in system.slots(item).items():
                        level = int(level.removeprefix('slot'))
                        if 'prepared' in slot_data:
                            match casting_type:
                                case 'innate':
                                    builder.spells[level] = slot_data['prepared']
                                case 'prepared':
                                    builder.spells[level] = [spell['id'] for spell
                                                     in slot_data['prepared']]
                                case 'spontaneous':
                                    pass
                                case unknown:
                                    raise ValueError(f'Unknown casting type {unknown}')
                case 'spell':
                    if 'ritual' in system(item):
                        ritual_dc = system.spellcasting.rituals.dc(json, _or=0)
                        spellcasting_lists[location := 'ritual'] = SpellcastingBuilder(
                            'Rituals', '', ritual_dc, 0)
                    else:
                        location = system.location.value(item, _or=None)
                    spellcasting_lists[location].add_spell(item)
                case 'condition':
                    interactions.append((item['name'], enrich(system.description.value(item))))
                case 'effect':
                    # Items that don't need to be in the stat block
                    pass
                case _ as unknown:
                    raise ValueError(f'Unknown item type {unknown}')
        except Exception as e:
            e.add_note(f'Item {i}: {item['name']}')
            raise
    size: str = system.traits.size.value(json)

    return PF2Creature(
        name=json['name'],
        level=system.details.level.value(json),
        rarity=system.traits.rarity(json),
        size=SIZES[size],
        # Filter out legacy alignment traits
        traits=[t for t in system.traits.value(json) if t not in ALIGNMENTS],
        perception=system.perception.mod(json),
        languages=system.details.languages.value(json),
        senses=senses,
        skills=skills,
        inventory=inventory,
        abilities={k: v['mod'] for k, v in system.abilities(json).items()},
        interactions=interactions,
        ac=attributes.ac.value(json),
        saves={k: v['value'] for k, v in system.saves(json).items()},
        max_hp=attributes.hp.max(json),
        immunities=[x['type'] for x in attributes.immunities(json, _or=[])],
        resistances={x['type']: x['value'] for x in attributes.resistances(json, _or=[])},
        weaknesses={x['type']: x['value'] for x in attributes.weaknesses(json, _or=[])},
        defenses=defenses,
        speeds={'walk': attributes.speed.value(json) or 0,
              **{speed['type']: speed['value']
                for speed in attributes.speed.otherSpeeds(json)}},
        actions=actions,
        spellcasting=[builder.build() for builder in spellcasting_lists.values()]
    )


def hazard(id: str):
    try:
        doc = mongo.get_document('npc', id)
        return _read_hazard(doc)
    except Exception as e:
        e.add_note(f'Reading hazard {id}')
        raise


def hazards(*ids: str):
    return map_ids(hazard, *ids)


def _read_hazard(json: Json) -> PF2Hazard:
    system = JsonPath('system')
    attributes = system.attributes
    details = system.details

    actions: list[Action] = []
    for i, item in enumerate(json['items']):
        try:
            match item['type']:
                case 'action':
                    actions.append(_read_simple_action(item))
                case 'melee':
                    actions.append(_read_strike(item))
                case 'consumable':
                    # Items that don't need to be in the stat block
                    pass
                case _ as unknown:
                    raise ValueError(f'Unknown item type {unknown}')
        except Exception as e:
            e.add_note(f'Item {i}: {item['name']}')
            raise

    return PF2Hazard(
        name=json['name'],
        level=details.level.value(json),
        complex=details.isComplex(json),
        stealth=attributes.stealth.value(json),
        disable=enrich(details.disable(json)),
        ac=attributes.ac.value(json),
        saves={k: v['value'] for k, v in json['system']['saves'].items()},
        max_hp=attributes.hp.value(json),
        hardness=attributes.hardness(json),
        routine=enrich(details.routine(json) or ''),  # routine can be null
        actions=actions,
        reset=enrich(details.reset(json)),
        description=system.details.description(json)
    )


def _read_simple_action(item):
    system = JsonPath('system')

    match system.actionType.value(item):
        case 'action':
            cost = system.actions.value(item)
        case 'reaction':
            cost = 'reaction'
        case 'free':
            cost = 'free'
        case 'passive':
            cost = 0
        case unknown:
            raise ValueError(f'Unknown action type {unknown}')
    return SimpleAction(item['name'], enrich(system.description.value(item)),
                        cost, system.traits.value(item))


def _read_strike(item):
    def damage(json: dict[str, Any]) -> tuple[SimpleDice | int, str]:
        damage_type: str = json['damageType']
        damage_category = json.get('category')
        if damage_category:
            damage_type = f'{damage_category} {damage_type}'
        damage: str = json['damage']
        if damage == '':
            return 0, damage_type
        elif damage.isnumeric():
            return int(damage), damage_type
        else:
            return SimpleDice.parse(json['damage']), damage_type
    system = JsonPath('system')
    strike_type = 'melee'
    if 'weaponType' in system(item):
        strike_type = system.weaponType.value(item)
    if any(t for t in system.traits.value(item) if t.startswith('thrown')):
        strike_type = 'ranged'
    return Strike(
        item['name'],
        strike_type,
        system.bonus.value(item),
        [damage(data) for data in system.damageRolls(item).values()],
        traits=system.traits.value(item),
        effects=system.attackEffects.value(item)
            if 'attackEffects' in system(item) else []
    )


def read(doc_type: str, id: str):
    return _read(mongo.get_document(doc_type, id))


def _read(data: dict[str, Any]):
    if 'type' not in data:
        return ('json', data)
    type: str = data['type']
    try:
        match type:
            case 'npc':
                return ('creature', _read_creature(data))
            case 'hazard':
                return (type, _read_hazard(data))
            case _:
                return (type, data)
    except Exception as e:
        e.add_note(f'Reading {type} {data['_id']}')
        raise


def keyed(*values: tuple[Callable[[str], Any], str | list[str]]) -> dict[str, Any]:
    def key(id: str):
        return id.rsplit('/', maxsplit=1)[-1].upper().replace('-', '_')
    return {key(id): factory(id)
            for factory, ids in values
            for id in ([ids] if isinstance(ids, str) else ids)}


def map_ids[T](factory: Callable[[str], T], *ids: str) -> dict[str, T]:
    return keyed(*((factory, id) for id in ids))


def __test_read_all_content():
    import time
    from pathlib import Path

    (logs := Path('logs')).mkdir(exist_ok=True)
    short_log = logging.getLogger('short')
    handler = logging.FileHandler(f'{logs}/{__test_read_all_content.__name__}_short.log', mode='w')
    handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(content_id)s: %(message)s\n\t%(notes)s'))
    short_log.addHandler(handler)

    full_log = logging.getLogger('full')
    handler = logging.FileHandler(f'{logs}/{__test_read_all_content.__name__}_full.log', mode='w')
    handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(content_id)s: %(message)s'))
    full_log.addHandler(handler)

    start = time.perf_counter()
    errors = 0
    for name in mongo.get_collection_names():
        for document in mongo.get_collection_content(name):
            try:
                _read(document)
                return 0
            except Exception as e:
                logging.getLogger('short').exception(
                    e, exc_info=False,
                    extra={'content_id': id, 'notes': '\n\t'.join(e.__notes__)})
                logging.getLogger('full').exception(e, extra={'content_id': id})
                return 1
    print(f'Finished test in {time.perf_counter() - start:.2f}s with {errors} errors')


if __name__ == '__main__':
    __test_read_all_content()
