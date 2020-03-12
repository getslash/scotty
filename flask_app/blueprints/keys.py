import http.client
from typing import Union

from flask import Blueprint, Response, jsonify, request

from ..models import Key, db
from .utils import validate_schema

keys = Blueprint("keys", __name__, template_folder="templates")

@keys.route('', methods=['POST'])
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
def post() -> Union[str, int]:
    obj = request.json['key']
    if not obj["description"]:
        return http.client.BAD_REQUEST

    key = Key(description=obj["description"], key=obj['key'])
    assert key.description
    db.session.add(key)
    db.session.commit()
    return '{}'


@keys.route('', methods=['GET'], strict_slashes=False)
def get_all() -> Response:
    return jsonify({'keys': [k.to_dict() for k in db.session.query(Key)]})
