import http
from flask import Blueprint, request, jsonify
from .utils import validate_schema
from .models import db, Issue

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
    issue = Issue(tracker_id=data['tracker_id'], id_in_tracker=data['id_in_tracker'], open=True)
    db.session.add(issue)
    db.session.commit()
    return jsonify({'issue': issue.to_dict()})


@issues.route('/<int:issue>', methods=['DELETE'])
def delete(issue):
    issue = db.session.query(Issue).filter_by(id=issue).first()
    if not issue:
        return 'Issue not found', http.client.NOT_FOUND

    db.session.delete(issue)
    db.session.commit()
    return ''
