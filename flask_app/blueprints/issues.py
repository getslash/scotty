import http
from typing import Tuple, Union

import sqlalchemy
from flask import Blueprint, Response, jsonify, request

from ..issue_trackers import is_valid_issue
from ..models import Issue, db
from .types import DBOperationResponse, ServerResponse
from .utils import validate_schema

issues = Blueprint("issues", __name__, template_folder="templates")


@issues.route("", methods=["POST"])
@validate_schema(
    {
        "type": "object",
        "properties": {
            "issue": {
                "type": "object",
                "properties": {
                    "tracker_id": {"type": "number"},
                    "id_in_tracker": {"type": "string"},
                },
                "required": ["tracker_id", "id_in_tracker"],
            }
        },
        "required": ["issue"],
    }
)
def create() -> ServerResponse:
    data = request.json["issue"]
    id_in_tracker = data["id_in_tracker"].strip()
    if not id_in_tracker:
        return "Invalid issue id", http.client.CONFLICT

    issue = Issue(tracker_id=data["tracker_id"], id_in_tracker=id_in_tracker, open=True)

    db.session.add(issue)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        issue = (
            db.session.query(Issue)
            .filter_by(tracker_id=data["tracker_id"], id_in_tracker=id_in_tracker)
            .first()
        )
        if not issue:
            raise
    return jsonify({"issue": issue.to_dict()})


@issues.route("/<int:issue>", methods=["DELETE"])
def delete(issue: int) -> DBOperationResponse:
    issue = db.session.query(Issue).filter_by(id=issue).first()
    if not issue:
        return "Issue not found", http.client.NOT_FOUND

    db.session.delete(issue)
    db.session.commit()
    return ""


@issues.route("/<int:issue>", methods=["GET"])
def get(issue: int) -> ServerResponse:
    issue_obj = db.session.query(Issue).filter_by(id=issue).first()
    if not issue_obj:
        return "Issue not found", http.client.NOT_FOUND

    return jsonify({"issue": issue_obj.to_dict()})


@issues.route("/get_by_tracker/", methods=["GET"])
def get_by_tracker() -> ServerResponse:
    id_in_tracker = request.args.get("id_in_tracker")
    tracker_id = request.args.get("tracker_id")
    if id_in_tracker is None:
        return "Invalid id in tracker", http.client.BAD_REQUEST
    if tracker_id is None:
        return "Invalid tracker id", http.client.BAD_REQUEST

    issue = (
        db.session.query(Issue)
        .filter_by(tracker_id=tracker_id, id_in_tracker=id_in_tracker)
        .first()
    )
    if not issue:
        return "Issue not found", http.client.NOT_FOUND

    return jsonify({"issue": issue.to_dict()})
