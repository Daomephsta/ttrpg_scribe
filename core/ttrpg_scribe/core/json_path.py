import itertools
import re
from typing import Any, overload

_or_sentinel = object()


class JsonPath:
    @overload
    def __init__(self, path: str) -> None: ...

    @overload
    def __init__(self, path: list[str | int]) -> None: ...

    def __init__(self, path: list[str | int] | str) -> None:
        match path:
            case str():
                if path.startswith('$.'):
                    path = path[2:]
                self.__path = [int(part[1]) if part.startswith('[') else part
                             for part in re.split(r'\.|(?=\[)', path)]
            case list():
                self.__path = path

    def __getattr__(self, key: str) -> 'JsonPath':
        return self[key]

    def __getitem__(self, key: str | int) -> 'JsonPath':
        return JsonPath(self.__path + [key])

    def __call__(self, json_obj: dict[str, Any], _or: Any = _or_sentinel) -> Any:
        json = json_obj
        for part in self.__path:
            match json, part:
                case dict(), str():
                    if part not in json and _or is not _or_sentinel:
                        return _or
                    json = json[part]
                case list(), int():
                    if part >= len(json) and _or is not _or_sentinel:
                        return _or
                    json = json[part]
                case _:
                    raise TypeError(f'Expected {str(self)} to be a dict or list')
        return json

    def __str__(self) -> str:
        def parts():
            for part in self.__path:
                match part:
                    case str():
                        yield f'.{part}'
                    case int():
                        yield f'[{part}]'
        return ''.join(itertools.chain('$', parts()))

    def __repr__(self) -> str:
        return f"JsonPath('{self}')"
