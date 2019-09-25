#! /usr/bin/python
from __future__ import print_function
import os
import sys
import time
import random
import string
import subprocess
from collections import defaultdict
from pathlib import Path
import subprocess

from _lib.bootstrapping import bootstrap_env, from_project_root, requires_env, from_env_bin
bootstrap_env()

from _lib.params import APP_NAME
from _lib.frontend import frontend, ember
from _lib.source_package import prepare_source_package
from _lib.db import db
from _lib.celery import celery
from _lib.utils import interact
from _lib.deployment import run_gunicorn
import click
import requests
import logbook

##### ACTUAL CODE ONLY BENEATH THIS POINT ######


@click.group()
def cli():
    pass


cli.add_command(run_gunicorn)
cli.add_command(db)
cli.add_command(frontend)
cli.add_command(ember)
cli.add_command(celery)


def _generate_secret_string(length=50):
    return "".join([random.choice(string.ascii_letters) for i in range(length)])


def _ensure_conf():
    config_directory = os.environ.get('CONFIG_DIRECTORY', None)
    if config_directory is None:
        config_directory = os.environ['CONFIG_DIRECTORY'] = '/conf'

    config_directory = Path(config_directory)
    private_file = config_directory / '000-private.yml'
    if not private_file.is_file():
        with private_file.open('w') as p_file:
            for secret_name in ('SECRET_KEY', 'SECURITY_PASSWORD_SALT'):
                p_file.write("{name}: {secret!r}\n".format(name=secret_name, secret=_generate_secret_string()))


@cli.command(name='docker-start')
def docker_start():
    from flask_app.app import create_app
    from flask_app.models import db
    import flask_migrate
    import gunicorn.app.base
    from werkzeug.contrib.fixers import ProxyFix


    _ensure_conf()

    app = create_app({'PROPAGATE_EXCEPTIONS': True})
    app.wsgi_app = ProxyFix(app.wsgi_app)

    flask_migrate.Migrate(app, db)

    with app.app_context():
        flask_migrate.upgrade()

    cpu_count = int(subprocess.check_output('nproc').decode("utf-8").strip())
    workers_count = cpu_count * 2 + 1

    class StandaloneApplication(gunicorn.app.base.BaseApplication):

        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super(StandaloneApplication, self).__init__()

        def load_config(self):
            config = dict([(key, value) for key, value in self.options.items()
                           if key in self.cfg.settings and value is not None])
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    options = {
        'bind': '0.0.0.0:8000',
        'workers': workers_count,
    }
    logbook.StreamHandler(sys.stdout, level=logbook.DEBUG).push_application()
    if app.config['DEBUG']:
        logbook.warning('Debug mode is active!')
    StandaloneApplication(app, options).run()



@cli.command(name='docker-nginx-start')
def docker_nginx_start():
    import jinja2
    with open('etc/nginx-site-conf.j2') as f:
        template = jinja2.Template(f.read())

    environ = defaultdict(str, os.environ)
    with open('/etc/nginx/conf.d/scotty.conf', 'w') as f:
        f.write(template.render({'environ': environ, 'hostname': environ['SCOTTY_HOSTNAME']}))

    nginx_path = '/usr/sbin/nginx'
    os.execv(nginx_path, [nginx_path, '-g', 'daemon off;'])


@cli.command()
@click.option("--develop", is_flag=True)
@click.option("--app", is_flag=True)
def bootstrap(develop, app):
    deps = ["base"]
    if develop:
        deps.append("develop")
    if app:
        deps.append("app")
    bootstrap_env(deps)
    click.echo(click.style("Environment up to date", fg='green'))


@cli.command()
@click.option('--livereload/--no-livereload', is_flag=True, default=True)
@click.option('-p', '--port', default=8000, envvar='TESTSERVER_PORT')
@click.option('--tmux/--no-tmux', is_flag=True, default=True)
@requires_env("app", "develop")
def testserver(tmux, livereload, port):
    if tmux:
        return _run_tmux_frontend(port=port)
    from flask_app.app import create_app

    extra_files=[
        from_project_root("flask_app", "app.yml")
    ]

    app = create_app({'DEBUG': True, 'TESTING': True, 'SECRET_KEY': 'dummy', 'SECURITY_PASSWORD_SALT': 'dummy'})
    if livereload:
        from livereload import Server
        s = Server(app)
        for filename in extra_files:
            s.watch(filename)
        s.watch('flask_app')
        for filename in ['webapp.js', 'vendor.js', 'webapp.css']:
            s.watch(os.path.join('static', 'assets', filename), delay=0.5)
        logbook.StreamHandler(sys.stderr, level='DEBUG').push_application()
        s.serve(port=port, liveport=35729)
    else:
        app.run(port=port, extra_files=extra_files)

def _run_tmux_frontend(port):
    tmuxp = from_env_bin('tmuxp')
    os.execve(tmuxp, [tmuxp, 'load', from_project_root('_lib', 'frontend_tmux.yml')], dict(os.environ, TESTSERVER_PORT=str(port), CONFIG_DIRECTORY=from_project_root("conf.d")))


@cli.command()
def unittest():
    _run_unittest()


@requires_env("app", "develop")
def _run_unittest():
    subprocess.check_call(
        [from_env_bin("py.test"), "tests/test_ut"], cwd=from_project_root())


@cli.command()
@click.argument('slash_args', nargs=-1)
def slash(slash_args):
    _run_slash(slash_args)


@requires_env("app", "develop")
def _run_slash(slash_args=()):
    subprocess.check_call(
        [from_env_bin("slash"), "run"]+list(slash_args), cwd=from_project_root())


@cli.command()
def fulltest():
    _run_fulltest()


@requires_env("app", "develop")
def _run_fulltest(extra_args=()):
    subprocess.check_call([from_env_bin("py.test"), "tests"]
                          + list(extra_args), cwd=from_project_root())


@cli.command('travis-test')
def travis_test():
    subprocess.check_call('createdb {0}'.format(APP_NAME), shell=True)
    _run_unittest()
    subprocess.check_call('dropdb {0}'.format(APP_NAME), shell=True)


def _wait_for_travis_availability():
    click.echo(click.style("Waiting for service to become available on travis", fg='magenta'))
    time.sleep(10)
    for _ in range(10):
        click.echo("Checking service...")
        resp = requests.get("http://localhost/")
        click.echo("Request returned {0}".format(resp.status_code))
        if resp.status_code == 200:
            break
        time.sleep(5)
    else:
        raise RuntimeError("Web service did not become responsive")
    click.echo(click.style("Service is up", fg='green'))


@cli.command()
@requires_env("app", "develop")
def shell():
    from flask_app.app import create_app
    from flask_app import models

    app = create_app()

    with app.app_context():
        interact({
            'app': app,
            'models': models,
            'db': models.db,
        })


if __name__ == "__main__":
    cli()
