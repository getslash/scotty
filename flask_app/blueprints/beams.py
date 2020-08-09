import http

from flask import Blueprint, Response, abort, current_app, jsonify, request
from flux import current_timeline
from paramiko.ssh_exception import SSHException
from sqlalchemy import distinct
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import false

from flask_app.utils.remote_host import create_key

from ..models import Beam, BeamType, Issue, Key, Pin, Tag, User, db
from ..tasks import beam_up, delete_beam
from .auth import InvalidEmail, get_or_create_user, require_user
from .types import ServerResponse
from .utils import is_valid_hostname, validate_schema

beams = Blueprint("beams", __name__, template_folder="templates")


_BEAMS_PER_PAGE = 50
_ALLOWED_PARAMS = ["tag", "pinned", "uid", "email", "page", "per_page"]


@beams.route("", methods=["GET"], strict_slashes=False)
def get_all() -> Response:
    if any({param not in _ALLOWED_PARAMS for param in request.values}):
        abort(http.client.BAD_REQUEST)

    beam_query = db.session.query(Beam).options(
        joinedload(Beam.pins), joinedload(Beam.type), joinedload(Beam.issues)
    )

    for param in request.values:
        param_values = request.values[param]
        if param == "tag":
            beam_query = beam_query.filter(
                Beam.tags.any(Tag.tag.in_(param_values.split(";")))
            )
        elif param == "pinned":
            pinned = db.session.query(distinct(Pin.beam_id))
            beam_query = beam_query.filter(Beam.id.in_(pinned))
        elif param == "uid":
            try:
                uid = int(param_values)
            except ValueError:
                abort(http.client.BAD_REQUEST)
            beam_query = beam_query.filter_by(initiator=uid)
        elif param == "email":
            user = db.session.query(User).filter_by(email=param_values).first()
            beam_query = (
                beam_query.filter_by(initiator=user.id)
                if user
                else beam_query.filter(false())
            )

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", _BEAMS_PER_PAGE, type=int)

    beams_obj = [
        b.to_dict(current_app.config["VACUUM_THRESHOLD"])
        for b in beam_query.order_by(Beam.id.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    ]

    total_pages = page + 1 if len(beams_obj) == per_page else page

    return jsonify({"beams": beams_obj, "meta": {"total_pages": total_pages}})


@beams.route("", methods=["POST"])
@require_user(allow_anonymous=True)
@validate_schema(
    {
        "type": "object",
        "properties": {
            "beam": {
                "type": "object",
                "properties": {
                    "auth_method": {
                        "type": "string",
                        "enum": ["rsa", "password", "independent", "stored_key"],
                    },
                    "user": {"type": "string"},
                    "comment": {"type": ["string", "null"]},
                    "type": {"type": ["string", "null"]},
                    "password": {"type": ["string", "null"]},
                    "directory": {"type": "string"},
                    "email": {"type": "string"},
                    "ssh_key": {"type": ["string", "null"]},
                    "stored_key": {"type": ["string", "null"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "combadge_version": {"type": "string"},
                },
                "required": ["auth_method", "host", "directory"],
            }
        },
        "required": ["beam"],
    }
)
def create(user: User) -> ServerResponse:
    ssh_key = None
    if request.json["beam"]["auth_method"] == "rsa":
        try:
            create_key(request.json["beam"]["ssh_key"])
            ssh_key = request.json["beam"]["ssh_key"]
        except SSHException:
            return "Invalid RSA key", http.client.CONFLICT
    elif request.json["beam"]["auth_method"] == "stored_key":
        if "stored_key" not in request.json["beam"]:
            return "No stored key was specified", http.client.CONFLICT
        key = (
            db.session.query(Key)
            .filter_by(id=int(request.json["beam"]["stored_key"]))
            .first()
        )
        if not key:
            return "Invalid stored key id", http.client.CONFLICT
        ssh_key = key.key

    if user.is_anonymous_user:
        if "email" in request.json["beam"]:
            try:
                user = get_or_create_user(request.json["beam"]["email"], None)
            except InvalidEmail:
                return "Invalid email", http.client.CONFLICT

    if not is_valid_hostname(request.json["beam"]["host"]):
        return "Invalid hostname", http.client.CONFLICT

    directory = request.json["beam"]["directory"]
    if directory == "/":
        return "Invalid beam directory", http.client.CONFLICT

    beam = Beam(
        start=current_timeline.datetime.utcnow(),
        size=0,
        host=request.json["beam"]["host"],
        comment=request.json["beam"].get("comment"),
        directory=directory,
        initiator=user.id,
        error=None,
        combadge_contacted=False,
        pending_deletion=False,
        completed=False,
        deleted=False,
    )

    if request.json["beam"].get("type") is not None:
        type_obj = (
            db.session.query(BeamType)
            .filter_by(name=request.json["beam"]["type"])
            .first()
        )
        if not type_obj:
            return "Invalid beam type", http.client.CONFLICT

        beam.type = type_obj

    db.session.add(beam)
    db.session.commit()

    tags = request.json["beam"].get("tags")
    if tags:
        for tag in tags:
            t = Tag(beam_id=beam.id, tag=tag)
            db.session.add(t)
        db.session.commit()

    if request.json["beam"]["auth_method"] != "independent":
        beam_up.delay(
            beam_id=beam.id,
            host=beam.host,
            directory=beam.directory,
            username=request.json["beam"]["user"],
            auth_method=request.json["beam"]["auth_method"],
            pkey=ssh_key,
            password=request.json["beam"].get("password", ""),
            combadge_version=request.json["beam"].get("combadge_version"),
        )

    return jsonify({"beam": beam.to_dict(current_app.config["VACUUM_THRESHOLD"])})


@beams.route("/<int:beam_id>", methods=["GET"])
def get(beam_id: int) -> ServerResponse:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        return "No such beam", http.client.NOT_FOUND
    beam_json = beam.to_dict(current_app.config["VACUUM_THRESHOLD"])
    beam_json["files"] = [f.id for f in beam.files]
    return jsonify({"beam": beam_json})


@beams.route("/<int:beam_id>", methods=["PUT"])
@validate_schema(
    {
        "type": "object",
        "properties": {
            "beam": {"type": "object"},
            "error": {"type": ["string", "null"]},
            "comment": {"type": ["string", "null"]},
        },
    }
)
def update(beam_id: int) -> str:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if beam.pending_deletion or beam.deleted:
        abort(http.client.FORBIDDEN)

    if "beam" in request.json:
        if len(request.json) > 1:
            abort(http.client.CONFLICT)

        json = request.json["beam"]
    else:
        json = request.json

    if "completed" in json:
        beam.set_completed(json["completed"])
        beam.error = json.get("error", None)

    if "comment" in json:
        beam.comment = json["comment"]

    db.session.commit()

    if "tags" in json:
        db.session.query(Tag).filter_by(beam_id=beam_id).delete()
        for tag in json["tags"]:
            db.session.add(Tag(beam_id=beam_id, tag=tag))

    try:
        db.session.commit()
    except IntegrityError:
        pass

    return "{}"


@beams.route("/<int:beam_id>", methods=["DELETE"])
def delete(beam_id: int) -> str:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)
    delete_beam.delay(beam_id=beam.id)
    return "{}"


@beams.route("/<int:beam_id>/tags/<path:tag>", methods=["POST"])
def put_tag(beam_id: int, tag: str) -> str:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    t = Tag(beam_id=beam_id, tag=tag)
    db.session.add(t)
    try:
        db.session.commit()
    except IntegrityError:
        pass
    return ""


@beams.route("/<int:beam_id>/tags/<path:tag>", methods=["DELETE"])
def remove_tag(beam_id: int, tag: str) -> str:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    t = db.session.query(Tag).filter_by(beam_id=beam_id, tag=tag).first()
    if t:
        db.session.delete(t)
        db.session.commit()
    return ""


@beams.route("/<int:beam_id>/issues/<int:issue_id>", methods=["POST", "DELETE"])
def set_issue_association(beam_id: int, issue_id: int) -> str:
    beam = db.session.query(Beam).filter_by(id=beam_id).first()
    if not beam:
        abort(http.client.NOT_FOUND)

    issue = db.session.query(Issue).filter_by(id=issue_id).first()
    if not issue:
        abort(http.client.NOT_FOUND)

    if request.method == "POST":
        beam.issues.append(issue)
    elif request.method == "DELETE":
        beam.issues.remove(issue)
    else:
        raise AssertionError()

    db.session.commit()
    return ""
