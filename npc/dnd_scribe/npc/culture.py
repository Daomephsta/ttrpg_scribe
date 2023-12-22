from random import Random
from typing import Any, Mapping

from dnd_scribe.npc.character import Sex


class Namer:
    def name(self, sex: Sex, rng: Random) -> str:
        raise NotImplementedError()


class FormattedNamer(Namer):
    Format = list[str | list[str]]

    def __init__(self, format: Format, names: Mapping[str, list[str]]):
        self.format = format
        self.names = names

    def name(self, sex: Sex, rng: Random) -> str:
        def part_type(part: str | list[str]) -> str:
            match part:
                case 'Gender':
                    return sex
                case str():
                    return part
                case list():
                    return part_type(rng.choice(part))
        return ' '.join(rng.choice(self.names[part_type(part)])
            for part in self.format)


_BY_NAME: dict[str, 'Culture'] = {}


class Culture:
    def __init__(self, name: str, namer: Namer) -> None:
        self.name = name
        self.namer = namer
        _BY_NAME[name] = self

    @staticmethod
    def from_config(config: dict[str, Any], culture_name: str):
        if culture_name in _BY_NAME:
            return _BY_NAME[culture_name]
        culture_args = config['CULTURES'][culture_name]
        return Culture(culture_name, culture_args)

    def __str__(self) -> str:
        return self.name
