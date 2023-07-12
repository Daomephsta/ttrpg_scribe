import traceback

from flask import Blueprint

import dnd_scribe.core.markdown

blueprint = Blueprint('core', __name__, static_folder='static', url_prefix='/core')

@blueprint.app_template_test()
def exception(x):
    return isinstance(x, Exception)

@blueprint.app_template_filter()
def handle_exception(ex: Exception):
    traceback.print_exception(ex)
    return ''.join(traceback.format_exception_only(type(ex), ex))

@blueprint.app_template_filter()
def markdown(s: str):
    return dnd_scribe.core.markdown.renderer.convert(s)[len('<p>'):-len('</p>')]