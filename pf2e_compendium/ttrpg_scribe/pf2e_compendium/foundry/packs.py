import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import platformdirs

from ttrpg_scribe.core.json_path import JsonPath
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import (PF2Creature, Sense, Skill,
                                                   Spellcasting)
from ttrpg_scribe.pf2e_compendium.foundry.enrich import enrich
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

type Json = dict[str, Any]
VERSION = '6.0.4'
_pf2e_dir = (platformdirs.user_data_path('ttrpg_scribe') /
                'pf2e_compendium/data/foundryvtt/pf2e').absolute()


def pf2e_dir() -> Path:
    return _get_or_create_pf2e_dir()


def _get_or_create_pf2e_dir():
    if not _pf2e_dir.exists():
        subprocess.run([
            'git', 'clone',
            '--depth', '1',
            '--branch', VERSION,
            'https://github.com/foundryvtt/pf2e',
            _pf2e_dir.as_posix()])
    return _pf2e_dir


def open_pf2e_file(path: str):
    return (pf2e_dir()/path).open(encoding='utf8')


def update():
    if _pf2e_dir.exists():
        package_data = json.loads((_pf2e_dir/'package.json').read_text())
        if package_data['version'] == VERSION:
            print(f'PF2e system already compatible ({VERSION})')
            return
        else:
            print(f'Replacing {package_data['version']} with {VERSION}')
            shutil.rmtree(_pf2e_dir)
    _get_or_create_pf2e_dir()


def creature(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        try:
            return _read_creature(json.load(file))
        except Exception as e:
            e.add_note(f'Reading creature {id}')
            raise


def _read_creature(json: Json) -> PF2Creature:
    ALIGNMENTS = {'good', 'neutral', 'evil', 'lawful', 'chaotic'}

    SIZES = {'sm': 'small', 'med': 'medium'}

    system = JsonPath('system')
    attributes = system.attributes
    traits = system.traits

    simple_traits: list[str] = traits.value(json)
    # Filter out legacy alignment traits
    simple_traits = [t for t in simple_traits if t not in ALIGNMENTS]

    senses = [Sense(sense['type'], sense.get('range'), sense.get('acuity'))
              for sense in system.perception.senses(json)]

    skills: list[Skill] = []
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
            return Spellcasting(self.name, self.tradition, self.dc, self.attack, self.spells)

    spellcasting_lists: dict[str, SpellcastingBuilder] = {}

    for item in json['items']:
        match item['type']:
            case 'action':
                name = item['name']
                desc = enrich(system.description.value(item))
                match system.category(item):
                    case 'interaction':
                        interactions.append((name, desc))
                    case 'defensive':
                        match system.actionType.value(item):
                            case 'passive':
                                cost = 0
                            case 'reaction':
                                cost = 're'
                            case unknown:
                                print(f'Unknown action type {unknown} for item {item['name']}',
                                      file=sys.stderr)
                                cost = 0
                        defenses.append(SimpleAction(name, desc, cost))
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
            case 'weapon' | 'armor' | 'consumable' | 'equipment':
                inventory[item['name']] = system.quantity(item)
            case 'spellcastingEntry':
                spellcasting_lists[item['_id']] = builder = SpellcastingBuilder(
                    item['name'], system.tradition.value(item),
                    system.spelldc.dc(item), system.spelldc.value(item)
                )
                for level, slot_data in system.slots(item).items():
                    level = int(level.removeprefix('slot'))
                    if slot_data['prepared']:
                        builder.spells[level] = [spell['id'] for spell in slot_data['prepared']]
            case 'spell':
                location = system.location.value(item)
                spellcasting_lists[location].add_spell(item)
            case _ as unknown:
                print(f"Ignored item {item['name']} of {json['name']} with type {unknown}",
                      file=sys.stderr)

    size = traits.size.value(json)

    return PF2Creature(
        name=json['name'],
        level=system.details.level.value(json),
        size=SIZES.get(size, size),
        traits=simple_traits,
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
        resistances=[(x['type'], x['value']) for x in attributes.resistances(json, _or=[])],
        weaknesses=[(x['type'], x['value']) for x in attributes.weaknesses(json, _or=[])],
        defenses=defenses,
        speeds={'walk': attributes.speed.value(json),
              **{speed['type']: speed['value']
                for speed in attributes.speed.otherSpeeds(json)}},
        actions=actions,
        spellcasting=[builder.build() for builder in spellcasting_lists.values()]
    )


def hazard(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        try:
            return _read_hazard(json.load(file))
        except Exception as e:
            e.add_note(f'Reading hazard {id}')
            raise


def _read_hazard(json: Json) -> PF2Hazard:
    system = JsonPath('system')
    attributes = system.attributes
    details = system.data.details

    actions: list[Action] = []
    for item in json['items']:
        match item['type']:
            case 'action':
                actions.append(_read_simple_action(item))
            case 'melee':
                actions.append(_read_strike(item))
            case _ as unknown:
                print(f"Ignored item {item['name']} with type {unknown}",
                      file=sys.stderr)

    return PF2Hazard(
        name=json['name'],
        level=details.level.value(json),
        complex=details.isComplex(json),
        stealth=attributes.stealth.value(json),
        disable=enrich(details.disable(json)),
        ac=attributes.ac.value(json),
        saves={k: v['value'] for k, v in json['system']['saves'].items()},
        hp=attributes.hp.value(json),
        hardness=attributes.hardness(json),
        routine=enrich(details.routine(json)),
        actions=actions,
        reset=enrich(details.reset(json)),
    )


def _read_simple_action(item):
    system = JsonPath('system')

    match system.actionType.value(item):
        case 'action':
            cost = system.actions.value(item)
        case 'reaction':
            cost = 'reaction'
        case str():
            cost = 0
        case unknown:
            raise ValueError(f'Unknown action type {unknown}')
    return SimpleAction(item['name'], enrich(system.description.value(item)),
                        cost, system.traits.value(item))


def _read_strike(item):
    def damage(json):
        damage_type = json['damageType']
        damage_category = json.get('category')
        if damage_category:
            damage_type = f'{damage_category} {damage_type}'
        return json['damage'], damage_type

    system = JsonPath('system')
    return Strike(
        item['name'],
        system.weaponType.value(item),
        system.bonus.value(item),
        [damage(data) for data in system.damageRolls(item).values()],
        traits=system.traits.value(item),
        effects=system.attackEffects.value(item)
            if 'attackEffects' in system(item) else []
    )


def content(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        data: Json = json.load(file)
        if 'type' not in data:
            print(f'Cannot determine content type for {id}, using \'json\'', file=sys.stderr)
            return ('json', data)
        type: str = data['type']
        try:
            match type:
                case 'npc':
                    return ('creature', _read_creature(data))
                case 'hazard':
                    return (type, _read_hazard(data))
                case _:
                    print(f'Unknown content type {type}', file=sys.stderr)
                    return (type, data)
        except Exception as e:
            e.add_note(f'Reading {type} {id}')
            raise
