from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from ttrpg_scribe.core import markdown
from ttrpg_scribe.notes import paths


@dataclass
class Content:
    relative_path: str
    title: str

    class Type(Enum):
        Directory = auto()
        File = auto()
    type: Type
    children: dict[str, 'Content']

    def __init__(self, absolute_path: Path, title: str) -> None:
        relative_path = absolute_path.relative_to(paths.pages())
        match relative_path.suffixes:
            case ['.j2', '.md'] | ['.j2', '.html'] as suffixes:
                name = relative_path.name.removesuffix(''.join(suffixes))
                relative_path = relative_path.with_name(name).with_suffix('.html')
        self.relative_path = relative_path.as_posix()
        self.title = title
        self.type = Content.Type.File if absolute_path.is_file()\
            else Content.Type.Directory
        self.children = {}

    def __find_title(self, path: Path) -> str:
        if path.suffixes == ['.j2', '.md']:
            with open(path, encoding='utf-8') as file:
                title = markdown.find_title(file.read())
                if title:
                    return title
        return path.name.removesuffix(f'.{'.'.join(path.suffixes)}')

    def add_child(self, path: Path) -> 'Content':
        child = Content(path, self.__find_title(path))
        self.children[path.name] = child
        return child

    def is_file(self) -> bool:
        return self.type == Content.Type.File

    def __iter__(self):
        return iter(self.children.items())


def walk(path: Path) -> Content:
    def walk_subtree(dir: Path, subtree: Content):
        for path in sorted(dir.iterdir(), key=lambda path: path.name):
            if path.name in ['assets', '__pycache__'] or path.suffix == '.py':
                continue
            child = subtree.add_child(path)
            if path.is_dir():
                walk_subtree(path, child)
        return subtree
    return walk_subtree(path, Content(path, ''))
