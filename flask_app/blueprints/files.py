import os
import http
import urllib.parse
import logbook
from flux import current_timeline
from flask import Blueprint, request, jsonify, abort, current_app, Response
from typing import Mapping, Union, Tuple, Optional, Any
from .utils import validate_schema
from ..models import db, File, Beam


files = Blueprint("files", __name__, template_folder="templates")


_STRIPPED_EXTENSIONS = ["log", "json", "html", "xml", "sh", "txt", "ini", "conf",
                        "xslt", "mhtml", "pcap", "alerts_summary"]

def _assure_beam_dir(beam_id: int) -> str:
    dir_name = str(beam_id % 1000)
    full_path = os.path.join(current_app.config['STORAGE_PATH'], dir_name)
    if not os.path.isdir(full_path):
        os.mkdir(full_path)

    return dir_name


def _strip_gz(storage_name: str) -> str:
    if storage_name is None:
        return None

    for ext in _STRIPPED_EXTENSIONS:
        if storage_name.endswith(ext + ".gz"):
            return storage_name[:-3]

    return storage_name


def _dictify_file(f: File) -> Mapping[str, Optional[Any]]:   
    url = f"{request.host_url}/file_contents/{urllib.parse.quote(_strip_gz(f.storage_name))}" if f.storage_name else None
    mtime = None if f.mtime is None else f.mtime.isoformat() + 'Z'
    return {"id": f.id, 
            "file_name": f.file_name, 
            "status": f.status, 
            "size": f.size, 
            "beam": f.beam_id,
            "storage_name": f.storage_name, 
            "url": url, 
            "mtime": mtime}


@files.route('/<int:file_id>', methods=['GET'])
def get(file_id: int) -> Union[Response, Tuple[str, int]]:
    file_rec = db.session.query(File).filter_by(id=file_id).first()
    if not file_rec:
        return "No such file", http.client.NOT_FOUND
    return jsonify({'file': _dictify_file(file_rec)})


@files.route('', methods=['GET'])
def get_all() -> Response:
    if "beam_id" not in request.args:
        abort(http.client.BAD_REQUEST)

    try:
        beam_id = request.args['beam_id']
    except ValueError:
        abort(http.client.BAD_REQUEST)

    query = db.session.query(File).filter_by(beam_id=beam_id)

    if "filter" in request.args and request.args["filter"]:
        query = query.filter(File.file_name.like("%{}%".format(request.args['filter'])))

    query = query.order_by(File.file_name)

    total = query.count()

    if "offset" in request.args or "limit" in request.args:
        if not "offset" in request.args and "limit" in request.args:
            abort(http.client.BAD_REQUEST)

        try:
            offset = int(request.args['offset'])
            limit = int(request.args['limit'])
        except ValueError:
            abort(http.client.BAD_REQUEST)

        query = query.offset(offset).limit(limit)

    return jsonify({
        'files': [_dictify_file(f) for f in query],
        'meta': {'total': total}
    })


@files.route('', methods=['POST'])
@validate_schema({
    'type': 'object',
    'properties': {
        'beam_id': {'type': 'number'},
        'file_name': {'type': 'string'},
    },
    'required': ['beam_id', 'file_name']
})
def register_file() -> Response:
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
    else:
        logbook.info("Got upload request for a existing file: {} @ {} ({})", file_name, beam_id, f.status)

    if not f.storage_name:
        f.storage_name = "{}/{}-{}".format(
            _assure_beam_dir(beam.id), f.id, f.file_name.replace("/", "__").replace("\\", "__"))
        db.session.commit()

    if not beam.combadge_contacted:
        beam.combadge_contacted = True
        db.session.commit()

    return jsonify({'file_id': str(f.id), 'should_beam': f.status != 'uploaded', 'storage_name': f.storage_name})


@files.route('/<int:file_id>', methods=['PUT'])
@validate_schema({
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean'},
        'size': {'type': ['number', 'null']},
        'checksum': {'type': ['string', 'null']},
        'mtime': {'type': ['number', 'null']},
    },
    'required': ['success']
})
def update_file(file_id: int) -> str:
    success = request.json['success']
    size = request.json.get('size', None)
    f = db.session.query(File).filter_by(id=file_id).first()
    if not f:
        logbook.error('Transporter attempted to update an unknown file id {}', file_id)
        abort(http.client.BAD_REQUEST)

    mtime = request.json.get("mtime")
    if mtime is not None:
        mtime = current_timeline.datetime.utcfromtimestamp(mtime)

    f.size = size
    f.mtime = mtime
    f.checksum = request.json.get('checksum', None)
    f.status = "uploaded" if success else "failed"
    if size is not None:
        f.beam.size += size
    db.session.commit()

    return '{}'
