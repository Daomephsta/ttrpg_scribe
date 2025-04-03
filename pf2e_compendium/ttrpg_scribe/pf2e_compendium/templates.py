from typing import Callable, Self
from typing import Protocol


type Template[T] = Callable[[T], None]


class SupportsTemplates(Protocol):
    def apply(self, *templates: Template) -> Self:
        ...


type Variant = tuple[str, list[Template]] | tuple[list[Template], str]


def variants[T: SupportsTemplates](factory: Callable[[str], T], base_id: str,
                                   *variants: Variant) -> dict[str, T]:
    base_key = base_id.rsplit('/', maxsplit=1)[-1].upper().replace('-', '_')

    def make():
        for variant in variants:
            match variant:
                case str() as prefix, list() as templates:
                    yield prefix + base_key, factory(base_id).apply(*templates)
                case list() as templates, str() as suffix:
                    yield base_key + suffix, factory(base_id).apply(*templates)

    return dict(make())
