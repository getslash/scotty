import os
import http.client
import logbook
import psutil
from sqlalchemy.sql import func
from flask import Blueprint, current_app, send_from_directory, jsonify, request, redirect, abort, send_file, Response
from ..models import Beam, db, Pin, Tag, User
from .auth import require_user
from .utils import validate_schema

views = Blueprint("views", __name__, template_folder="templates")

@views.route('/tags')
def get_tags() -> Response:
    tags = (
        db.session.query(Tag.tag, func.count(Tag.beam_id))
        .filter(Tag.beam.has(None, deleted=False))
        .group_by(Tag.tag)
        .limit(200))
    return jsonify({'tags': [{'id': tag[0], 'number_of_beams': tag[1]} for tag in tags]})


@views.route('/pin', methods=['PUT'])
@require_user(allow_anonymous=False)
@validate_schema({
    'type': 'object',
    'properties': {
        'beam_id': {'type': 'number'},
        'should_pin': {'type': 'boolean'},
    },
    'required': ['beam_id', 'should_pin']
})
def update_pin(user: User) -> str:
    beam = db.session.query(Beam).filter_by(id=int(request.json['beam_id'])).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    pin = db.session.query(Pin).filter_by(user_id=user.id, beam_id=beam.id).first()
    if request.json['should_pin'] and not pin:
        logbook.info("{} is pinning {}", user.name, beam.id)
        db.session.add(Pin(user_id=user.id, beam_id=beam.id))
    elif not request.json['should_pin'] and pin:
        logbook.info("{} is unpinning {}", user.name, beam.id)
        db.session.delete(pin)

    db.session.commit()
    return ''


@views.route("/info")
def info() -> Response:
    return jsonify({
        'version': current_app.config['APP_VERSION'],
        'transporter': current_app.config['TRANSPORTER_HOST']
    })


@views.route("/summary")
def summary() -> Response:
    disk_usage = psutil.disk_usage(current_app.config['STORAGE_PATH'])
    return jsonify({
        "total_space": disk_usage.total,
        "used_space": disk_usage.used,
        "free_space": disk_usage.free,
    })


@views.route("/combadge")
def get_combadge() -> Response:
    return send_file("../webapp/dist/assets/combadge.py")
