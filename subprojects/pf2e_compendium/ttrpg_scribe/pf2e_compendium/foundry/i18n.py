import json
from typing import Any, cast

from ttrpg_scribe.pf2e_compendium import foundry

type Json = dict[str, Any]

_translations = {}


def _initialise():
    def visit(obj: Json, path: list[str]):
        for k, v in obj.items():
            match v:
                case str():
                    _translations['.'.join(path + [k])] = v
                case dict():
                    visit(v, path + [k])

    for language in foundry.system_data('languages'):
        if language['lang'] != 'en':
            continue
        with (foundry.pf2e_dir/cast(str, language['path'])).open(encoding='utf8') as file:
            visit(json.load(file), [])


def translate(key: str):
    if not _translations:
        _initialise()
    return _translations.get(key, key)
