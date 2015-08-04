import os
import logbook
import http.client
import urllib.parse
from jsonschema import Draft4Validator
from functools import wraps
from datetime import datetime, time
from sqlalchemy import distinct
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from paramiko.ssh_exception import SSHException
from flask import send_from_directory, jsonify, request, redirect, abort
from .models import Beam, db, File, User, Pin, Tag
from .tasks import beam_up, create_key
from .auth import require_user, get_or_create_user, InvalidEmail
from flask import Blueprint, current_app

views = Blueprint("views", __name__, template_folder="templates")


def validate_schema(schema):
    validator = Draft4Validator(schema)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.json:
                abort(http.client.BAD_REQUEST)

            try:
                validator.validate(request.json)
            except Exception as e:
                logbook.error(e)
                abort(http.client.BAD_REQUEST)

            return f(*args, **kwargs)
        return wrapper
    return decorator


def _jsonify_beam(beam):
    purge_time = (
        current_app.config['VACUUM_THRESHOLD'] - (datetime.utcnow() - datetime.combine(beam.start, time(0, 0))).days
        if beam.size else 0)
    purge_time = max(purge_time, 0)
    return {
        'id': beam.id,
        'host': beam.host,
        'completed': beam.completed,
        'start': beam.start.isoformat() + 'Z',
        'size': beam.size,
        'initiator': beam.initiator,
        'purge_time': purge_time,
        'error': beam.error,
        'directory': beam.directory,
        'deleted': beam.pending_deletion or beam.deleted,
        'pins': [u.user_id for u in beam.pins]
    }


@views.route('/beams', methods=['GET'])
def get_beams():
    query = (
        db.session.query(Beam)
        .options(joinedload(Beam.pins))
        .filter_by(pending_deletion=False, deleted=False)
        .order_by(Beam.start.desc()))
    if 'tag' in request.values:
        if 'pinned' in request.values:
            abort(http.client.BAD_REQUEST)
        tag = request.values['tag']
        query = query.filter(Beam.tags.any(Tag.tag == tag))
    if 'pinned' in request.values:
        if 'tags' in request.values:
            abort(http.client.BAD_REQUEST)

        pinned = db.session.query(distinct(Pin.beam_id))
        query = query.filter(Beam.id.in_(pinned))

    beams = [_jsonify_beam(b) for b in query.limit(50)]
    return jsonify({'beams': beams})


@views.route('/beams', methods=['POST'])
@require_user(allow_anonymous=True)
@validate_schema({
    'type': 'object',
    'properties': {
        'beam': {
            'type': 'object',
            'properties': {
                'auth_method': {'type': 'string', 'enum': ['rsa', 'password', 'independent']},
                'user': {'type': 'string'},
                'password': {'type': ['string', 'null']},
                'directory': {'type': 'string'},
                'email': {'type': 'string'},
                'ssh_key': {'type': ['string', 'null']},
            },
            'required': ['auth_method', 'host', 'directory']
        }
    },
    'required': ['beam']
})
def create_beam(user):
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

    beam = Beam(
        start=datetime.utcnow(), size=0,
        host=request.json['beam']['host'],
        directory=request.json['beam']['directory'],
        initiator=user.id,
        error=None,
        combadge_contacted=False,
        pending_deletion=False, completed=False, deleted=False)
    db.session.add(beam)
    db.session.commit()

    if request.json['beam']['auth_method'] != 'independent':
        beam_up.delay(
            beam.id, beam.host, beam.directory, request.json['beam']['user'], request.json['beam']['auth_method'],
            request.json['beam'].get('ssh_key', None), request.json['beam'].get('password', ''))

    return jsonify({'beam': _jsonify_beam(beam)})


def _strip_gz(storage_name):
    if storage_name is None:
        return None

    if storage_name[-6:] == "log.gz":
        return storage_name[:-3]
    else:
        return storage_name


def _dictify_file(f):
    url = (
        "{}/file_contents/{}".format(request.host_url, urllib.parse.quote(_strip_gz(f.storage_name)))
        if f.storage_name else None)
    return {"id": f.id, "file_name": f.file_name, "status": f.status, "size": f.size, "beam": f.beam_id,
            "storage_name": f.storage_name, "url": url}


def _dictify_user(user):
    return {'user': {'id': user.id, 'email': user.email, 'name': user.name}}


@views.route('/users/by_email/<email>', methods=['GET'])
def get_user_by_email(email):
    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        abort(http.client.NOT_FOUND)

    return jsonify(_dictify_user(user))


@views.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        abort(http.client.NOT_FOUND)

    return jsonify(_dictify_user(user))


@views.route('/beams/<int:beam_id>', methods=['GET'])
def get_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        return "No such beam", http.client.NOT_FOUND
    beam_json = _jsonify_beam(beam)
    beam_json['files'] = [f.id for f in beam.files]
    return jsonify({'beam': beam_json})


@views.route('/files/<int:file_id>', methods=['GET'])
def get_file(file_id):
    file_rec = db.session.query(File).filter_by(id=file_id).first()
    if not file_rec:
        return "No such file", http.client.NOT_FOUND
    return jsonify({'file': _dictify_file(file_rec)})


@views.route('/beams/<int:beam_id>/tags/<path:tag>', methods=['POST'])
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


@views.route('/tags')
def get_tags():
    tags = (
        db.session.query(Tag.tag, func.count(Tag.beam_id))
        .filter(Tag.beam.has(None, deleted=False))
        .group_by(Tag.tag)
        .limit(200))
    return jsonify({'tags': [{'id': tag[0], 'number_of_beams': tag[1]} for tag in tags]})


@views.route('/beams/<int:beam_id>/tags/<path:tag>', methods=['DELETE'])
def remove_tag(beam_id, tag):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    t = db.session.query(Tag).filter_by(beam_id=beam_id, tag=tag).first()
    if t:
        db.session.delete(t)
        db.session.commit()
    return ''


@views.route('/beams/<int:beam_id>', methods=['PUT'])
@validate_schema({
    'type': 'object',
    'properties': {
        'completed': {'type': 'boolean'},
        'error': {'type': ['string', 'null']}
    },
    'required': ['completed']
})
def update_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if beam.pending_deletion or beam.deleted:
        abort(http.client.FORBIDDEN)

    beam.completed = request.json['completed']
    beam.error = request.json.get('error', None)
    db.session.commit()

    return '{}'


def _assure_beam_dir(beam_id):
    dir_name = str(beam_id % 1000)
    full_path = os.path.join(current_app.config['STORAGE_PATH'], dir_name)
    if not os.path.isdir(full_path):
        os.mkdir(full_path)

    return dir_name


@views.route('/files', methods=['POST'])
@validate_schema({
    'type': 'object',
    'properties': {
        'beam_id': {'type': 'number'},
        'file_name': {'type': 'string'},
    },
    'required': ['beam_id', 'file_name']
})
def register_file():
    beam_id = request.json['beam_id']
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        logbook.error('Transporter attempted to post to unknown beam id {}', beam_id)
        abort(http.client.BAD_REQUEST)

    if beam.pending_deletion or beam.deleted:
        abort(http.client.FORBIDDEN)

    file_name = request.json['file_name']
    f = db.session.query(File).filter_by(beam_id=beam_id, file_name=file_name).first()
    if not f:
        logbook.info("Got upload request for a new file: {} @ {}", file_name, beam_id)
        f = File(beam_id=beam_id, file_name=file_name, size=None, status="pending")
        db.session.add(f)
        db.session.commit()
        f.storage_name = "{}/{}-{}".format(
            _assure_beam_dir(beam.id), f.id, f.file_name.replace("/", "__").replace("\\", "__"))
        db.session.commit()
    else:
        logbook.info("Got upload request for a existing file: {} @ {} ({})", file_name, beam_id, f.status)

    if not beam.combadge_contacted:
        beam.combadge_contacted = True
        db.session.commit()

    return jsonify({'file_id': str(f.id), 'should_beam': f.status != 'uploaded', 'storage_name': f.storage_name})


@views.route('/files/<int:file_id>', methods=['PUT'])
@validate_schema({
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean'},
        'size': {'type': ['number', 'null']},
    },
    'required': ['success']
})
def update_file(file_id):
    success = request.json['success']
    size = request.json.get('size', None)
    f = db.session.query(File).filter_by(id=file_id).first()
    if not f:
        logbook.error('Transporter attempted to update an unknown file id {}', file_id)
        abort(http.client.BAD_REQUEST)

    f.size = size
    f.status = "uploaded" if success else "failed"
    if size is not None:
        f.beam.size += size
    db.session.commit()

    return '{}'


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
def update_pin(user):
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
def info():
    return jsonify({
        'version': current_app.config['APP_VERSION'],
        'transporter': current_app.config['TRANSPORTER_HOST']
    })


@views.route("/summary")
def summary():
    beams = db.session.query(Beam).filter_by(pending_deletion=False, deleted=False)
    size = int(db.session.query(func.sum(Beam.size)).filter_by(pending_deletion=False, deleted=False)[0][0] or 0)
    oldest = beams.order_by(Beam.start).first()
    return jsonify({
        "space_usage": size,
        "oldest_beam": oldest.id if oldest else None,
        "number_of_beams": beams.count()
    })


@views.route("/combadge")
def get_combadge():
    return redirect("/static/assets/combadge.py")


@views.route("/")
def index():
    if not os.path.isdir(current_app.static_folder):
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'webapp', 'app'), 'index.html')
    return send_from_directory(current_app.static_folder, 'index.html')
