import re

import frontmatter
from flask import render_template
from markdown import Markdown
from markdown.extensions.toc import TocExtension

MD_HEADER = re.compile('^# (.+)$', flags=re.MULTILINE)
renderer = Markdown(extensions=['attr_list', 'md_in_html', 'tables',
    # Empty string marker disables the search to speed up processing
    TocExtension(marker='')],
    output_format='html')

def find_title(markdown: str):
    match = MD_HEADER.search(markdown)
    return match.group(1) if match else None

def render(markdown: str):
    metadata, markdown = frontmatter.parse(markdown)
    # Convert Markdown to HTML fragment
    html_fragment = renderer.convert(markdown)
    # Parse metadata
    def as_list(name: str, element_type, default) -> list:
        candidate = metadata.get(name, default)
        match candidate:
            case []:
                return candidate
            case [*elements]:
                type_errors = [e for e in elements
                    if not isinstance(e, element_type)]
                if type_errors:
                    args = ', '.join(str(e) for e in type_errors)
                    arg_types = ', '.join(type(e).__name__ for e in type_errors)
                    raise TypeError(f'Elements [{args}] in {name} must each be'\
                                    f' {element_type} not [{arg_types}]')
                return candidate
            case _:
                raise TypeError(f'Value {candidate} of {name} must be a list')
    layout = metadata.get('layout', 'base')
    def script(element: str | dict) -> str:
        match element:
            case dict() as attributes:
                return ' '.join(f'{key}="{value}"'
                        if not isinstance(value, bool)
                        else key # True boolean attributes just need the key
                    for key, value in attributes.items()
                    # Filter out false boolean attributes
                    if not (isinstance(value, bool) and not value))
            case str():
                return f'src="{element}"'
    extra_scripts=[script(s) for s in as_list('extra_scripts', str | dict, [])]
    extra_stylesheets=as_list('extra_stylesheets', str, [])
    assert isinstance(extra_scripts, list), 'extra_scripts must be a list'
    # Render template using HTML fragment and metadata
    return render_template(f"layout/{layout}.html.j2",
        content=html_fragment,
        toc=renderer.toc_tokens, # type: ignore
        extra_stylesheets=extra_stylesheets,
        extra_scripts=extra_scripts)