import logging
import traceback
from functools import reduce
from typing import Any

import flask
from jinja2.runtime import Macro
from markupsafe import Markup
from pluralizer import Pluralizer

import ttrpg_scribe.core.markdown

_blueprint = flask.Blueprint('core', __name__, static_folder='static',
                      template_folder='templates', url_prefix='/core')


class ExtensibleJSONProvider(flask.json.provider.DefaultJSONProvider):
    @staticmethod
    def encode_json(obj: Any) -> Any:
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        return flask.json.provider.DefaultJSONProvider.default(obj)

    default = staticmethod(encode_json)


def extend(app: flask.Flask):
    app.json = ExtensibleJSONProvider(app)
    app.jinja_env.policies['json.dumps_kwargs'].update(
        default=ExtensibleJSONProvider.encode_json)
    app.register_blueprint(_blueprint)


@_blueprint.app_template_test()
def exception(x):
    return isinstance(x, Exception)


@_blueprint.app_template_filter()
def handle_exception(ex: Exception):
    traceback.print_exception(ex)
    return ''.join(traceback.format_exception_only(type(ex), ex))


@_blueprint.app_template_filter()
def block_markdown(s: str):
    html, _ = ttrpg_scribe.core.markdown.convert(s)
    return Markup('\n'.join(html.splitlines()))


@_blueprint.app_template_filter()
def inline_markdown(s: str):
    html, _ = ttrpg_scribe.core.markdown.convert(s)
    return Markup('\n'.join(line.removeprefix('<p>').removesuffix('</p>')
        for line in html.splitlines()))


__PLURALIZER = Pluralizer()


@_blueprint.app_template_filter()
def plural(s: str, count: int, inclusive: bool = False):
    return __PLURALIZER.pluralize(s, count, inclusive=inclusive)


@_blueprint.app_template_filter()
def ordinal(n: int):
    match n % 10:
        case 1:
            return f'{n}st'
        case 2:
            return f'{n}nd'
        case 3:
            return f'{n}rd'
        case _:
            return f'{n}th'


@_blueprint.app_template_filter()
def format_as(value: Any, spec: str):
    match value:
        case tuple():
            return spec.format(*value)
        case _:
            return spec.format(value)


@_blueprint.app_template_filter()
def kebab(value: str | tuple[str, ...]):
    if isinstance(value, tuple):
        value = '-'.join(value)
    return value.lower().replace(' ', '-')


@_blueprint.app_template_global('DEPRECATED')
def deprecated(old: Macro | str, new: Macro | str | None):
    def macro_name(macro: Macro):
        import inspect
        from pathlib import Path
        source = inspect.getsourcefile(macro._func)
        if source is None:
            return f'{macro.name}()'
        else:
            source = Path(source)
            source = reduce(str.removesuffix, reversed(source.suffixes), source.name)
            return f'{source}.{macro.name}()'
    if isinstance(old, Macro):
        old = macro_name(old)
    if isinstance(new, Macro):
        new = macro_name(new)
    logging.warning(f'{old} is deprecated!' if new is None
                    else f'{old} is deprecated! Use {new} instead.')


@_blueprint.before_app_request
def setup_asset_registry():
    flask.g.assets = {
        'scripts': list(),
        'stylesheets': set(),
    }
