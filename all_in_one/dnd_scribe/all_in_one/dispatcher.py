from werkzeug.middleware.dispatcher import DispatcherMiddleware
import flask
import dnd_scribe.bestiary.flask
from dnd_scribe.bestiary.apis import DND5EAPI
import dnd_scribe.core.flask

app = flask.Flask('dnd_scribe.all_in_one')
app.register_blueprint(dnd_scribe.bestiary.flask.blueprint)
app.register_blueprint(dnd_scribe.core.flask.blueprint)
application = DispatcherMiddleware(app, {
    
})
@app.get('/test')
def test():
    return flask.render_template('test.j2.html', creatures = [DND5EAPI.creature('elk'), DND5EAPI.creature('wolf')])

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('localhost', 5000, application, 
               use_reloader=True, use_debugger=True)