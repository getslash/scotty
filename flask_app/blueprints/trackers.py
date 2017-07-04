import http
from flask import Blueprint, request, jsonify
from .utils import validate_schema
from ..models import db, Tracker

trackers = Blueprint("trackers", __name__, template_folder="templates")


@trackers.route('', methods=['POST'])
@validate_schema({
    'type': 'object',
    'properties': {
        'tracker': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'type': {'type': 'string'},
                'url': {'type': 'string'},
                'config': {'type': 'string'},
            },
            'required': ['name', 'type', 'url']
        }
    },
    'required': ['tracker']
})
def create():
    tracker = request.json['tracker']
    if tracker['type'] not in ('jira', 'file', 'faulty'):
        return 'Bad tracker type', http.client.BAD_REQUEST

    tracker_model = Tracker(
        name=tracker['name'],
        type=tracker['type'],
        url=tracker['url'],
        config=tracker.get('config'))
    db.session.add(tracker_model)
    db.session.commit()

    return jsonify({'tracker': tracker_model.to_dict()})


@trackers.route('/<int:tracker>', methods=['DELETE'])
def delete(tracker):
    tracker = db.session.query(Tracker).filter_by(id=tracker).first()
    if not tracker:
        return 'Tracker not found', http.client.NOT_FOUND

    db.session.delete(tracker)
    db.session.commit()
    return ''


@trackers.route('/<int:tracker>', methods=['GET'])
def get(tracker):
    tracker = db.session.query(Tracker).filter_by(id=tracker).first()
    if not tracker:
        return 'Tracker not found', http.client.NOT_FOUND

    return jsonify({'tracker': tracker.to_dict()})


@trackers.route('', methods=['GET'], strict_slashes=False)
def get_all():
    tracker_models = db.session.query(Tracker)
    return jsonify({'trackers': [tracker.to_dict() for tracker in tracker_models]})


@trackers.route('/by_name/<tracker_name>', methods=['GET'])
def get_by_name(tracker_name):
    tracker = db.session.query(Tracker).filter_by(name=tracker_name).first()
    if not tracker:
        return 'Tracker not found', http.client.NOT_FOUND

    return jsonify({'tracker': tracker.to_dict()})


@trackers.route('/<int:tracker>', methods=['PUT'])
@validate_schema({
    'type': 'object',
    'properties': {
        'tracker': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'url': {'type': 'string'},
                'config': {'type': 'string'},
            },
        }
    },
    'required': ['tracker']
})
def update(tracker):
    tracker_data = request.json['tracker']
    tracker = db.session.query(Tracker).filter_by(id=tracker).first()
    if not tracker:
        return 'Tracker not found', http.client.NOT_FOUND

    if 'name' in tracker_data:
        tracker.name = tracker_data['name']

    if 'url' in tracker_data:
        tracker.url = tracker_data['url']

    if 'config' in tracker_data:
        tracker.config = tracker_data['config']

    db.session.commit()

    return jsonify({'tracker': tracker.to_dict()})
