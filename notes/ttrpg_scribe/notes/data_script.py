from typing import Any

from ttrpg_scribe.core import script_loader
from ttrpg_scribe.notes import data_cache, paths


def bind(namespace: paths.Namespace, template: str) -> dict[str, Any]:
    def _bind_data(name, script) -> dict[str, Any]:
        with data_cache.for_file(name, script) as (cache, valid):
            if valid:
                return cache.data
            module = script_loader.load(name, script, execute=True)
            exports = getattr(module, 'exports', None)
            if not exports:
                return {}
            if not isinstance(exports, dict):
                raise TypeError(f'Value of {script}.exports is not a dict')
            cache.data = exports
            cache.modified = True
            return cache.data
        return {}
    [name, _] = template.split('.', maxsplit=1)
    script = namespace.pages(f'{name}.py')
    if script.exists():
        return _bind_data(name, script)
    return {}


script_loader.add_library_folder('pages')
