import json
from typing import Any

from pf2e_bestiary.dnd_scribe.pf2e_bestiary import foundry

type Json = dict[str, Any]

_translations = {}


def _initialise():
    with foundry.pf2e_pack_open('static/lang/en.json') as file:
        def visit(obj: Json, path: list[str]):
            for k, v in obj.items():
                match v:
                    case str():
                        _translations['.'.join(path + [k])] = v
                    case dict():
                        visit(v, path + [k])

        visit(json.load(file), [])


def translate(key: str):
    if not _translations:
        _initialise()
    return _translations.get(key, key)
