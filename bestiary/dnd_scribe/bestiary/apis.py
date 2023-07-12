from collections import namedtuple
from dataclasses import dataclass
import operator
from abc import ABCMeta, abstractmethod
from http import HTTPStatus
from typing import Any, Callable, ClassVar, Generic, Never, Self, TypeAlias, TypeVar

from requests import Session
from pathlib import Path
import platformdirs

from .creature import *
import shelve

T = TypeVar('T')
ErrorHandler: TypeAlias = Callable[[Exception], T]
Template: TypeAlias = Callable[[Creature], None]

api_sessions = []

class Api(Generic[T], metaclass=ABCMeta):
    def __init__(self, error_handler: ErrorHandler[T]) -> None:
        self.error_handler = error_handler

    @abstractmethod
    def creature(self, index: str) -> Creature | T:
        raise NotImplementedError

class HttpApi(Api[T], metaclass=ABCMeta):
    base_url: str

    __session = None
    def session(self) -> Session:
        if not self.__session:
            self.__session = Session()
            api_sessions.append(self.session)
        return self.__session

    def creature(self, index: str) -> Creature | T:
        url = self.base_url + index
        print(f'GET {url}')
        try:
            response = self.session().get(url, verify=True)
        except Exception as ex:
            return self.error_handler(ex)
        if response.status_code != HTTPStatus.OK:
            return self.error_handler(KeyError(f'{url} returned {response.status_code} {response.reason}', response.status_code))
        data = response.json()

        try:
            return Creature(**self._parse_creature_data(data))
        except Exception as ex:
            ex.add_note(str(data))
            return self.error_handler(ex)

    @abstractmethod
    def _parse_creature_data(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

class Dnd5eApi(HttpApi[T]):
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
        actions = [(action['name'],action['desc'])
            for action in data['actions']]

        def parse_ac(ac_data: dict[str, Any]) -> ArmourClass:
            value = ac_data['value']
            def desc() -> str:
                match ac_data['type']:
                    case 'dex':
                        return ac_data.get('desc', str(value))
                    case 'natural':
                        return ac_data.get('desc', f'{value} (Natural Armor)')
                    case 'armor':
                        if 'desc' in ac_data:
                            return ac_data['desc']
                        armor = ', '.join(armor['name'] for armor in ac_data['armor'])
                        return f'{value} ({armor})'
                    case ('condition' | 'spell') as type:
                        condition = ac_data[type]['name']
                        return ac_data.get('desc', f'{value} ({condition})')
                    case type:
                        raise ValueError(f'Unknown AC type {type}')
            return ArmourClass(value, desc())

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

U = TypeVar('U')

class Database(Api[T]):
    DATABASES = {Creature: 'creature'}

    def __init__(self, path: Path, error_handler: ErrorHandler):
        super().__init__(error_handler)
        path.mkdir(exist_ok=True)
        self.path = path

    def __cache(self, kind: type[U]) -> shelve.Shelf[U]:
        path = self.path/self.DATABASES[kind]
        return shelve.open(path.as_posix())

    CreatureFactory: TypeAlias = Callable[[str], Creature | Exception]

    def creature(self, index: str, 
                 factory: CreatureFactory | None = None) -> Creature | T:
        with self.__cache(Creature) as database:
            if index in database:
                return database[index]
            elif factory:
                match factory(index):
                    case Creature() as creature:
                        return creature
                    case Exception() as exception:
                        return self.error_handler(exception)
                return database[index]
        return self.error_handler(
            KeyError(f'No creature with id {index} in system database'))
    
    def insert(self, index: str, record: Creature):
        with self.__cache(type(record)) as database:
            if index in database:
                return self.error_handler(KeyError(f'{index} already exists'))
            else:
                database[index] = record
    
    def replace(self, index: str, record: Creature):
        with self.__cache(type(record)) as database:
            database[index] = record


def return_error(ex: Exception) -> Exception:
    return ex

def raise_error(ex: Exception) -> Never:
    raise ex

GLOBAL_DATABASE = Database(platformdirs.user_cache_path('dnd_scribe', 
        appauthor=False)/'bestiary', return_error)
DND5EAPI = Dnd5eApi(return_error)