import http
from flask import Blueprint, jsonify, abort
from ..models import db, User


users = Blueprint("users", __name__, template_folder="templates")


def _dictify_user(user):
    return {'user': {'id': user.id, 'email': user.email, 'name': user.name}}


@users.route('/by_email/<email>', methods=['GET'])
def get_by_email(email):
    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        abort(http.client.NOT_FOUND)

    return jsonify(_dictify_user(user))


@users.route('/<int:user_id>', methods=['GET'])
def get(user_id):
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        abort(http.client.NOT_FOUND)

    return jsonify(_dictify_user(user))
