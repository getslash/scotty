import os
import flask
import yaml
from raven.contrib.flask import Sentry
from flask.ext.security import Security  # pylint: disable=import-error
from flask.ext.mail import Mail  # pylint: disable=import-error
import logbook
from logbook.compat import redirect_logging



def create_app(config=None):
    if config is None:
        config = {}

    ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

    app = flask.Flask(__name__, static_folder=os.path.join(ROOT_DIR, "..", "static"))

    app.config['COMBADGE_CONTACT_TIMEOUT'] = 60 * 60
    app.config['SHA512SUM'] = '/usr/bin/sha512sum'
    _CONF_D_PATH = os.environ.get('CONFIG_DIRECTORY', os.path.join(ROOT_DIR, "..", "..", "conf.d"))

    configs = [os.path.join(ROOT_DIR, "app.yml")]

    if os.path.isdir(_CONF_D_PATH):
        configs.extend(sorted(os.path.join(_CONF_D_PATH, x) for x in os.listdir(_CONF_D_PATH) if x.endswith(".yml")))

    for yaml_path in configs:
        if os.path.isfile(yaml_path):
            with open(yaml_path) as yaml_file:
                app.config.update(yaml.load(yaml_file))

    app.config.update(config)

    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.path.expandvars(
            os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://localhost/{0}'.format(app.config['app_name'])))


    if os.path.exists("/dev/log"):
        syslog_handler = logbook.SyslogHandler(app.config['app_name'], "/dev/log")
        syslog_handler.push_application()

    del app.logger.handlers[:]
    redirect_logging()

    app.logger.info("Started")

    Mail(app)

    app.raven = Sentry(app, dsn=app.config.get('SENTRY_DSN'))

    from . import models

    models.db.init_app(app)

    from . import auth
    Security(app, auth.user_datastore, register_blueprint=False)

    from .auth import auth
    from .views import views
    from .setup import setup
    blueprints = [auth, views, setup]

    from .errors import errors

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    for code in errors:
        app.errorhandler(code)(errors[code])

    return app
