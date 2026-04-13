from typing import Any, Self


class Tag:
    name: str
    children: list[Self | str]
    attrs: dict[str, str]

    def __init__(self, name: str, *,
                 children: list[Self | str] | None = None,
                 attrs: dict[str, str] | None = None,
                 **kwargs: Any) -> None:
        self.name = name
        self.children = children if children else []
        self.attrs = attrs if attrs else {}
        for prop, value in kwargs.items():
            setattr(self, prop, value)

    @property
    def id(self) -> str | None:
        return self.attrs.get('id')

    @id.setter
    def id(self, id: str):
        self.attrs['id'] = id

    @property
    def style(self) -> str | None:
        return self.attrs.get('style')

    @style.setter
    def style(self, style: str):
        self.attrs['style'] = style

    @property
    def text(self) -> str:
        return ''.join(map(str, self.children))

    @text.setter
    def text(self, text: str):
        self.children = [text]

    def __str__(self) -> str:
        opening_tag = ' '.join([self.name, *(f'{k}="{v}"' for k, v in self.attrs.items())])
        return (f'<{opening_tag}>{self.text}</{self.name}>')
