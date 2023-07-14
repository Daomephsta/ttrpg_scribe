import importlib.util
from pathlib import Path


def load(module_name: str, path: Path, execute=False):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec, f'spec_from_file_location returned None for {path}'
    module = importlib.util.module_from_spec(spec)
    if execute:
        assert spec.loader, f'spec.loader returned None for {path}'
        spec.loader.exec_module(module)
    return module