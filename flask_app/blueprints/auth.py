import http.client
from functools import wraps

from apiclient.discovery import build
from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user, login_user, logout_user
from flask_security import SQLAlchemyUserDatastore
from httplib2 import Http
from itsdangerous import BadSignature, TimedSerializer
from oauth2client.client import flow_from_clientsecrets

from ..models import Role, User, db

auth = Blueprint("auth", __name__, template_folder="templates")

_MAX_TOKEN_AGE = 60 * 60 * 24 * 365

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


class InvalidEmail(Exception):
    pass


def _get_token_serializer():
    return TimedSerializer(current_app.config["SECRET_KEY"])


def _get_info(credentials):
    http_client = Http()
    if credentials.access_token_expired:
        credentials.refresh(http_client)
    credentials.authorize(http_client)
    service = build("oauth2", "v2", http=http_client)
    return service.userinfo().get().execute()


def get_or_create_user(email, name):
    user = user_datastore.get_user(email)
    if not user:
        user = user_datastore.create_user(email=email, name=name)
        user_datastore.db.session.commit()
    else:
        if name is not None and name != user.name:
            user.name = name
            user_datastore.db.session.commit()

    return user


@auth.route("/login", methods=["POST"])
def login():
    flow = flow_from_clientsecrets(
        filename=current_app.config["CLIENT_SECRET_PATH"],
        scope="https://www.googleapis.com/auth/userinfo.profile",
        redirect_uri=request.json["redirectUri"],
    )
    credentials = flow.step2_exchange(request.json["authorizationCode"])

    user_info = _get_info(credentials)
    user = get_or_create_user(user_info["email"], user_info["name"])
    token = _get_token_serializer().dumps({"user_id": user.id})
    login_user(user)

    return jsonify(
        {
            "id": user.id,
            "auth_token": token,
        }
    )


@auth.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()

    return ""


def _get_user_from_auth_token(auth_token):
    try:
        token_data = _get_token_serializer().loads(auth_token, max_age=_MAX_TOKEN_AGE)
    except BadSignature:
        abort(http.client.UNAUTHORIZED)

    return user_datastore.get_user(token_data["user_id"])


@auth.route("/restore", methods=["POST"])
def restore():
    user = _get_user_from_auth_token(request.json["auth_token"])
    if not user:
        abort(http.client.FORBIDDEN)

    assert user.id == request.json["id"]
    login_user(user)
    return jsonify(request.json)


def _get_anonymous_user():
    user = user_datastore.get_user("anonymous@getslash.github.io")
    if not user:
        user = user_datastore.create_user(email="anonymous@getslash.github.io", name="Anonymous")
        user_datastore.db.session.commit()

    return user


def require_user(allow_anonymous):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_token = request.headers.get("X-Authentication-Token")
            user = None
            if auth_token:
                user = _get_user_from_auth_token(auth_token)

            if current_user.is_authenticated:
                user = current_user

            test_email = request.headers.get("X-Scotty-Email")
            if current_app.config.get("DEBUG", False) and test_email:
                user = get_or_create_user(test_email, "Test user")

            if not user:
                if not allow_anonymous:
                    abort(http.client.FORBIDDEN)
                else:
                    user = _get_anonymous_user()

            kwargs["user"] = user
            return f(*args, **kwargs)

        return wrapper

    return decorator
