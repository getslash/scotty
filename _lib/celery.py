import click

import logbook

_logger = logbook.Logger(__name__)

@click.group()
def celery():
    pass


@celery.command()
@click.argument('name')
def task(name):

    from flask_app import tasks
    from flask_app.app import create_app


    task = getattr(tasks, name, None)
    if task is None:
        click.echo('Could not find task named {}'.format(task))
        raise click.Abort()
    with create_app().app_context():
        task()
