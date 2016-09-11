import http.client
from flask import Blueprint, request, jsonify
from .utils import validate_schema
from ..models import db, Key


keys = Blueprint("keys", __name__, template_folder="templates")

@keys.route('/', methods=['POST'])
@validate_schema({
    'type': 'object',
    'properties': {
        'key': {
            'type': 'object',
            'properties': {
                'description': {'type': 'string'},
                'key': {'type': 'string'},
            },
            'required': ['description', 'key']
        }
    },
    'required': ['key']
})
def post():
    obj = request.json['key']
    if not obj["description"]:
        return http.client.BAD_REQUEST

    key = Key(description=obj["description"], key=obj['key'])
    assert key.description
    db.session.add(key)
    db.session.commit()
    return '{}'


@keys.route('/', methods=['GET'])
def get_all():
    return jsonify({'keys': [k.to_dict() for k in db.session.query(Key)]})
