import traceback
from typing import Any

import flask
from markupsafe import Markup

import dnd_scribe.core.markdown

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
def markdown(s: str):
    md = dnd_scribe.core.markdown.renderer.convert(s)
    return Markup('\n'.join(line.removeprefix('<p>').removesuffix('</p>')
             for line in md.splitlines()))