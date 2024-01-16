import json
from typing import Any

from ttrpg_scribe.pf2e_compendium.foundry import packs

type Json = dict[str, Any]

_translations = {}


def _initialise():
    with packs.open_pf2e_file('static/lang/en.json') as file:
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
