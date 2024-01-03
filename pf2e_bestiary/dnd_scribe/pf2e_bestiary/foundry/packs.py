import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import flask

from dnd_scribe.pf2e_bestiary.creature import Melee, PF2Creature, SimpleAction
from dnd_scribe.pf2e_bestiary.foundry.enrich import enrich

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


def creature(id: str) -> PF2Creature:
    def from_json(data):
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

        if 'perception' in attributes:
            perception = attributes['perception']['value']
        else:
            perception = system['perception']['mod']

        if 'senses' in traits:
            senses = traits['senses']['value'].split(', ')
        else:
            senses = [sense['type'] for sense in system['perception']['senses']]

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
            speeds=dict(speeds),
            actions=actions
        )
    with open_pf2e_file(f'packs/{id}.json') as file:
        return from_json(json.load(file))
