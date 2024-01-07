import importlib.util
import sys
from pathlib import Path


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
