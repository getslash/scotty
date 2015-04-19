import os
import logging
import logbook
import http.client
from contextlib import closing
from flask import send_from_directory, jsonify, request
from datetime import datetime, timezone
from .models import Beam, db, File, User, Pin
from .tasks import beam_up, create_key
from .auth import require_user
from flask import Blueprint, current_app

views = Blueprint("views", __name__, template_folder="templates")

def _jsonify_beam(beam):
    return {
        'id': beam.id,
        'host': beam.host,
        'completed': beam.completed,
        'start': beam.start.isoformat(),
        'size': beam.size,
        'initiator': beam.initiator,
        'directory': beam.directory,
        'pins': [u.user_id for u in beam.pins]
    }


@views.route('/beams', methods=['GET'])
def get_beams():
    beams = [_jsonify_beam(b) for b in db.session.query(Beam).filter(Beam.pending_deletion == False, Beam.deleted == False)]
    return jsonify({'beams': beams})


@views.route('/beams', methods=['POST'])
@require_user
def create_beam(user):
    create_key(request.json['beam']['ssh_key'])

    beam = Beam(
        start=datetime.utcnow(), size=0,
        host=request.json['beam']['host'],
        directory=request.json['beam']['directory'],
        initiator=user.id,
        pending_deletion=False, completed=False, deleted=False)
    db.session.add(beam)
    db.session.commit()

    db.session.add(Pin(user_id=user.id, beam_id=beam.id))
    db.session.commit()

    beam_up.delay(
        beam.id, beam.host, beam.directory, request.json['beam']['user'], request.json['beam']['ssh_key'])
    return jsonify({'beam': _jsonify_beam(beam)})


@views.route('/beams/<int:beam_id>', methods=['DELETE'])
def delete_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    beam.pending_deletion = True
    db.session.commit()
    return '{}'


@views.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        return '', http.client.NOT_FOUND

    return jsonify({'user': {'id': user.id, 'email': user.email, 'name': user.name}})


@views.route('/beams/<int:beam_id>', methods=['GET'])
def get_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if beam.pending_deletion or beam.deleted:
        return '', http.client.FORBIDDEN

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
    db.session.commit()

    return '{}'


@views.route('/files', methods=['POST'])
def register_file():
    beam_id = request.json['beam_id']
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        logging.error('Transporter attempted to post to unknown beam id %d', beam_id)
        return '', http.client.BAD_REQUEST

    if beam.pending_deletion or beam.deleted:
        return '', http.client.FORBIDDEN

    size = request.json['file_size']
    file_name = request.json['file_name']
    f = db.session.query(File, File.status, File.id).filter_by(beam_id=beam_id, file_name=file_name).first()
    if not f:
        logging.info("Got upload request for a new file: %s @ %d", file_name, beam_id)
        f = File(beam_id=beam_id, file_name=file_name, size=size, status="pending")
        beam.size += size
        db.session.add(f)
        db.session.commit()
        f.storage_name = "{}-{}".format(f.id, f.file_name.replace("/", "__").replace("\\", "__"))
        db.session.commit()
    else:
        logging.info("Got upload request for a existing file: %s @ %d (%s)", file_name, beam_id, f.status)

    return jsonify({'file_id': str(f.id), 'should_beam': f.status != 'uploaded', 'storage_name': f.storage_name})


@views.route('/files/<int:file_id>', methods=['PUT'])
def update_file(file_id):
    success = request.json['success']
    error_string = request.json['error']
    f = db.session.query(File).filter_by(id=file_id).first()
    if not f:
        logging.error('Transporter attempted to update an unknown file id %d', file_id)
        return '', http.client.BAD_REQUEST

    f.status = "uploaded" if success else "failed"
    db.session.commit()

    return '{}'


@views.route('/pin', methods=['PUT'])
@require_user
def pin(user):
    beam = db.session.query(Beam).filter_by(id=int(request.json['beam_id'])).first()
    if not beam:
        return '', NOT_FOUND

    logbook.info("hio")
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
        'version': current_app.config['APP_VERSION']
    })


@views.route("/")
def index():
    if not os.path.isdir(current_app.static_folder):
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'webapp', 'app'), 'index.html')
    return send_from_directory(current_app.static_folder, 'index.html')
