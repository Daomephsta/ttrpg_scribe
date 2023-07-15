import pickle
from pathlib import Path
from typing import Any, Self

from dnd_scribe.notes import paths

FILE_TIMES: Path
file_times: dict[Path, float]

def initialise(cache_dir: Path):
    global FILE_TIMES, file_times
    FILE_TIMES = cache_dir/'file_times.cache'
    file_times = {}
    if FILE_TIMES.exists():
        with open(FILE_TIMES, 'rb') as cache_file:
            file_times = pickle.load(cache_file)

class DataCache:
    def __init__(self, cache: Path, dependencies: set[Path]) -> None:
        self.cache = cache
        self.dependencies = dependencies
        self.data: dict[str, Any] = {}
        self.modified: bool = False
        for dependency in (dependencies - file_times.keys()):
            file_times[dependency] = dependency.stat().st_mtime

    def _update_mtime(self, file: Path):
        file_times[file] = file.stat().st_mtime

    def is_valid(self) -> bool:
        valid = True
        for dependency in self.dependencies:
            m_time = dependency.stat().st_mtime
            if file_times[dependency] < m_time:
                file_times[dependency] = m_time
                valid = False
        return valid

    def __enter__(self) -> tuple[Self, bool]:
        if self.cache.exists():
            if self.is_valid():
                with open(self.cache, 'rb') as cache_file:
                    self.data = pickle.load(cache_file)
                    self.modified = True
                return (self, True)
        else:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
        return (self, False)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            if self.modified:
                with open(self.cache, 'wb') as cache_file:
                    pickle.dump(self.data, cache_file)
            with open(FILE_TIMES, 'wb') as cache_file:
                pickle.dump(file_times, cache_file)
        return False

def for_file(name: str, *dependencies: Path) -> DataCache:
    cache = paths.build()/f'{name}.data'
    return DataCache(cache, set(dependencies))