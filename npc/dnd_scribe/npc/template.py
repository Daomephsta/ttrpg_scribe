import inspect
from random import Random
from random import _inst as default_random
from typing import Any

from dnd_scribe.npc import Entity, Feature


class Template:
    feature_order: list[Feature[Any]]
    feature_values: dict[Feature[Any], Any]

    def __init__(self, *features: tuple[Feature[Any], Any] | Feature[Any]):
        self.feature_order = []
        self.feature_values = {}
        for entry in features:
            match entry:
                case (feature, value):
                    self.feature_order.append(feature)
                    self.feature_values[feature] = value
                case Feature():
                    self.feature_order.append(entry)
                    self.feature_values[entry] = None
                case _:
                    raise ValueError(f'Unexpected value {entry} ({type(entry)})')

    def into_entity(self, rng: Random=default_random) -> Entity:
        return Entity.new(self.feature_order,
            {feature: value() if inspect.isfunction(value) else value
                for feature, value in self.feature_values.items()}, rng)