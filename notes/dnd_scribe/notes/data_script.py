from typing import Any

from dnd_scribe.core import script_loader
from dnd_scribe.notes import data_cache, paths


def _bind_data(template_file, name, script, module) -> dict[str, Any]:
    with data_cache.for_file(name, template_file, script) as (cache, valid):
        if valid:
            return cache.data
        exports = getattr(module, 'exports', None)
        if not exports:
            return {}
        if not isinstance(exports, dict):
            raise TypeError(f'Value of {script}.exports is not a dict')
        cache.data = exports
        cache.modified = True
        return cache.data
    return {}

def bind(template: str) -> dict[str, Any]:
    # Bind helper script to template
    template_file = paths.pages()/template
    [name, _] = template.split('.', maxsplit=1)
    script = paths.pages()/f'{name}.py'
    if script.exists():
        module = script_loader.load(name, script, execute=True)
        return _bind_data(template_file, name, script, module)
    return {}