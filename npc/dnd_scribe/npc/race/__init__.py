from random import Random
from typing import Any, Mapping, Self

from dnd_scribe.npc.character import Sex

BY_NAME: dict[str, 'Race'] = {}

class Subrace:
    def __init__(self, parent: 'Race', subname: str) -> None:
        self.parent = parent
        self.subname = subname

    @property
    def name(self):
        return f'{self.subname} {self.parent.name}'

    def __str__(self) -> str:
        return self.subname

    __repr__ = __str__

class Namer:
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
                    return rng.choice(part)
        return ' '.join(rng.choice(self.names[part_type(part)])
            for part in self.format)

class Race:
    name: str
    namer: Namer
    subraces: dict[str, Subrace]

    def __init__(self, name: str, format: Namer.Format,
                 names: Mapping[str, list[str]],
                 subraces: dict[str, dict[str, Any] | Subrace] = {}):
        self.name = name
        self.namer = Namer(format, names)
        self.subraces = {subname:
            args if isinstance(args, Subrace) else Subrace(self, subname)
            for subname, args in subraces.items()}
        BY_NAME[name] = self

    def derive(self, **overrides) -> Self:
        return Race(name=self.name, format=self.namer.format, names=self.namer.names, subraces={**self.subraces})

    def gen_name(self, sex: Sex, rng: Random) -> str:
        return self.namer.name(sex, rng)

    def names(self, kind: str) -> list[str]:
        return self.namer.names[kind]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Race) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__
