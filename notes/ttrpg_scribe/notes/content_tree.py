from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from ttrpg_scribe.core import markdown
from ttrpg_scribe.notes import paths


@dataclass
class Content:
    url: str
    title: str

    class Type(Enum):
        Directory = auto()
        File = auto()
    type: Type
    children: dict[str, 'Content']

    def __init__(self, namespace: paths.Namespace, absolute_path: Path, title: str) -> None:
        self.namespace = namespace
        url = namespace.id/absolute_path.relative_to(namespace.pages())
        match url.suffixes:
            case ['.j2', '.md'] | ['.j2', '.html'] as suffixes:
                name = url.name.removesuffix(''.join(suffixes))
                url = url.with_name(name).with_suffix('.html')
        self.url = url.as_posix()
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
        child = Content(self.namespace, path, self.__find_title(path))
        self.children[path.name] = child
        return child

    def is_file(self) -> bool:
        return self.type == Content.Type.File

    def __iter__(self):
        return iter(self.children.items())


def walk(path: str) -> Content:
    def walk_subtree(dir: Path, subtree: Content):
        for path in sorted(dir.iterdir(), key=lambda path: path.name):
            if path.name in ['assets', '__pycache__'] or path.suffix == '.py':
                continue
            child = subtree.add_child(path)
            if path.is_dir():
                walk_subtree(path, child)
        return subtree
    root_path = paths.CAMPAIGN.get(path)
    root = walk_subtree(root_path, Content(paths.CAMPAIGN, root_path, ''))
    if paths.SETTING is not None:
        setting_path = paths.SETTING.get(path)
        root.children['setting'] = walk_subtree(
            setting_path, Content(paths.SETTING, setting_path, 'setting'))
    return root
