import logging
import operator
import re
from abc import ABCMeta, abstractmethod
from functools import cache
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable, Never

import flask
from requests import Session
from requests_cache import CachedSession

from dnd_scribe.bestiary.creature import Creature
from dnd_scribe.bestiary.creature.ability import Ability, Skill
from dnd_scribe.bestiary.creature.armour import ArmourClass
from dnd_scribe.bestiary.creature.movement import Movement
from dnd_scribe.bestiary.creature.sense import Sense
from dnd_scribe.core import signals

type ErrorHandler[T] = Callable[[Exception], T]
type Template = Callable[[Creature], None]


@cache
def cache_dir():
    if flask.current_app:
        return Path(flask.current_app.instance_path)/'_build/cache'
    else:
        return Path.cwd()/'_build/cache'


class Api[T](metaclass=ABCMeta):
    def __init__(self, error_handler: ErrorHandler[T]) -> None:
        self.error_handler = error_handler

    @abstractmethod
    def creature(self, index: str) -> Creature | T:
        raise NotImplementedError


class HttpApi[T](Api[T], metaclass=ABCMeta):
    base_url: str
    __session: Session | None = None

    def __init__(self, error_handler: Callable[[Exception], T]) -> None:
        super().__init__(error_handler)

        def clean(sender):
            self.session().close()
            self.__session = None
        self.__clean = clean
        signals.clean.connect(self.__clean)

    def __del__(self):
        signals.clean.disconnect(self.__clean)

    def session(self) -> Session:
        if not self.__session:
            host_start = self.base_url.find('://') + 1
            cache_name = re.sub(r'\W', '_', self.base_url[host_start:])
            self.__session = CachedSession((cache_dir()/cache_name).as_posix())
        return self.__session

    def creature(self, index: str) -> Creature | T:
        url = self.base_url + index
        logging.debug('GET %s', url)
        try:
            response = self.session().get(url, verify=True)
        except Exception as ex:
            return self.error_handler(ex)
        if response.status_code != HTTPStatus.OK:
            return self.error_handler(
                KeyError(f'{url} returned {response.status_code} {response.reason}',
                         response.status_code))
        data = response.json()

        try:
            return Creature(**self._parse_creature_data(data))
        except Exception as ex:
            ex.add_note(str(data))
            return self.error_handler(ex)

    @abstractmethod
    def _parse_creature_data(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class Dnd5eApi[T](HttpApi[T]):
    base_url = 'https://www.dnd5eapi.co/api/monsters/'

    def _parse_creature_data(self, data: dict[str, Any]) -> dict[str, Any]:
        skills = []
        saves = []
        for prof in data['proficiencies']:
            prof_id = prof['proficiency']['index']
            if prof_id.startswith('skill-'):
                prof_id = prof_id.removeprefix('skill-')
                skills.append((Skill.BY_ID[prof_id], prof['value']))
            if prof_id.startswith('saving-throw-'):
                prof_id = prof_id.removeprefix('saving-throw-')
                saves.append(Ability.BY_ID[prof_id])

        senses = [Sense.parse(name.title(), amount)
            for name, amount in data['senses'].items()
            if not name == 'passive_perception']
        traits = [(trait['name'], trait['desc'])
            for trait in data['special_abilities']]
        actions = [(action['name'], action['desc'])
            for action in data['actions']]

        def parse_ac(ac_data: dict[str, Any]) -> ArmourClass:
            value = ac_data['value']
            match ac_data['type']:
                case 'dex':
                    desc = ac_data.get('desc', '{ac:d}')
                case 'natural':
                    desc = ac_data.get('desc', '{ac:d} (Natural Armor)')
                case 'armor':
                    if 'desc' in ac_data:
                        desc = ac_data['desc']
                    armor = ', '.join(armor['name'] for armor in ac_data['armor'])
                    desc = f'{{ac:d}} ({armor})'
                case ('condition' | 'spell') as type:
                    condition = ac_data[type]['name']
                    desc = ac_data.get('desc', f'{{ac:d}} ({condition})')
                case type:
                    raise ValueError(f'Unknown AC type {type}')
            return ArmourClass(value, desc)

        return {
            'name': data['name'].lower(),
            'size': data['size'],
            'type': data['type'],
            'alignment': data['alignment'],
            'ac': [parse_ac(ac_data) for ac_data in data['armor_class']],
            'hp': tuple(map(int, data['hit_dice'].split('d'))),
            'default_hp': Creature.mean_hp,
            'speeds': Movement.from_dict(data['speed'],
                lambda v: int(v.removesuffix(' ft.'))),
            'statistics': operator.itemgetter('strength', 'dexterity',
                'constitution', 'intelligence', 'wisdom', 'charisma')(data),
            'cr': data['challenge_rating'],
            'saves': saves,
            'skill_profs': skills,
            'vulnerabilities': [x.title() for x in data['damage_vulnerabilities']],
            'resistances': [x.title() for x in data['damage_resistances']],
            'immunities': [x.title() for x in data['damage_immunities']] +
                [x['name'] for x in data['condition_immunities']],
            'senses': senses,
            'languages': data['languages'].split(', ')
                if data['languages'] else [],
            'traits': traits,
            'actions': actions
        }


def return_error(ex: Exception) -> Exception:
    return ex


def raise_error(ex: Exception) -> Never:
    raise ex


# For use by helper scripts
DND5EAPI = Dnd5eApi(raise_error)
