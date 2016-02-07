import http
from sqlalchemy import distinct
from sqlalchemy.sql import false
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from paramiko.ssh_exception import SSHException
from flux import current_timeline
from flask import Blueprint, abort, request, current_app, jsonify
from .auth import require_user, get_or_create_user, InvalidEmail
from ..models import Beam, db, User, Pin, Tag, BeamType, Issue
from .utils import validate_schema, is_valid_hostname
from ..tasks import create_key, beam_up



beams = Blueprint("beams", __name__, template_folder="templates")


_ALLOWED_PARAMS = ['tag', 'pinned', 'uid', 'email']
@beams.route('', methods=['GET'])
def get_all():
    query = (
        db.session.query(Beam)
        .options(joinedload(Beam.pins), joinedload(Beam.type), joinedload(Beam.issues))
        .filter_by(pending_deletion=False, deleted=False)
        .order_by(Beam.start.desc()))
    query_params = []
    for param in request.values:
        if query_params or param not in _ALLOWED_PARAMS:
            abort(http.client.BAD_REQUEST)

        query_params.append(param)

    param = query_params[0] if query_params else None
    if param == "tag":
        tag = request.values['tag']
        query = query.filter(Beam.tags.any(Tag.tag == tag))
    elif param == "pinned":
        pinned = db.session.query(distinct(Pin.beam_id))
        query = query.filter(Beam.id.in_(pinned))
    elif param == "uid":
        try:
            uid = int(request.values['uid'])
        except ValueError:
            abort(http.client.BAD_REQUEST)
        query = query.filter_by(initiator=uid)
    elif param == "email":
        email = request.values['email']
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            query = query.filter(false())
        else:
            query = query.filter_by(initiator=user.id)

    beams_obj = [b.to_dict(current_app.config['VACUUM_THRESHOLD']) for b in query.limit(50)]
    return jsonify({'beams': beams_obj})


@beams.route('', methods=['POST'])
@require_user(allow_anonymous=True)
@validate_schema({
    'type': 'object',
    'properties': {
        'beam': {
            'type': 'object',
            'properties': {
                'auth_method': {'type': 'string', 'enum': ['rsa', 'password', 'independent']},
                'user': {'type': 'string'},
                'comment': {'type': ['string', 'null']},
                'type': {'type': ['string', 'null']},
                'password': {'type': ['string', 'null']},
                'directory': {'type': 'string'},
                'email': {'type': 'string'},
                'ssh_key': {'type': ['string', 'null']},
                'tags': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['auth_method', 'host', 'directory']
        }
    },
    'required': ['beam']
})
def create(user):
    if request.json['beam']['auth_method'] == 'rsa':
        try:
            create_key(request.json['beam']['ssh_key'])
        except SSHException:
            return 'Invalid RSA key', http.client.CONFLICT

    if user.is_anonymous_user:
        if 'email' in request.json['beam']:
            try:
                user = get_or_create_user(request.json['beam']['email'], None)
            except InvalidEmail:
                return 'Invalid email', http.client.CONFLICT

    if not is_valid_hostname(request.json['beam']['host']):
        return 'Invalid hostname', http.client.CONFLICT

    beam = Beam(
        start=current_timeline.datetime.utcnow(), size=0,
        host=request.json['beam']['host'],
        comment=request.json['beam'].get('comment'),
        directory=request.json['beam']['directory'],
        initiator=user.id,
        error=None,
        combadge_contacted=False,
        pending_deletion=False, completed=False, deleted=False)

    if request.json['beam'].get('type') is not None:
        type_obj = db.session.query(BeamType).filter_by(name=request.json['beam']['type']).first()
        if not type_obj:
            return 'Invalid beam type', http.client.CONFLICT

        beam.type = type_obj

    db.session.add(beam)
    db.session.commit()

    tags = request.json['beam'].get('tags')
    if tags:
        for tag in tags:
            t = Tag(beam_id=beam.id, tag=tag)
            db.session.add(t)
        db.session.commit()

    if request.json['beam']['auth_method'] != 'independent':
        beam_up.delay(
            beam.id, beam.host, beam.directory, request.json['beam']['user'], request.json['beam']['auth_method'],
            request.json['beam'].get('ssh_key', None), request.json['beam'].get('password', ''))

    return jsonify(
        {'beam': beam.to_dict(current_app.config['VACUUM_THRESHOLD'])})


@beams.route('/<int:beam_id>', methods=['GET'])
def get(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        return "No such beam", http.client.NOT_FOUND
    beam_json = beam.to_dict(current_app.config['VACUUM_THRESHOLD'])
    beam_json['files'] = [f.id for f in beam.files]
    return jsonify({'beam': beam_json})


@beams.route('/<int:beam_id>', methods=['PUT'])
@validate_schema({
    'type': 'object',
    'properties': {
        'beam': {'type': 'object'},
        'error': {'type': ['string', 'null']},
        'comment': {'type': ['string', 'null']}
    },
})
def update(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if beam.pending_deletion or beam.deleted:
        abort(http.client.FORBIDDEN)

    if 'beam' in request.json:
        if len(request.json) > 1:
            abort(http.client.CONFLICT)

        json = request.json['beam']
    else:
        json = request.json

    if 'completed' in request.json:
        beam.completed = json['completed']
        beam.error = json.get('error', None)

    if 'comment' in json:
        beam.comment = json['comment']

    db.session.commit()

    return '{}'


@beams.route('/<int:beam_id>/tags/<path:tag>', methods=['POST'])
def put_tag(beam_id, tag):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    t = Tag(beam_id=beam_id, tag=tag)
    db.session.add(t)
    try:
        db.session.commit()
    except IntegrityError:
        pass
    return ''


@beams.route('/<int:beam_id>/tags/<path:tag>', methods=['DELETE'])
def remove_tag(beam_id, tag):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    t = db.session.query(Tag).filter_by(beam_id=beam_id, tag=tag).first()
    if t:
        db.session.delete(t)
        db.session.commit()
    return ''


@beams.route('/<int:beam_id>/issues/<int:issue_id>', methods=['POST', 'DELETE'])
def set_issue_association(beam_id, issue_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    issue = db.session.query(Issue).filter_by(id=issue_id).first()
    if not issue:
        abort(http.client.NOT_FOUND)

    if request.method == 'POST':
        beam.issues.append(issue)
    elif request.method == 'DELETE':
        beam.issues.remove(issue)
    else:
        raise AssertionError()

    db.session.commit()
    return ''
