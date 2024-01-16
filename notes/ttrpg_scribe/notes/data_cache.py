import pickle
from functools import cache
from pathlib import Path
from typing import Any, Self

from ttrpg_scribe.notes import paths


@cache
def FILE_TIMES():
    return paths.build()/'file_times.cache'


_file_times: dict[Path, float] = {}


def file_times():
    global _file_times
    if not _file_times and FILE_TIMES().exists():
        _file_times = pickle.loads(FILE_TIMES().read_bytes())
    return _file_times


class DataCache:
    def __init__(self, cache: Path, dependencies: set[Path]) -> None:
        self.cache = cache
        self.dependencies = dependencies
        self.data: dict[str, Any] = {}
        self.modified: bool = False
        for dependency in (dependencies - file_times().keys()):
            file_times()[dependency] = dependency.stat().st_mtime

    def _update_mtime(self, file: Path):
        file_times()[file] = file.stat().st_mtime

    def is_valid(self) -> bool:
        valid = True
        for dependency in self.dependencies:
            m_time = dependency.stat().st_mtime
            if file_times()[dependency] < m_time:
                file_times()[dependency] = m_time
                valid = False
        return valid

    def __enter__(self) -> tuple[Self, bool]:
        if self.cache.exists():
            if self.is_valid():
                self.data = pickle.loads(self.cache.read_bytes())
                self.modified = True
                return (self, True)
        else:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
        return (self, False)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            if self.modified:
                self.cache.write_bytes(pickle.dumps(self.data))
            FILE_TIMES().write_bytes(pickle.dumps(file_times()))
        return False


def for_file(name: str, *dependencies: Path) -> DataCache:
    cache = paths.build()/f'{name}.data'
    return DataCache(cache, set(dependencies))
