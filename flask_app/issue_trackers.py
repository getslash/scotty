import json
from datetime import timedelta, timezone
import confetti
import flux
from jira import JIRA
import logbook
from .models import db


logger = logbook.Logger(__name__)


def _refresh_file(url, issues):
    with open(url, 'r') as f:
        data = json.load(f)
        for issue in issues:
            issue.open = data[issue.id_in_tracker]


def _refresh_faulty():
    raise Exception("Tracker Error")


def _refresh_jira(url, config, issues):
    config = confetti.Config(json.loads(config))
    jira = JIRA(url, basic_auth=(config.root.username, config.root.password))
    resolution_grace = config.get('resolution_grace', 0)
    resolution_grace = timedelta(days=resolution_grace)
    for issue_obj in issues:
        issue = jira.issue(issue_obj.id_in_tracker)

        if issue.fields.resolutiondate is None:
            issue_obj.open = True
        else:
            resolution_date = flux.current_timeline.datetime.strptime(
                issue.fields.resolutiondate, '%Y-%m-%dT%H:%M:%S.%f%z')
            now = flux.current_timeline.datetime.now().replace(tzinfo=timezone.utc)
            issue_obj.open = (now - resolution_date) < resolution_grace

    db.session.commit()



def refresh(tracker, issues):
    if tracker.type == "file":
        _refresh_file(tracker.url, issues)
    elif tracker.type == "jira":
        _refresh_jira(tracker.url, tracker.config, issues)
    elif tracker.type == "faulty":
        _refresh_faulty()
    else:
        raise ValueError("Unknown tracker type {}".format(tracker.type))
