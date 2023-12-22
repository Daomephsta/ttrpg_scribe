from typing import Any

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


class Race:
    name: str
    subraces: dict[str, Subrace]

    def __init__(self, name: str,
                 subraces: dict[str, dict[str, Any] | Subrace] = {}):
        self.name = name
        self.subraces = {subname:
            args if isinstance(args, Subrace) else Subrace(self, subname)
            for subname, args in subraces.items()}
        BY_NAME[name] = self

    def derive(self, **overrides) -> 'Race':
        return Race(name=self.name, subraces={**self.subraces})

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Race) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__
