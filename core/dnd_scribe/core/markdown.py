import re
from typing import Any, TypedDict, cast

import frontmatter
from flask import render_template
from markdown import Markdown
from markdown.extensions.toc import TocExtension
from markupsafe import Markup

MD_HEADER = re.compile('^# (.+)$', flags=re.MULTILINE)
renderer = Markdown(extensions=['attr_list', 'md_in_html', 'tables',
    # Empty string marker disables the search to speed up processing
    TocExtension(marker='')],
    output_format='html')


def find_title(markdown: str):
    match = MD_HEADER.search(markdown)
    return match.group(1) if match else None


class Metadata(TypedDict):
    layout: str
    extra_scripts: list[str | dict]
    extra_stylesheets: list[str]


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
    return {
        'layout': metadata.get('layout', 'base'),
        'extra_scripts': [s if isinstance(s, dict) else dict(src=s)
            for s in as_list('extra_scripts', str | dict, [])],
        'extra_stylesheets': as_list('extra_stylesheets', str, []),
    }


def render(markdown: str):
    metadata, markdown = frontmatter.parse(markdown)
    html_fragment = renderer.convert(markdown)
    metadata = parse_metadata(metadata)
    return render_template(f"layout/{metadata['layout']}.j2.html",
        content=Markup(html_fragment),
        toc=renderer.toc_tokens,  # type: ignore
        extra_stylesheets=metadata['extra_stylesheets'],
        extra_scripts=metadata['extra_scripts'])
