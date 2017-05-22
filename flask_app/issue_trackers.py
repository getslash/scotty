import json
from datetime import timedelta, timezone

import flux
import logbook

from jira import JIRA as JIRAAPI
from jira.exceptions import JIRAError

from .models import Tracker as TrackerModel, db

logger = logbook.Logger(__name__)


class Tracker:
    @staticmethod
    def get(model):
        if model.type == "file":
            return File(model.url)
        elif model.type == "jira":
            return JIRA(url=model.url, config=model.config)
        elif model.type == "faulty":
            return Faulty()
        else:
            raise ValueError("Unknown model type {}".format(model.type))

    def refresh(self, issues):
        raise NotImplementedError()

    def is_valid_issue(self, id_in_tracker):
        raise NotImplementedError()


class JIRA(Tracker):
    def __init__(self, *, url, config):
        self._url = url
        config = json.loads(config)
        self._jira = JIRAAPI(url, basic_auth=(config['username'], config['password']))
        self._resolution_grace = timedelta(days=config.get('resolution_grace', 0))

    def refresh(self, issues):
        for issue_obj in issues:
            issue = self._jira.issue(issue_obj.id_in_tracker)

            if issue.fields.resolutiondate is None:
                issue_obj.open = True
            else:
                resolution_date = flux.current_timeline.datetime.strptime(
                    issue.fields.resolutiondate, '%Y-%m-%dT%H:%M:%S.%f%z')
                now = flux.current_timeline.datetime.now().replace(tzinfo=timezone.utc)
                issue_obj.open = (now - resolution_date) < self._resolution_grace

        db.session.commit()

    def is_valid_issue(self, id_in_tracker):
        try:
            self._jira.issue(id_in_tracker)
        except JIRAError:
            return False
        else:
            return True


  # pylint: disable=abstract-method
class File(Tracker):
    def __init__(self, name):
        self._name = name

    def refresh(self, issues):
        with open(self._name, 'r') as f:
            data = json.load(f)
            for issue in issues:
                issue.open = data[issue.id_in_tracker]


class Faulty(Tracker):
    def refresh(self, issues):
        raise Exception("Tracker Error")


def refresh(tracker, issues):
    Tracker.get(tracker).refresh(issues)


def is_valid_issue(issue):
    tracker_obj = db.session.query(TrackerModel).filter_by(id=issue.tracker_id).first()
    if not tracker_obj:
        return False

    return Tracker.get(tracker_obj).is_valid_issue(issue.id_in_tracker)
