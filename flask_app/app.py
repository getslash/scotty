import functools
import logging
import os

import flask
import logbook
import raven
import yaml
from flask_mail import Mail  # pylint: disable=import-error
from flask_security import Security  # pylint: disable=import-error
from jira import JIRAError
from logbook.compat import redirect_logging
from paramiko.ssh_exception import SSHException
from raven.contrib.flask import Sentry

APP = None


def get_or_create_app(config=None):
    global APP

    if APP is None:
        APP = create_app(config=config)

    return APP


def needs_app_context(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        with get_or_create_app().app_context():
            return f(*args, **kwargs)

    return wrapper


def create_app(config=None):
    if config is None:
        config = {}

    ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

    app = flask.Flask(__name__, static_folder=os.path.join(ROOT_DIR, "..", "static"))

    app.config["COMBADGE_CONTACT_TIMEOUT"] = 60 * 60
    app.config["SHA512SUM"] = "/usr/bin/sha512sum"
    app.config["STORAGE_PATH"] = os.environ.get("STORAGE_PATH")
    _CONF_D_PATH = os.environ.get(
        "CONFIG_DIRECTORY", os.path.join(ROOT_DIR, "..", "conf.d")
    )

    configs = [os.path.join(ROOT_DIR, "app.yml")]

    if os.path.isdir(_CONF_D_PATH):
        configs.extend(
            sorted(
                os.path.join(_CONF_D_PATH, x)
                for x in os.listdir(_CONF_D_PATH)
                if x.endswith(".yml")
            )
        )
    for yaml_path in configs:
        if os.path.isfile(yaml_path):
            with open(yaml_path) as yaml_file:
                app.config.update(yaml.load(yaml_file, Loader=yaml.FullLoader))

    app.config.update(config)

    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.path.expandvars(
            os.environ.get(
                "SQLALCHEMY_DATABASE_URI",
                "postgresql://localhost/{0}".format(app.config["app_name"]),
            )
        )

    del app.logger.handlers[:]
    redirect_logging()

    app.logger.info("Started")

    Mail(app)

    if os.environ.get("SQLALCHEMY_LOG_QUERIES"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    app.raven = Sentry(
        app,
        client=raven.Client(
            dsn=app.config.get("SENTRY_DSN"),
            ignore_exceptions=[SSHException, JIRAError],
        ),
    )

    from . import models

    models.db.init_app(app)

    from .errors import errors
    from .blueprints import (
        auth,
        beams,
        files,
        issues,
        trackers,
        user_datastore,
        users,
        views,
        keys,
    )

    Security(app, user_datastore, register_blueprint=False)

    app.register_blueprint(auth)
    app.register_blueprint(beams, url_prefix="/beams")
    app.register_blueprint(files, url_prefix="/files")
    app.register_blueprint(issues, url_prefix="/issues")
    app.register_blueprint(trackers, url_prefix="/trackers")
    app.register_blueprint(users, url_prefix="/users")
    app.register_blueprint(keys, url_prefix="/keys")
    app.register_blueprint(views)

    if app.config.get("DEBUG"):
        from .blueprints import test_methods

        app.register_blueprint(test_methods)

    for code in errors:
        app.errorhandler(code)(errors[code])

    return app
