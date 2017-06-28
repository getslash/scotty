import http
import sqlalchemy
from flask import Blueprint, request, jsonify
from .utils import validate_schema
from ..models import db, Issue
from ..issue_trackers import is_valid_issue

issues = Blueprint("issues", __name__, template_folder="templates")


@issues.route('', methods=['POST'])
@validate_schema({
    'type': 'object',
    'properties': {
        'issue': {
            'type': 'object',
            'properties': {
                'tracker_id': {'type': 'number'},
                'id_in_tracker': {'type': 'string'},
            },
            'required': ['tracker_id', 'id_in_tracker']
        }
    },
    'required': ['issue']
})
def create():
    data = request.json['issue']
    id_in_tracker = data['id_in_tracker'].strip()
    if not id_in_tracker:
        return 'Invalid issue id', http.client.CONFLICT

    issue = Issue(tracker_id=data['tracker_id'], id_in_tracker=id_in_tracker, open=True)
    if not is_valid_issue(issue):
        return "Invalid Issue", http.client.BAD_REQUEST

    db.session.add(issue)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        issue = db.session.query(Issue).filter_by(
            tracker_id=data['tracker_id'], id_in_tracker=id_in_tracker).first()
        if not issue:
            raise
    return jsonify({'issue': issue.to_dict()})


@issues.route('/<int:issue>', methods=['DELETE'])
def delete(issue):
    issue = db.session.query(Issue).filter_by(id=issue).first()
    if not issue:
        return 'Issue not found', http.client.NOT_FOUND

    db.session.delete(issue)
    db.session.commit()
    return ''


@issues.route('/<int:issue>', methods=['GET'])
def get(issue):
    issue = db.session.query(Issue).filter_by(id=issue).first()
    if not issue:
        return 'Issue not found', http.client.NOT_FOUND

    return jsonify({'issue': issue.to_dict()})
