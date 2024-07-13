import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import platformdirs

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import (PF2Creature, Sense, Skill,
                                                   Spellcasting)
from ttrpg_scribe.pf2e_compendium.foundry.enrich import enrich
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

type Json = dict[str, Any]
_pf2e_pack = None


def pf2e_dir() -> Path:
    global _pf2e_pack
    if _pf2e_pack is not None:
        return _pf2e_pack
    _pf2e_pack = (platformdirs.user_data_path('ttrpg_scribe') /
                  'pf2e_compendium/data/foundryvtt/pf2e').absolute()
    if not _pf2e_pack.exists():
        subprocess.run([
            'git', 'clone', '--depth', '1',
            'https://github.com/foundryvtt/pf2e',
            _pf2e_pack.as_posix()])
    return _pf2e_pack


def open_pf2e_file(path: str):
    return (pf2e_dir()/path).open(encoding='utf8')


def update():
    subprocess.run(
        ['git', 'pull', '--depth', '1', '--rebase'],
        cwd=pf2e_dir()
    )


def creature(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        try:
            return _read_creature(json.load(file))
        except Exception as e:
            e.add_note(f'Reading creature {id}')
            raise


def _read_creature(data: Json) -> PF2Creature:
    ALIGNMENTS = {'good', 'neutral', 'evil', 'lawful', 'chaotic'}

    SIZES = {'sm': 'small', 'med': 'medium'}

    system: Json = data['system']
    attributes: Json = system['attributes']
    traits: Json = system['traits']

    simple_traits: list[str] = traits['value']
    # Filter out legacy alignment traits
    simple_traits = [t for t in simple_traits if t not in ALIGNMENTS]

    perception = system['perception']['mod']
    senses = [Sense(sense['type'], sense.get('range'), sense.get('acuity'))
              for sense in system['perception']['senses']]

    skills: list[Skill] = []
    interactions: list[tuple[str, str]] = []
    defenses: list[SimpleAction] = []
    actions: list[Action] = []
    inventory: dict[str, int] = {}
    spellcasting_lists: dict[str, Spellcasting] = {}

    for item in data['items']:
        match item['type']:
            case 'action':
                name = item['name']
                desc = enrich(item['system']['description']['value'])
                match item['system']['category']:
                    case 'interaction':
                        interactions.append((name, desc))
                    case 'defensive':
                        match item['system']['actionType']['value']:
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
                    item['system']['mod']['value'],
                    [x['label'] for x in item['system'].get('variants', {}).values()]
                ))
            case 'melee':
                actions.append(_read_strike(item))
            case 'weapon' | 'armor' | 'consumable' | 'equipment':
                inventory[item['name']] = item['system']['quantity']
            case 'spellcastingEntry':
                spellcasting_lists[item['_id']] = spellcasting = Spellcasting(
                    item['name'], item['system']['tradition']['value'],
                    item['system']['spelldc']['dc'], item['system']['spelldc']['value']
                )
                for level, slot_data in item['system']['slots'].items():
                    level = int(level.removeprefix('slot'))
                    if slot_data['prepared']:
                        spellcasting.spells[level] = [spell['id']
                            for spell in slot_data['prepared']]
            case 'spell':
                location = item['system']['location']['value']
                spellcasting = spellcasting_lists[location]
                level = item['system']['level']['value']
                level = item['system']['level']['value']
                if not level in spellcasting.spells:
                    spellcasting.spells[level] = []
                spellcasting.spells[level].append(item['_id'])
                spellcasting.id_to_name[item['_id']] = item['name']
            case _ as unknown:
                print(f"Ignored item {item['name']} of {data['name']} with type {unknown}",
                      file=sys.stderr)

    print(spellcasting_lists)

    return PF2Creature(
        name=data['name'],
        level=system['details']['level']['value'],
        size=SIZES.get(traits['size']['value'],
                       traits['size']['value']),
        traits=simple_traits,
        perception=perception,
        languages=system['details']['languages']['value'],
        senses=senses,
        skills=skills,
        inventory=inventory,
        abilities={k: v['mod'] for k, v in system['abilities'].items()},
        interactions=interactions,
        ac=attributes['ac']['value'],
        saves={k: v['value'] for k, v in system['saves'].items()},
        max_hp=attributes['hp']['max'],
        immunities=[x['type'] for x in attributes.get('immunities', [])],
        resistances=[(x['type'], x['value']) for x in attributes.get('resistances', [])],
        weaknesses=[(x['type'], x['value']) for x in attributes.get('weaknesses', [])],
        defenses=defenses,
        speeds={'walk': attributes['speed']['value'],
              **{speed['type']: speed['value']
                for speed in attributes['speed']['otherSpeeds']}},
        actions=actions,
        spellcasting=spellcasting_lists
    )


def hazard(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        try:
            return _read_hazard(json.load(file))
        except Exception as e:
            e.add_note(f'Reading hazard {id}')
            raise


def _read_hazard(data: Json) -> PF2Hazard:
    details = data['system']['details']
    actions: list[Action] = []
    for item in data['items']:
        match item['type']:
            case 'action':
                actions.append(_read_simple_action(item))
            case 'melee':
                actions.append(_read_strike(item))
            case _ as unknown:
                print(f"Ignored item {item['name']} with type {unknown}",
                      file=sys.stderr)
    attributes = data['system']['attributes']
    return PF2Hazard(
        name=data['name'],
        level=details['level']['value'],
        complex=details['isComplex'],
        stealth=data['system']['attributes']['stealth']['value'],
        disable=enrich(details['disable']),
        ac=attributes['ac']['value'],
        saves={k: v['value'] for k, v in data['system']['saves'].items()},
        hp=attributes['hp']['value'],
        hardness=attributes['hardness'],
        routine=enrich(details['routine']),
        actions=actions,
        reset=enrich(details['reset']),
    )


def _read_simple_action(item):
    match item['system']['actionType']['value']:
        case 'action':
            cost = item['system']['actions']['value']
        case 'reaction':
            cost = 'reaction'
        case str():
            cost = 0
        case unknown:
            raise ValueError(f'Unknown action type {unknown}')
    return SimpleAction(item['name'], enrich(item['system']['description']['value']), cost,
                        item['system']['traits']['value'])


def _read_strike(item):
    def damage(data):
        damage_type = data['damageType']
        damage_category = data.get('category')
        if damage_category:
            damage_type = f'{damage_category} {damage_type}'
        return data['damage'], damage_type
    return Strike(
        item['name'],
        item['system']['weaponType']['value'],
        item['system']['bonus']['value'],
        [damage(data) for data in item['system']['damageRolls'].values()],
        traits=item['system']['traits']['value'],
        effects=item['system']['attackEffects']['value']
            if 'attackEffects' in item['system'] else []
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
