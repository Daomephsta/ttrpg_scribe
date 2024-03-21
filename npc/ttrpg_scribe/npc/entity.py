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
                 generator: Callable[['EntityBuilder'], T],
                 display: str | None = None,
                 to_str: 'Callable[[T], str]' = lambda value: str(value),
                 from_str: 'Callable[[str, dict[Feature[Any], Any]], T]' =
                    lambda value, _: cast(T, value)
                 ) -> None:
        self.name = name
        self.generator = generator
        self.to_str = to_str
        self.from_str = from_str
        self.display = display if display else name.title()

    def generate_into(self, builder: 'EntityBuilder'):
        builder[self] = self.generator(builder)

    def read_into(self, destination: 'dict[Feature[Any], Any]',
                  value: str | None):
        if value:
            destination[self] = self.from_str(value, destination)
        else:
            destination[self] = None

    @staticmethod
    def choice(name: str, choices: list[T], *, weights: list[float] = [],
           filter: Optional[Callable[['EntityBuilder', T], bool]] = None,
           display: str | None = None) -> 'Feature[T]':
        if weights:
            def generator(builder: EntityBuilder):
                return builder.choose(choices, weights=weights)
        elif filter:
            def generator(builder: EntityBuilder) -> T:
                def dependent_filter(option):
                    return filter(builder, option)
                match builder.choose(choices, filter=dependent_filter):
                    case None:
                        raise RuntimeError(f'All values for {name} were filtered')
                    case some:
                        return some
        else:
            def generator(builder: EntityBuilder):
                return builder.choose(choices)
        return Feature(name, generator=generator, display=display)

    @staticmethod
    def from_yaml(yaml, name: str, display=None):
        return Feature.choice(name, yaml[name], display=display)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__


class EntityBuilder:
    features: dict[Feature[Any], Any]
    context: 'EntityGenerator'

    def __init__(self, context: 'EntityGenerator') -> None:
        self.features = {}
        self.context = context

    def __getitem__[F](self, feature: Feature[F]) -> F:
        if self.get(feature) is None:
            feature.generate_into(self)
        return self.features[feature]

    def get[F](self, feature: Feature[F]) -> F | None:
        return self.features.get(feature)

    def __setitem__[F](self, feature: Feature[F], value: F | None):
        self.features[feature] = value

    @overload
    def choose[C](self, options: Sequence[C]) -> C: ...

    @overload
    def choose[C](self, options: Sequence[C], *,
               filter: Callable[[C], bool] | None = None) -> C | None: ...

    @overload
    def choose[C](self, options: Sequence[C], *,
               weights: Sequence[float] | None = None) -> C: ...

    @overload
    def choose[C](self, options: Sequence[C], *,
               weights: Sequence[float] | None = None, k: int) -> list[C]: ...

    @overload
    def choose[C](self, options: Sequence[C], *,
               filter: Callable[[C], bool] | None = None, k: int) -> list[C]: ...

    def choose[C](self, options: Sequence[C], *, weights: Sequence[float] | None = None,
               filter: Callable[[C], bool] | None = None, k=1) -> list[C] | C | None:
        if filter:
            weights = [int(filter(option)) for option in options]
            if sum(weights) == 0:  # Abort if all options filtered
                return None if k == 1 else []
        if k == 1:
            if weights is not None:
                return self.context.rng.choices(options, weights)[0]
            return self.context.rng.choice(options)
        return self.context.rng.choices(options, weights, k=k)


def different(feature_name: str):
    def filter(npc: EntityBuilder, choice) -> bool:
        return choice != npc.get(Features[feature_name])
    return filter


class __Features(type):
    def __init__(cls, *_):
        with resources.open_text('ttrpg_scribe.npc', 'features.yaml') as file:
            features_yaml = yaml.safe_load(file)
        cls.REGION: Feature[str] = Feature('region',
            lambda builder: builder.choose(list(builder.context.config['REGIONS'].keys())))

        def race(builder: EntityBuilder) -> Race:
            culture = builder[Features.CULTURE]
            races = list(culture.races.keys())
            race_weights = [sum(weights.values()) if isinstance(weights, dict) else weights
                for weights in culture.races.values()]
            return builder.choose(races, weights=race_weights)
        cls.RACE: Feature[Race] = Feature('race', race,
            from_str=lambda s, _: ttrpg_scribe.npc.race.BY_NAME[s])

        def subrace(builder: EntityBuilder) -> Subrace | None:
            culture = builder[Features.CULTURE]
            race: Race = builder[Features.RACE]
            if race.subraces:
                match culture.races[race]:
                    case dict() as subrace_weights:
                        subraces = [race.subraces[name] for name in subrace_weights.keys()]
                        return builder.choose(subraces,
                                                      weights=list(subrace_weights.values()))
                    case int() | float() as race_weight:
                        return builder.choose(list(race.subraces.values()),
                            weights=[race_weight / len(race.subraces)] * len(race.subraces))
            return None
        cls.SUBRACE = Feature('subrace', subrace,
            from_str=lambda s, features:
                features[cls.RACE].subraces[s] if s != 'None' else None)

        def culture(builder: EntityBuilder) -> 'Culture':
            region: str = builder[Features.REGION]
            region_cultures: dict[str, int] = builder.context.config['REGIONS'][region]['cultures']
            culture_name = builder.choose(
                list(region_cultures.keys()),
                weights=list(region_cultures.values()))
            return Culture.from_config(builder.context.config, culture_name)
        cls.CULTURE: Feature[Culture] = Feature('culture', culture,
            from_str=lambda s, _: Culture.from_config(flask.current_app.config, s))

        cls.SEX: Feature[Sex] = Feature.choice('sex', SEXES)
        cls.AGE: Feature[str] = Feature.choice('age',
            # Age distribution is more or less uniform, only decreasing for old ages
            ['Young Adult', 'Middle Aged', 'Old'], weights=[3, 3, 1])
        cls.NAME: Feature[str] = Feature('name',
            lambda builder: builder[cls.CULTURE].namer.name(builder, builder.context.rng))
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

    def register(cls, feature: Feature) -> Feature:
        cls._BY_NAME[feature.name] = feature
        return feature


class Features(metaclass=__Features):
    pass


class Entity:
    feature_values: dict[Feature[Any], Any]

    def __init__(self, builder: EntityBuilder):
        self.feature_values = builder.features

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
        self.feature_values = {}
        for k, v in state.items():
            Features[k].read_into(self.feature_values, v)

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

    def generate(self, builder: EntityBuilder) -> Entity:
        # Initialise feature values from overrides
        feature_values = {f: v for f, v in builder.features.items() if v is not None}
        region_config = self.config['REGIONS'][builder[Features.REGION]]
        for feature in region_config.get('extra_features', []):
            builder[feature] = None
        # Generate remaining features afterwards
        for feature in builder.features:
            if feature in feature_values:
                continue
            feature.generate_into(builder)
        return Entity(builder)


class Namer:
    def name(self, builder: EntityBuilder, rng: Random) -> str:
        raise NotImplementedError()


class FormattedNamer(Namer):
    Format = list[str | list[str]]

    def __init__(self, format: Format, names: Mapping[str, list[str]]):
        self.format = format
        self.names = names

    def name(self, builder: EntityBuilder, rng: Random) -> str:
        def part_type(part: str | list[str]) -> str:
            match part:
                case 'Gender':
                    return builder[Features.SEX]
                case str():
                    return part
                case list():
                    return part_type(rng.choice(part))
        return ' '.join(rng.choice(self.names[part_type(part)])
            for part in self.format)


class Culture:
    BY_NAME: dict[str, 'Culture'] = {}

    def __init__(self, name: str, namer: Namer,
                 races: dict[Race, dict[str, int] | int]) -> None:
        self.name = name
        self.namer = namer
        self.races = races
        Culture.BY_NAME[name] = self

    @staticmethod
    def from_config(config: dict[str, Any], culture_name: str):
        if culture_name in Culture.BY_NAME:
            return Culture.BY_NAME[culture_name]
        culture_args: dict[str, Any] = config['CULTURES'][culture_name]
        return Culture(culture_name, culture_args['namer'], culture_args['races'])

    def __str__(self) -> str:
        return self.name
