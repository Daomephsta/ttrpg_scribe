import json
from typing import Any

from ttrpg_scribe.pf2e_compendium import foundry

type Json = dict[str, Any]

_translations = {}


def _initialise():
    with (foundry.pf2e_dir/'static/lang/en.json').open(encoding='utf8') as file:
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
