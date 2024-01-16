from functools import reduce
from importlib import resources
from random import Random
from random import _inst as default_random
from typing import Any, Callable, Mapping, Optional, Sequence, cast, overload

import flask
import yaml

import ttrpg_scribe.npc.race
from ttrpg_scribe.npc.character import ABILITIES, SEXES, Ability, Sex
from ttrpg_scribe.npc.race import Race, Subrace


class Feature[T]:
    def __init__(self, name: str,
                 generator: Callable[['EntityGenerator', 'FeatureMapping'], T],
                 dependencies: 'list[Feature[Any] | str]' = [],
                 display: str | None = None,
                 to_str: 'Callable[[T], str]' = lambda value: str(value),
                 from_str: 'Callable[[str, FeatureMapping], T]' =
                    lambda value, _: cast(T, value)
                 ) -> None:
        self.name = name
        self.generator = generator
        self.dependencies = dependencies
        self.to_str = to_str
        self.from_str = from_str
        self.display = display if display else name.title()

    def generate_into(self, entity_generator: 'EntityGenerator',
                      features: 'FeatureMap'):
        for dependency in self.dependencies:
            if dependency in features:
                continue
            if isinstance(dependency, str):
                dependency = Features[dependency]
            dependency.generate_into(entity_generator, features)
        features[self] = self.generator(entity_generator, features)

    def read_into(self, destination: 'FeatureMap',
                  value: str | None) -> 'FeatureMap':
        if value:
            destination[self] = self.from_str(value, destination)
        else:
            destination[self] = None
        return destination

    @staticmethod
    def choice(name: str, choices: list[T], *, weights: list[float] = [],
           filter: Optional[Callable[['FeatureMapping', T], bool]] = None,
           display: str | None = None) -> 'Feature[T]':
        if weights:
            def generator(helper: 'EntityGenerator', _):
                return helper.choose(choices, weights=weights)
        elif filter:
            def generator(helper: 'EntityGenerator', dependencies):  # type: ignore
                def dependent_filter(option):
                    return filter(dependencies, option)
                return helper.choose(choices, filter=dependent_filter)
        else:
            def generator(helper: 'EntityGenerator', _):
                return helper.choose(choices)
        return Feature(name, generator=generator, display=display)

    @staticmethod
    def from_yaml(yaml, name: str, display=None):
        return Feature.choice(name, yaml[name], display=display)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__


FeatureMapping = Mapping[Feature[Any], Any]
FeatureMap = dict[Feature[Any], Any]


def different(feature_name: str):
    def filter(npc: FeatureMapping, choice) -> bool:
        return choice != npc.get(Features[feature_name])
    return filter


class __Features(type):
    def __init__(cls, *_):
        with resources.open_text('ttrpg_scribe.npc', 'features.yaml') as file:
            features_yaml = yaml.safe_load(file)
        cls.REGION: Feature[str] = Feature('region',
            lambda generator, _: generator.choose(list(generator.config['REGIONS'].keys())))

        def race(generator: 'EntityGenerator',
                          features: FeatureMapping) -> Race:
            region: str = features[Features.REGION]
            region_race_weights: dict[Race, dict[str, int] | int] =\
                generator.config['REGIONS'][region]['races']
            races = list(region_race_weights.keys())
            race_weights = [sum(weights.values()) if isinstance(weights, dict) else weights
                for weights in region_race_weights.values()]
            return generator.choose(races, weights=race_weights)
        cls.RACE: Feature[Race] = Feature('race', race,
            from_str=lambda s, _: ttrpg_scribe.npc.race.BY_NAME[s],
            dependencies=[cls.REGION])

        def subrace(generator: 'EntityGenerator',
                    features: FeatureMapping) -> Subrace | None:
            region: str = features[Features.REGION]
            region_race_weights: dict[Race, dict[str, int] | int] =\
                generator.config['REGIONS'][region]['races']
            race: Race = features[Features.RACE]
            if race.subraces:
                match region_race_weights[race]:
                    case dict() as subrace_weights:
                        subraces = [race.subraces[name] for name in subrace_weights.keys()]
                        return generator.choose(subraces, weights=list(subrace_weights.values()))
                    case int() | float() as race_weight:
                        return generator.choose(list(race.subraces.values()),
                            weights=[race_weight / len(race.subraces)] * len(race.subraces))
            return None
        cls.SUBRACE = Feature('subrace', subrace,
            from_str=lambda s, features:
                features[cls.RACE].subraces[s] if s != 'None' else None,
            dependencies=[cls.REGION, cls.RACE])

        def culture(generator: 'EntityGenerator', features: FeatureMapping) -> 'Culture':
            region: str = features[Features.REGION]
            region_cultures: dict[str, int] = generator.config['REGIONS'][region]['cultures']
            culture_name = generator.choose(
                list(region_cultures.keys()),
                weights=list(region_cultures.values()))
            return Culture.from_config(generator.config, culture_name)
        cls.CULTURE: Feature[Culture] = Feature('culture', culture,
            from_str=lambda s, _: Culture.from_config(flask.current_app.config, s),
            dependencies=[cls.REGION])

        cls.SEX: Feature[Sex] = Feature.choice('sex', SEXES)
        cls.AGE: Feature[str] = Feature.choice('age',
            # Age distribution is more or less uniform, only decreasing for old ages
            ['Young Adult', 'Middle Aged', 'Old'], weights=[3, 3, 1])
        cls.NAME: Feature[str] = Feature('name',
            lambda helper, features: features[cls.CULTURE].namer.name(features, helper.rng),
            dependencies=[cls.CULTURE, cls.SEX, cls.AGE, cls.RACE])
        cls.HEIGHT: Feature[str] = Feature.choice('height',
            # 68% of values in a normal distribution are within 1 standard deviation of the mean
            ['Short', 'Average', 'Tall'], weights=[0.16, 0.68, 0.16])
        cls.WEIGHT: Feature[str] = Feature.choice('weight',
            # 68% of values in a normal distribution are within 1 standard deviation of the mean
            ['Light', 'Average', 'Heavy'], weights=[0.16, 0.68, 0.16])
        cls.HIGH_STAT: Feature[Ability] = Feature.choice('high_stat',
            ABILITIES, filter=different('low_stat'), display='High')
        cls.LOW_STAT: Feature[Ability] = Feature.choice('low_stat',
            ABILITIES, filter=different('high_stat'), display='Low')
        cls.APPEARANCE: Feature[str] = Feature.from_yaml(features_yaml, 'appearance')
        cls.POSITIVE_PERSONALITY: Feature[str] = Feature.from_yaml(features_yaml,
            'positive_personality', display='Positive Personality')
        cls.NEGATIVE_PERSONALITY: Feature[str] = Feature.from_yaml(features_yaml,
            'negative_personality', display='Negative Personality')
        cls.MANNERISM: Feature[str] = Feature.from_yaml(features_yaml, 'mannerism')
        cls._BY_NAME = {value.name: value for value in vars(cls).values()
            if isinstance(value, Feature)}

    def __getitem__(cls, index: str) -> Feature[Any]:
        return cls._BY_NAME[index]

    def __iter__(cls):
        return iter(cls._BY_NAME)

    def __contains__(cls, key: str):
        return key in cls._BY_NAME


class Features(metaclass=__Features):
    pass


class Entity:
    def __init__(self, feature_values: FeatureMap):
        self.feature_values = FeatureMap(feature_values)

    @property
    def name(self):
        return self[Features.NAME]

    def __setitem__[T](self, key: Feature[T], value: T):
        self.feature_values[key] = value

    def __getitem__[T](self, key: Feature[T]) -> T:
        return self.feature_values[key]

    def __iter__(self):
        return iter(self.feature_values.items())

    def to_dict[K, V](
            self, order: list[Feature[Any]] = [],
            exclude: list[Feature[Any]] = [],
            key_mapper: Callable[[Feature[Any]], K] = lambda k: k,
            value_mapper: Callable[[Feature[Any], Any], V] = lambda k, v: v
            ) -> dict[K, V]:
        # Find features with no specified order and put them last
        last = list(self.feature_values.keys() - set(order))
        order = order + last
        return {key_mapper(feature): value_mapper(feature, self[feature])
                for feature in order
                if feature not in exclude}

    def to_json(self) -> dict[str, str]:
        return {feature.name: feature.to_str(value) for feature, value in self}

    def __getstate__(self) -> dict[str, str]:
        return self.to_json()

    def __setstate__(self, state: dict[str, str]):
        self.feature_values = reduce(lambda features, feature:
                Features[feature[0]].read_into(features, feature[1]),
            state.items(), {})

    def for_display(self, order: list[Feature[Any]] = [],
                    exclude: list[Feature[Any]] = []):
        return list(self.to_dict(order, exclude,
                                 key_mapper=lambda f: f.display,
                                 value_mapper=lambda f, v: f.to_str(v)
                                 ).items())

    def __str__(self) -> str:
        return f'Entity{self.feature_values}'


class EntityGenerator:
    def __init__(self, *, rng=default_random, config: dict[str, Any]) -> None:
        self.rng = rng
        self.config = config

    @overload
    def choose[C](self, options: list[C], *,
               filter: Callable[[C], bool] | None = None) -> C: ...

    @overload
    def choose[C](self, options: list[C], *,
               weights: Sequence[float] | None = None) -> C: ...

    @overload
    def choose[C](self, options: list[C], *,
               weights: Sequence[float] | None = None, k: int) -> list[C]: ...

    @overload
    def choose[C](self, options: list[C], *,
               filter: Callable[[C], bool] | None = None, k: int) -> list[C]: ...

    def choose[C](self, options: list[C], *, weights: Sequence[float] | None = None,
               filter: Callable[[C], bool] | None = None, k=1) -> list[C] | C:
        if filter:
            weights = [int(filter(option)) for option in options]
        if k == 1:
            if weights is not None:
                return self.rng.choices(options, weights)[0]
            return self.rng.choice(options)
        return self.rng.choices(options, weights, k=k)

    def generate(self, features: FeatureMap) -> Entity:
        # Initialise feature values from overrides
        feature_values = {f: v for f, v in features.items() if v is not None}
        # Generate remaining features afterwards
        for feature in features:
            if feature in feature_values:
                continue
            feature.generate_into(self, feature_values)
        return Entity(feature_values)


class Namer:
    def name(self, features: FeatureMapping, rng: Random) -> str:
        raise NotImplementedError()


class FormattedNamer(Namer):
    Format = list[str | list[str]]

    def __init__(self, format: Format, names: Mapping[str, list[str]]):
        self.format = format
        self.names = names

    def name(self, features: FeatureMapping, rng: Random) -> str:
        def part_type(part: str | list[str]) -> str:
            match part:
                case 'Gender':
                    return features[Features.SEX]
                case str():
                    return part
                case list():
                    return part_type(rng.choice(part))
        return ' '.join(rng.choice(self.names[part_type(part)])
            for part in self.format)


class Culture:
    BY_NAME: dict[str, 'Culture'] = {}

    def __init__(self, name: str, namer: Namer) -> None:
        self.name = name
        self.namer = namer
        Culture.BY_NAME[name] = self

    @staticmethod
    def from_config(config: dict[str, Any], culture_name: str):
        if culture_name in Culture.BY_NAME:
            return Culture.BY_NAME[culture_name]
        culture_args = config['CULTURES'][culture_name]
        return Culture(culture_name, culture_args)

    def __str__(self) -> str:
        return self.name
