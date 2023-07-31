import inspect
from random import Random
from random import _inst as default_random
from typing import Any, Self

from dnd_scribe.npc import Entity, Feature


class Template:
    def __init__(self, feature_order: list[Feature[Any]],
                 feature_values: dict[Feature[Any], Any]):
        self.feature_order = feature_order
        self.feature_values = feature_values

    @classmethod
    def from_features(cls, *features: Feature[Any]) -> Self:
        return cls(list(features), dict.fromkeys(features, None))

    @classmethod
    def from_entries(cls, *entries: tuple[Feature[Any], Any] | Feature[Any]) -> Self:
        feature_order = []
        feature_values = {}
        for entry in entries:
            match entry:
                case (feature, value):
                    feature_order.append(feature)
                    feature_values[feature] = value
                case Feature():
                    feature_order.append(entry)
                    feature_values[entry] = None
                case _:
                    raise ValueError(f'Unexpected value {entry} ({type(entry)})')
        return cls(feature_order, feature_values)

    def into_entity(self, rng: Random=default_random) -> Entity:
        return Entity.new(self.feature_order,
            {feature: value() if inspect.isfunction(value) else value
                for feature, value in self.feature_values.items()}, rng)