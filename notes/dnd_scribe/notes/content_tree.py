import re
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Self

from dnd_scribe.core import markdown
from dnd_scribe.notes import paths


@dataclass
class Content:
    relative_path: str
    title: str
    class Type(Enum):
        Directory = auto()
        File = auto()
    type: Type
    children: dict[str, Self]

    def __init__(self, absolute_path: Path, title: str) -> None:
        relative_path = absolute_path.relative_to(paths.pages())
        match relative_path.suffixes:
            case ['.j2', '.md'] | ['.j2', '.html'] as suffixes:
                name = relative_path.name.removesuffix(''.join(suffixes))
                relative_path = relative_path.with_name(name).with_suffix('.html')
        self.relative_path = relative_path.as_posix()
        print(self.relative_path)
        self.title = title
        self.type = Content.Type.File if absolute_path.is_file()\
            else Content.Type.Directory
        self.children = {}

    HTML_TITLE = re.compile(r'<title>(.+)<\/title>')
    def __find_title(self, path: Path) -> str:
        match path.suffixes:
            case ['.j2', '.md']:
                with open(path, encoding='utf-8') as file:
                    title = markdown.find_title(file.read())
                    if title:
                        return title
            case ['.j2', '.html']:
                return path.name.removesuffix('.html.j2')
        return path.name

    def add_child(self, path: Path) -> Self:
        child = Content(path, self.__find_title(path))
        self.children[path.name] = child
        return child

    def is_file(self) -> bool:
        return self.type == Content.Type.File

    def __iter__(self):
        return iter(self.children.items())

def walk() -> Content:
    def walk_subtree(dir: Path, subtree: Content):
        for path in dir.iterdir():
            if path.name in ['assets', '__pycache__'] or path.suffix == '.py':
                continue
            child = subtree.add_child(path)
            if path.is_dir():
                walk_subtree(path, child)
        return subtree
    return walk_subtree(paths.pages(), Content(paths.pages(), ''))
