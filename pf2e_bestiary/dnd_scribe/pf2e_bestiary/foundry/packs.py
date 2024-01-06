import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import flask

from dnd_scribe.pf2e_bestiary.actions import Action, SimpleAction, Strike
from dnd_scribe.pf2e_bestiary.creature import PF2Creature
from dnd_scribe.pf2e_bestiary.foundry.enrich import enrich
from dnd_scribe.pf2e_bestiary.hazard import PF2Hazard

type Json = dict[str, Any]
_pf2e_pack = None


def pf2e_dir() -> Path:
    global _pf2e_pack
    if _pf2e_pack is not None:
        return _pf2e_pack
    root = Path(flask.current_app.instance_path)\
        if flask.current_app else Path.cwd()
    _pf2e_pack = (root/'_build/pf2e_foundry').absolute()
    if not _pf2e_pack.exists():
        subprocess.run([
            'git', 'clone', '--depth', '1',
            'https://github.com/foundryvtt/pf2e',
            _pf2e_pack.as_posix()])
    return _pf2e_pack


def open_pf2e_file(path: str):
    return (pf2e_dir()/path).open(encoding='utf8')


def creature(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        return read_creature(json.load(file))


def read_creature(data: Json) -> PF2Creature:
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

    perception = system['perception']['mod']
    senses = [sense['type'] for sense in system['perception']['senses']]

    skills: list[tuple[str, int]] = []
    interactions: list[tuple[str, str]] = []
    defenses: list[tuple[str, str]] = []
    actions: list[Action] = []
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
                actions.append(Strike(
                    item['name'],
                    1,
                    item['system']['traits']['value'],
                    item['system']['weaponType']['value'],
                    item['system']['bonus']['value'],
                    [(v['damage'], v['damageType'])
                     for v in item['system']['damageRolls'].values()],
                    item['system']['attackEffects']['value']
                        if 'attackEffects' in item['system'] else []
                ))
            case _ as unknown:
                print(f"Ignored item {item['name']} with type {unknown}",
                      file=sys.stderr)
    return PF2Creature(
        name=data['name'],
        level=system['details']['level']['value'],
        alignments=alignments if alignments else ['neutral'],
        size=SIZES[traits['size']['value']],
        traits=simple_traits,
        perception=perception,
        senses=senses,
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
        speeds={'walk': attributes['speed']['value'],
              **{speed['type']: speed['value']
                for speed in attributes['speed']['otherSpeeds']}},
        actions=actions
    )


def hazard(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        return read_hazard(json.load(file))


def read_hazard(data: Json) -> PF2Hazard:
    details = data['system']['details']
    actions: list[Action] = []
    for item in data['items']:
        match item['type']:
            case 'action':
                name = item['name']
                desc = enrich(item['system']['description']['value'])
                cost = item['system']['actionType']['value']
                if cost == 'action':
                    cost = item['system']['actions']['value']
                elif cost is None:
                    cost = 0
                actions.append(SimpleAction(
                    name, cost,
                    item['system']['traits']['value'],
                    desc))
            case 'melee':
                actions.append(Strike(
                    item['name'],
                    1,
                    item['system']['traits']['value'],
                    item['system']['weaponType']['value'],
                    item['system']['bonus']['value'],
                    [(v['damage'], v['damageType'])
                     for v in item['system']['damageRolls'].values()],
                    item['system']['attackEffects']['value']
                        if 'attackEffects' in item['system'] else []
                ))
            case _ as unknown:
                print(f"Ignored item {item['name']} with type {unknown}",
                      file=sys.stderr)
    return PF2Hazard(
        name=data['name'],
        level=details['level']['value'],
        notice=data['system']['attributes']['stealth']['value'],
        disable=enrich(details['disable']),
        actions=actions,
        reset=enrich(details['reset']),
    )


def content(id: str):
    with open_pf2e_file(f'packs/{id}.json') as file:
        data: Json = json.load(file)
        type: str = data['type']
        match type:
            case 'npc':
                return ('creature', read_creature(data))
            case 'hazard':
                return (type, read_hazard(data))
            case _:
                print(f'Unknown content type {type}', file=sys.stderr)
                return (type, data)
