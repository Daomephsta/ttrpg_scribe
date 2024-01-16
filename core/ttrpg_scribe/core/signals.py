import blinker
import flask

clean = blinker.signal('ttrpg_scribe.clean')


def send_clean():
    app = None
    if flask.current_app:
        app = flask.current_app._get_current_object()  # type: ignore
    clean.send(app)
