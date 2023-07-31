from importlib import resources
from random import Random
from random import _inst as default_random
from typing import (Any, Callable, Generic, Iterable, Mapping, Optional, Self,
                    TypeVar, cast)

import flask
import yaml

from dnd_scribe.npc import race
from dnd_scribe.npc.character import ABILITIES, SEXES, Ability, Sex
from dnd_scribe.npc.race import Race, Subrace

T = TypeVar('T')

def choice(choices: Iterable[T],
        weights: list[float]=[],
        filter: Optional[Callable[['Entity', T], bool]]=None) -> Callable[['Entity', Random], T]:

        if weights and filter:
            raise ValueError('weights and filter are mutually exclusive')
        choices = list(choices)
        if weights:
            return lambda _, rng: rng.choices(choices, weights)[0]
        if filter:
            filter0: Callable[['Entity', T], bool] = filter
            return lambda npc, rng: rng.choices(choices,
                weights=[int(filter0(npc, c)) for c in choices])[0]
        return lambda _, rng: rng.choice(choices)

class Feature(Generic[T]):
    def __init__(self, name: str,
        generator: Callable[['Entity', Random], T],
        dependencies: 'list[Feature[Any] | str]'=[],
        display: str | None=None,
        to_str: 'Callable[[T], str]'=lambda value: str(value),
        from_str: 'Callable[[Mapping[Feature[Any], Any], str], T]'=
            lambda _, value: cast(T, value)
    ) -> None:

        self.name = name
        self.generator = generator
        self.dependencies = dependencies
        self.to_str = to_str
        self.from_str = from_str
        self.display = display if display else name.title()

    def read_into(self, destination: dict['Feature[Any]', Any],
                  value: str | None):
        if value:
            destination[self] = self.from_str(destination, value)
        else:
            destination[self] = None

    @staticmethod
    def from_yaml(yaml, name: str,
        dependencies: 'list[Feature[Any] | str]'=[],
        display=None,
        to_str: 'Callable[[T], str]'=
            lambda value: str(value)):
        return Feature(name, choice(yaml[name]),
            dependencies, display, to_str)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__

def _race(npc: 'Entity', rng: Random) -> Race:
    region_race_weights: dict[Race, int] =\
        flask.current_app.config['RACE_WEIGHTS'][npc[Features.REGION]]
    races = list(region_race_weights.keys())
    race_weights = [sum(weights.values()) if isinstance(weights, dict) else weights
        for weights in region_race_weights.values()]
    return rng.choices(races, race_weights)[0]

def _subrace(npc: 'Entity', rng: Random) -> Subrace | None:
    region_race_weights: dict[Race, int] =\
        flask.current_app.config['RACE_WEIGHTS'][npc[Features.REGION]]
    race = npc[Features.RACE]
    if race.subraces:
        subrace_weights = region_race_weights[race]
        if isinstance(subrace_weights, dict):
            subraces = [race.subraces[name] for name in subrace_weights.keys()]
            return rng.choices(subraces, list(subrace_weights.values()))[0]
        else:
            subrace_weights = [subrace_weights / len(race.subraces)
                for _ in race.subraces]
            [result] = rng.choices(list(race.subraces.values()), subrace_weights)
            return result
    return None

def different(feature_name: str):
    def filter(npc: 'Entity', choice) -> bool:
        return choice != npc.feature_values.get(Features[feature_name])
    return filter

class __Features(type):
    def __init__(cls, *_):
        with resources.open_text('dnd_scribe.npc', 'features.yaml') as file:
            features_yaml = yaml.safe_load(file)
        cls.REGION: Feature[str] = Feature('region', lambda *_: '')
        cls.RACE: Feature[Race] = Feature('race', _race,
            from_str=lambda _, s: race.BY_NAME[s],
            dependencies=[cls.REGION])
        cls.SUBRACE: Feature[Subrace | None] = Feature('subrace', _subrace,
            from_str=lambda npc, s: npc[cls.RACE].subraces[s],
            dependencies=[cls.RACE])
        cls.SEX: Feature[Sex] = Feature('sex', choice(SEXES))
        cls.NAME: Feature[str] = Feature('name',
            lambda npc, rng: npc[cls.RACE].gen_name(npc[cls.SEX], rng),
            dependencies=[cls.RACE, cls.SEX])
        cls.HEIGHT: Feature[str] = Feature('height',
            # 68% of values in a normal distribution are within 1 standard deviation of the mean
            choice(['Short', 'Average', 'Tall'], weights=[0.16, 0.68, 0.16]))
        cls.WEIGHT: Feature[str] = Feature('weight',
            # 68% of values in a normal distribution are within 1 standard deviation of the mean
            choice(['Light', 'Average', 'Heavy'], weights=[0.16, 0.68, 0.16]))
        cls.HIGH_STAT: Feature[Ability] = Feature('high_stat',
            choice(ABILITIES, filter=different('low_stat')), display='High')
        cls.LOW_STAT: Feature[Ability] = Feature('low_stat',
            choice(ABILITIES, filter=different('high_stat')), display='Low')
        cls.APPEARANCE: Feature[str] = Feature.from_yaml(features_yaml, 'appearance')
        cls.POSITIVE_PERSONALITY: Feature[str] = Feature.from_yaml(features_yaml,
            'positive_personality', display='Positive Personality')
        cls.NEGATIVE_PERSONALITY: Feature[str] = Feature.from_yaml(features_yaml,
            'negative_personality', display='Negative Personality')
        cls.MANNERISM: Feature[str] = Feature.from_yaml(features_yaml, 'mannerism')
        cls.AGE: Feature[str] = Feature('age',
            # Age distribution is more or less uniform, only decreasing for old ages
            choice(['Young Adult', 'Middle Aged', 'Old'], weights=[3, 3, 1]))
        cls._BY_NAME = {value.name: value for value in vars(cls).values()
            if isinstance(value, Feature)}

    def __getitem__(cls, index: str) -> Feature[Any]:
        return cls._BY_NAME[index]

    def __iter__(cls):
        return iter(cls._BY_NAME)

    def __contains__(cls, key: str):
        return key in cls._BY_NAME

class Features(metaclass=__Features): pass

class Entity:
    def __init__(self, feature_values: dict[Feature[Any], Any]):
        self.feature_values = feature_values

    @classmethod
    def new(cls, features: list[Feature[Any]],
            feature_values: dict[Feature[Any], Any] = {},
            rng: Random=default_random) -> Self:
        if not feature_values:
            feature_values = dict.fromkeys(features)
        entity = cls(feature_values)
        for feature in features:
            if not feature_values.get(feature):
                entity._generate_value(feature, rng)
        return entity

    def _generate_value(self, feature: Feature[Any], rng: Random):
        for dependency in feature.dependencies:
            if isinstance(dependency, str):
                dependency = Features[dependency]
            self._generate_value(dependency, rng)
        if not self.feature_values.get(feature):
            self.feature_values[feature] = feature.generator(self, rng)

    def __setitem__(self, key: Feature[T], value: T):
        self.feature_values[key] = value

    def __getitem__(self, key: Feature[T]) -> T:
        return self.feature_values[key]

    def __iter__(self):
        return iter(self.feature_values.items())

    def __str__(self) -> str:
        return str(self.feature_values)

    __repr__ = __str__
