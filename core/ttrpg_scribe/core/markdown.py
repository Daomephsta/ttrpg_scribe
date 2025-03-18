import re
from typing import Any, NamedTuple, TypedDict, cast

import frontmatter
from flask import render_template
from markdown import Markdown
from markdown.extensions.toc import TocExtension
from markupsafe import Markup

MD_HEADER = re.compile('^# (.+)$', flags=re.MULTILINE)
__renderer = Markdown(extensions=['admonition', 'attr_list', 'def_list',
    'md_in_html', 'smarty', 'tables',
    # Empty string marker disables the search to speed up processing
    TocExtension(marker='')],
    output_format='html')


def find_title(markdown: str) -> str | None:
    metadata, markdown = frontmatter.parse(markdown)
    if 'title' in metadata:
        return str(metadata['title'])
    match = MD_HEADER.search(markdown)
    return match.group(1) if match else None


class Metadata(TypedDict):
    layout: str
    extra_scripts: list[str | dict]
    extra_stylesheets: list[str]


_ALLOWED_SCRIPT_ATTRS = {'async', 'crossorigin', 'blocking', 'defer', 'fetchpriority',
                         'integrity', 'nomodule', 'nonce', 'referrerpolicy', 'src', 'type'}


def parse_metadata(metadata: dict[str, Any]) -> Metadata:
    def as_list[E](name: str, element_type: type[E], default: list[E]) -> list[E]:
        candidate = cast(list[E], metadata.get(name, default))
        match candidate:
            case []:
                return candidate
            case [*elements]:
                type_errors = [e for e in elements
                    if not isinstance(e, element_type)]
                if type_errors:
                    args = ', '.join(str(e) for e in type_errors)
                    arg_types = ', '.join(type(e).__name__ for e in type_errors)
                    raise TypeError(f'Elements [{args}] in {name} must each be'
                                    f' {element_type} not [{arg_types}]')
                return candidate
            case _:
                raise TypeError(f'Value {candidate} of {name} must be a list')

    def sanitise(attrs: dict[str, str]):
        return {k: attrs[k] for k in (attrs.keys() & _ALLOWED_SCRIPT_ATTRS)}
    return {
        'layout': metadata.get('layout', 'base'),
        'extra_scripts': [sanitise(s) if isinstance(s, dict) else dict(src=s)
            for s in as_list('extra_scripts', str | dict, [])],  # type: ignore
        'extra_stylesheets': as_list('extra_stylesheets', str, []),
    }


class RenderResult(NamedTuple):
    html: str
    toc: list[dict[str, Any]]


def convert(markdown: str):
    html = __renderer.convert(markdown)
    toc = getattr(__renderer, 'toc_tokens')
    __renderer.reset()
    return RenderResult(html, toc)


def render(markdown: str):
    metadata, markdown = frontmatter.parse(markdown)
    metadata = parse_metadata(metadata)
    html_fragment, toc = convert(markdown)

    return render_template(f"layout/{metadata['layout']}.j2.html",
        content=Markup(html_fragment),
        toc=toc,
        extra_stylesheets=metadata['extra_stylesheets'],
        extra_scripts=metadata['extra_scripts'])
