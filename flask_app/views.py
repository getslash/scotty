import os
import logbook
import http.client
from datetime import datetime
from sqlalchemy.sql import func
from contextlib import closing
from paramiko.ssh_exception import SSHException
from flask import send_from_directory, jsonify, request
from datetime import datetime, timezone, time
from .models import Beam, db, File, User, Pin, Alias
from .tasks import beam_up, create_key, _COMBADGE
from .auth import require_user
from flask import Blueprint, current_app

views = Blueprint("views", __name__, template_folder="templates")

def _jsonify_beam(beam):
    return {
        'id': beam.id,
        'host': beam.host,
        'completed': beam.completed,
        'start': beam.start.isoformat() + 'Z',
        'size': beam.size,
        'initiator': beam.initiator,
        'purge_time': max(0, current_app.config['VACUUM_THRESHOLD'] - (datetime.utcnow() - datetime.combine(beam.start, time(0,0))).days) if beam.files else 0,
        'error': beam.error,
        'directory': beam.directory,
        'deleted': beam.pending_deletion or beam.deleted,
        'pins': [u.user_id for u in beam.pins]
    }


@views.route('/beams', methods=['GET'])
def get_beams():
    beams = [_jsonify_beam(b) for b in db.session.query(Beam).filter(Beam.pending_deletion == False, Beam.deleted == False)]
    return jsonify({'beams': beams})


@views.route('/beams', methods=['POST'])
@require_user(allow_anonymous=True)
def create_beam(user):
    if request.json['beam']['auth_method'] == 'rsa':
        try:
            create_key(request.json['beam']['ssh_key'])
        except SSHException as e:
            return 'Invalid RSA key', 409

    beam = Beam(
        start=datetime.utcnow(), size=0,
        host=request.json['beam']['host'],
        directory=request.json['beam']['directory'],
        initiator=user.id,
        error=None,
        pending_deletion=False, completed=False, deleted=False)
    db.session.add(beam)
    db.session.commit()

    if request.json['beam']['auth_method'] != 'independent':
        beam_up.delay(
            beam.id, beam.host, beam.directory, request.json['beam']['user'], request.json['beam']['auth_method'],
            request.json['beam'].get('ssh_key', None), request.json['beam'].get('password', ''))

    return jsonify({'beam': _jsonify_beam(beam)})



def _dictify_user(user):
    return {'user': {'id': user.id, 'email': user.email, 'name': user.name}}


@views.route('/users/by_email/<email>', methods=['GET'])
def get_user_by_email(email):
    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        return '', http.client.NOT_FOUND

    return jsonify(_dictify_user(user))


@views.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        return '', http.client.NOT_FOUND

    return jsonify(_dictify_user(user))


@views.route('/beams/<int:beam_id>', methods=['GET'])
def get_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    beam_json = _jsonify_beam(beam)
    beam_json['files'] = [f.id for f in beam.files]
    return jsonify(
        {'beam': beam_json,
         'files':
            [{"id": f.id, "file_name": f.file_name, "status": f.status, "size": f.size, "beam": beam.id,
              "storage_name": f.storage_name}
             for f in beam.files]})


@views.route('/beams/<int:beam_id>', methods=['PUT'])
def update_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if beam.pending_deletion or beam.deleted:
        return '', http.client.FORBIDDEN

    beam.completed = request.json['completed']
    beam.error = request.json.get('error', None)
    db.session.commit()

    return '{}'


@views.route('/aliases', methods=['POST'])
def create_alias():
    alias = request.json['alias']
    beam = db.session.query(Beam).filter_by(id=request.json['beam_id']).first()
    if not beam:
        return '', http.client.BAD_REQUEST

    alias = Alias(beam_id=beam.id, id=alias)
    db.session.add(alias)
    db.session.commit()

    return ""


@views.route('/alias/<alias_name>', methods=['GET'])
def get_alias(alias_name):
    alias = db.session.query(Alias).filter_by(id=alias_name).first()
    if not alias:
        return '', http.client.NOT_FOUND

    return jsonify({'beam_id': alias.beam_id})


@views.route('/alias/<alias_name>', methods=['DELETE'])
def delete_alias(alias_name):
    alias = db.session.query(Alias).filter_by(id=alias_name).first()
    if not alias:
        return '', http.client.NOT_FOUND

    db.session.delete(alias)
    db.session.commit()

    return ""


@views.route('/files', methods=['POST'])
def register_file():
    beam_id = request.json['beam_id']
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        logbook.error('Transporter attempted to post to unknown beam id {}', beam_id)
        return '', http.client.BAD_REQUEST

    if beam.pending_deletion or beam.deleted:
        return '', http.client.FORBIDDEN

    file_name = request.json['file_name']
    f = db.session.query(File, File.status, File.id).filter_by(beam_id=beam_id, file_name=file_name).first()
    if not f:
        logbook.info("Got upload request for a new file: {} @ {}", file_name, beam_id)
        f = File(beam_id=beam_id, file_name=file_name, size=None, status="pending")
        db.session.add(f)
        db.session.commit()
        f.storage_name = "{}-{}".format(f.id, f.file_name.replace("/", "__").replace("\\", "__"))
        db.session.commit()
    else:
        logbook.info("Got upload request for a existing file: {} @ {} ({})", file_name, beam_id, f.status)

    return jsonify({'file_id': str(f.id), 'should_beam': f.status != 'uploaded', 'storage_name': f.storage_name})


@views.route('/files/<int:file_id>', methods=['PUT'])
def update_file(file_id):
    success = request.json['success']
    size = request.json.get('size', None)
    f = db.session.query(File).filter_by(id=file_id).first()
    if not f:
        logbook.error('Transporter attempted to update an unknown file id {}', file_id)
        return '', http.client.BAD_REQUEST

    f.size = size
    f.status = "uploaded" if success else "failed"
    f.beam.size += size
    db.session.commit()

    return '{}'


@views.route('/pin', methods=['PUT'])
@require_user(allow_anonymous=False)
def pin(user):
    beam = db.session.query(Beam).filter_by(id=int(request.json['beam_id'])).first()
    if not beam:
        return '', NOT_FOUND

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
    beams = db.session.query(Beam).filter(Beam.pending_deletion == False, Beam.deleted == False)
    size = int(db.session.query(func.sum(Beam.size)).filter(Beam.pending_deletion == False, Beam.deleted == False)[0][0] or 0)
    oldest = beams.order_by(Beam.start).first()
    return jsonify({
        "space_usage": size,
        "oldest_beam": oldest.id if oldest else None,
        "number_of_beams":  beams.count()
    })



@views.route("/combadge")
def get_combadge():
    return _COMBADGE


@views.route("/")
def index():
    if not os.path.isdir(current_app.static_folder):
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'webapp', 'app'), 'index.html')
    return send_from_directory(current_app.static_folder, 'index.html')
