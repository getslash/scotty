import os
import logging
from contextlib import closing
from flask import send_from_directory, jsonify, request
from datetime import datetime, timezone
from .models import Beam, db, File
from .app import app


def _jsonify_beam(beam):
    return {
        'id': beam.id,
        'host': beam.host,
        'completed': beam.completed,
        'start': beam.start.replace(tzinfo=timezone.utc).timestamp(),
        'size': beam.size,
        'directory': beam.directory
    }


@app.route('/beams', methods=['GET'])
def get_beams():
    beams = [_jsonify_beam(b) for b in db.session.query(Beam)]
    return jsonify({'beams': beams})


@app.route('/beams', methods=['POST'])
def create_beam():
    beam = Beam(
        start=datetime.utcnow(), size=0,
        host=request.json['beam']['host'],
        directory=request.json['beam']['directory'],
        pending_deletion=False, completed=False)
    db.session.add(beam)
    db.session.commit()
    return jsonify({'beam': _jsonify_beam(beam)})


@app.route('/beams/<int:beam_id>', methods=['GET'])
def get_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    files = db.session.query(File).filter_by(beam_id=beam_id)
    return jsonify(
        {'beam':
            {'id': beam.id, 'host': beam.host, 'completed': beam.completed, 'start': beam.start, 'size': beam.size,
             'directory': beam.directory,
             'files': [{'id': f.id, 'path': f.file_name, 'size': f.size, 'status': f.status} for f in files]}})


@app.route('/beams/<int:beam_id>', methods=['PUT'])
def update_beam(beam_id):
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    beam.completed = request.json['completed']
    db.session.commit()

    return '{}'


@app.route('/files', methods=['POST'])
def register_file():
    beam_id = request.json['beam_id']
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        logging.error('Transporter attempted to post to unknown beam id %d', beam_id)
        return '', http.client.BAD_REQUEST

    size = request.json['file_size']
    file_name = request.json['file_name']
    f = db.session.query(File, File.status, File.id).filter_by(beam_id=beam_id, file_name=file_name).first()
    if not f:
        logging.info("Got upload request for a new file: %s @ %d", file_name, beam_id)
        f = File(beam_id=beam_id, file_name=file_name, size=size, status="pending")
        beam.size += size
        db.session.add(f)
        db.session.commit()
    else:
        logging.info("Got upload request for a existing file: %s @ %d (%s)", file_name, beam_id, f.status)

    return jsonify({'file_id': str(f.id), 'should_beam': f.status != 'uploaded'})


@app.route('/files/<int:file_id>', methods=['PUT'])
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



@app.route("/")
def index():
    if not os.path.isdir(app.static_folder):
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'webapp', 'app'), 'index.html')
    return send_from_directory(app.static_folder, 'index.html')
