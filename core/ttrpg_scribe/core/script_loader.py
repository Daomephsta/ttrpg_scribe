import importlib.util
import itertools
import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Sequence

from ttrpg_scribe.notes import paths


def load(module_name: str, path: Path, execute=False):
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec, f'spec_from_file_location returned None for {path}'
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if execute:
        assert spec.loader, f'spec.loader returned None for {path}'
        spec.loader.exec_module(module)
    return module


class ScriptFinder(MetaPathFinder):
    locations: set[str] = set()

    def __try_resolve(self, fullname: str, fragment: str) -> ModuleSpec | None:
        candidates: list[Path] = [delta(paths.project_dir/base)
                      for base, delta in itertools.product(
            [fragment, f'setting/{fragment}'],
            [lambda p: p/'__init__.py', lambda p: p.with_suffix('.py')]
        )]
        for path in candidates:
            if path.exists():
                return spec_from_file_location(fullname, path)
        tried = '\n\t'.join(p.as_posix() for p in candidates)
        print(f'Could not resolve \'{fullname}\' at any of:\n\t{tried}',
              file=sys.stderr)
        return None

    def find_spec(self, fullname: str, path: Sequence[str] | None,
                  target: ModuleType | None = None) -> ModuleSpec | None:
        for location in self.locations:
            fragment = fullname.replace('.', '/')
            if fullname.startswith(location):
                spec = self.__try_resolve(fullname, fragment)
                if spec is not None:
                    return spec
        return None


def add_library_folder(folder: str):
    ScriptFinder.locations.add(folder)


sys.meta_path.append(ScriptFinder())
