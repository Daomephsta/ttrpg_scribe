from collections.abc import Set
from typing import overload


class Args:
    keyed: dict[str, str] = {}
    __match_args__ = ('positional', 'keyed')

    def __init__(self, raw: str, *, arg_sep: str, key_value_sep: str, error_context: str) -> None:
        self.raw = raw
        self.error_context = error_context
        self.keyed = {}
        for arg in raw.split(arg_sep):
            match arg.split(key_value_sep, maxsplit=1):
                case [key, value]:
                    self.keyed[key] = value
                case [arg]:
                    self.keyed[arg] = arg
        self.position_keys = {p: k for p, k in enumerate(self.keyed)}

    def consume_bool(self, key: str, default=False) -> bool:
        value = self.keyed.pop(key, default)
        return value == 'true' or self.__is_positional(key, value)

    def consume_str(self, key: str, default=None) -> str | None:
        return self.keyed.pop(key, default)

    def ignore(self, *keys: str):
        for key in keys:
            self.consume_str(key)

    __sentinel = object()

    @overload
    def consume_index(self, index: int) -> str:
        ...

    @overload
    def consume_index(self, index: int, default: str | None | object = __sentinel) -> str | None:
        ...

    def consume_index(self, index: int, default: str | None | object = __sentinel) -> str | None:
        if default == Args.__sentinel:
            return self.keyed.pop(self.position_keys[index])
        elif key := self.position_keys.get(index):
            assert isinstance(default, str) or default is None
            return self.keyed.pop(key, default)
        return None

    def consume_positional(self):
        for key in self.position_keys.values():
            yield self.keyed.pop(key)

    def consume_set(self, key: str, default: Set[str] = frozenset()) -> Set[str]:
        if value := self.consume_str(key):
            return {e.strip() for e in value.split(',')}
        return default

    def assert_consumed(self):
        keyed = []
        positional = []
        for k, v in self.keyed.items():
            if self.__is_positional(k, v):
                positional.append(k)
            else:
                keyed.append(k)
        assert len(keyed) == 0, f'Unconsumed keys {keyed}'
        assert len(positional) == 0, f'Unconsumed arguments {positional}'

    def __is_positional(self, key, value):
        return key == value

    def __enter__(self):
        return self

    def __exit__(self, e_type: type[Exception] | None, e_value: Exception | None, traceback):
        def notes(e: Exception):
            e.add_note(f'context={self.error_context}')
            e.add_note(f'args={self.raw}')
        if e_value is None:
            try:
                self.assert_consumed()
            except Exception as e:
                notes(e)
                raise
        else:
            notes(e_value)
        return False

    def __str__(self):
        args = ', '.join(k if self.__is_positional(k, v) else f'{k}={v}'
                         for k, v in self.keyed.items())
        return f'Args({args})'
