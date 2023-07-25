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
        display=None,
        to_str: 'Callable[[T], str]'=
            lambda value: str(value),
        from_str: 'Callable[[Mapping[Feature[Any], Any], str], T]'=
            lambda _, value: cast(T, value)
    ) -> None:

        self.name = name
        self.generator = generator
        self.dependencies = dependencies
        self.to_str = to_str
        self.from_str = from_str
        self.display = display if display else name.title()

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
            return rng.choices(list(race.subraces.values()), subrace_weights)[0]
    return None

def different(feature_name: str):
    def filter(npc: 'Entity', choice) -> bool:
        return choice != npc.feature_values.get(Features.BY_NAME[feature_name])
    return filter

class Features:
    with resources.open_text('dnd_scribe.npc', 'features.yaml') as file:
        __YAML = yaml.safe_load(file)
    REGION: Feature[str] = Feature('region', lambda *_: '')
    RACE: Feature[Race] = Feature('race', _race,
        from_str=lambda _, s: race.BY_NAME[s],
        dependencies=[REGION])
    SUBRACE: Feature[Subrace | None] = Feature('subrace', _subrace,
        from_str=lambda npc, s: npc[Features.RACE].subraces[s],
        dependencies=[RACE])
    def _sex(self, _entity, rng: Random) -> Sex:
        return rng.choice(['Male', 'Female'])
    SEX: Feature[Sex] = Feature('sex', choice(SEXES))
    NAME: Feature[str] = Feature('name',
        lambda npc, rng: npc[Features.RACE].gen_name(npc[Features.SEX], rng),
        dependencies=[RACE, SEX])
    HEIGHT: Feature[str] = Feature('height',
        # 68% of values in a normal distribution are within 1 standard deviation of the mean
        choice(['Short', 'Average', 'Tall'], weights=[0.16, 0.68, 0.16]))
    WEIGHT: Feature[str] = Feature('weight',
        # 68% of values in a normal distribution are within 1 standard deviation of the mean
        # 95% are within 2 standard deviations
        choice(['Thin', 'Average', 'Plump', 'Fat'],
        weights=[0.16, 0.68, 0.135, 0.025]))
    HIGH_STAT: Feature[Ability] = Feature('high_stat',
        choice(ABILITIES, filter=different('low_stat')), display='High')
    LOW_STAT: Feature[Ability] = Feature('low_stat',
        choice(ABILITIES, filter=different('high_stat')), display='Low')
    APPEARANCE: Feature[str] = Feature.from_yaml(__YAML, 'appearance')
    POSITIVE_PERSONALITY: Feature[str] = Feature.from_yaml(__YAML,
        'positive_personality', display='Positive Personality')
    NEGATIVE_PERSONALITY: Feature[str] = Feature.from_yaml(__YAML,
        'negative_personality', display='Negative Personality')
    MANNERISM: Feature[str] = Feature.from_yaml(__YAML, 'mannerism')
    AGE: Feature[str] = Feature('age',
        # Age distribution is more or less uniform, only decreasing for old ages
        choice(['Young Adult', 'Middle Aged', 'Old'], weights=[3, 3, 1]))
    BY_NAME = {value.name : value for _, value in locals().items() if isinstance(value, Feature)}

    @staticmethod
    def parse_ids(feature_ids: list[str]) -> list[Feature[Any]]:
        features = []
        for id in feature_ids:
            if not id in Features.BY_NAME:
                raise RuntimeError(f'Unknown feature {id}')
            else:
                features.append(Features.BY_NAME[id])
        return features

class Entity:
    feature_order: list[Feature[Any]]
    feature_values: dict[Feature[Any], Any]

    def __init__(self, feature_order: list[Feature[Any]], feature_values: dict[Feature[Any], Any]):
        self.feature_order = feature_order
        self.feature_values = feature_values

    @classmethod
    def new(cls, features: list[Feature[Any]],
        feature_values: dict[Feature[Any], Any] = {},
        rng: Random=default_random) -> Self:

        if not feature_values:
            feature_values = dict.fromkeys(features)
        entity = cls(features, feature_values)
        for feature in features:
            if not feature_values.get(feature):
                entity._generate_value(feature, rng)
        return entity

    def _generate_value(self, feature: Feature[Any], rng: Random):
        for dependency in feature.dependencies:
            if isinstance(dependency, str):
                dependency = Features.BY_NAME[dependency]
            self._generate_value(dependency, rng)
        if not self.feature_values.get(feature):
            self.feature_values[feature] = feature.generator(self, rng)

    def __setitem__(self, key: Feature[T], value: T):
        self.feature_values[key] = value

    def __getitem__(self, key: Feature[T]) -> T:
        return self.feature_values[key]

    def __str__(self) -> str:
        return str(self.feature_values)

    __repr__ = __str__
