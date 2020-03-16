import http.client

import logbook
import psutil
from flask import (Blueprint, Response, abort, current_app, jsonify, request,
                   send_file)
from sqlalchemy.sql import func

from flask_app.utils.remote_combadge import DEFAULT_COMBADGE_VERSION

from ..models import Beam, Pin, Tag, User, db
from ..paths import get_combadge_path
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
    combadge_version = request.args.get('combadge_version', default=DEFAULT_COMBADGE_VERSION)
    os_type = request.args.get('os_type', default='linux')
    combadge_path = get_combadge_path(combadge_version, os_type=os_type)
    if combadge_path is None:
        abort(http.client.BAD_REQUEST)
    return send_file(combadge_path)
