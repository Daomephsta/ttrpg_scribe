from typing import Any

from ttrpg_scribe.core.json_path import JsonPath

__SYSTEM = JsonPath('system')


class Flags(str):
    def __getitem__(self, key):
        match key:
            case str():
                return Flags(f'{self}.{key}')
            case _:
                return super().__getitem__(key)
        if isinstance(key, str):
            return Flags(f'{self}.{key}')
        else:
            return super().__getitem__(key)


def __common(data: dict[str, Any]):
    data['hardness'] = __SYSTEM.attributes.hardness(data, _or=0)


def actor(data: dict[str, Any]):
    __common(data)
    data['level'] = __SYSTEM.details.level.value(data, _or=None)
    data['traits'] = set(__SYSTEM.traits.value(data, _or=[]))
    data['size'] = __SYSTEM.traits.size.value(data, _or='med')
    data['flags'] = Flags('@actor.flags')
    return {'actor': data}


def item(data: dict[str, Any]):
    __common(data)
    data['flags'] = Flags('@item.flags')
    return {'item': data}
