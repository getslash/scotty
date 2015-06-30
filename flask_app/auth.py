import re
import os
import http.client
from functools import wraps
from httplib2 import Http
from oauth2client.client import flow_from_clientsecrets
from apiclient.discovery import build
from flask import request, jsonify, Blueprint, current_app, abort
from flask.ext.security import SQLAlchemyUserDatastore
from .models import Role, User, db
from itsdangerous import TimedSerializer, BadSignature


auth = Blueprint("auth", __name__, template_folder="templates")

_MAX_TOKEN_AGE = 60 * 60 * 24 * 365

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


class InvalidEmail(Exception):
    pass


_EMAIL = re.compile("^.*?@infinidat.com$")


def _get_token_serializer():
    return TimedSerializer(current_app.config['SECRET_KEY'])


def _get_info(credentials):
    http_client = Http()
    if credentials.access_token_expired:
        credentials.refresh(http_client)
    credentials.authorize(http_client)
    service = build('oauth2', 'v2', http=http_client)
    return service.userinfo().get().execute()


def is_email_valid(email):
    return _EMAIL.search(email) is not None


def get_or_create_user(email, name):
    if not is_email_valid(email):
        raise InvalidEmail()

    user = user_datastore.get_user(email)
    if not user:
        user = user_datastore.create_user(
            email=email,
            name=name)
        user_datastore.db.session.commit()
    else:
        if name is not None and name != user.name:
            user.name = name
            user_datastore.db.session.commit()

    return user


@auth.route("/login", methods=['POST'])
def login():
    flow = flow_from_clientsecrets(
        os.path.join(os.path.dirname(__file__), 'client_secret.json'),
        scope="https://www.googleapis.com/auth/userinfo.profile",
        redirect_uri=request.host_url[:-1])
    credentials = flow.step2_exchange(request.json['authorizationCode'])

    user_info = _get_info(credentials)
    if user_info.get('hd') != 'infinidat.com':
        abort(http.client.UNAUTHORIZED)

    user = get_or_create_user(user_info['email'], user_info['name'])
    token = _get_token_serializer().dumps({'user_id': user.id})

    return jsonify({
        'id': user.id,
        'auth_token': token,
    })


def _get_user_from_auth_token(auth_token):
    try:
        token_data = _get_token_serializer().loads(auth_token, max_age=_MAX_TOKEN_AGE)
    except BadSignature:
        abort(http.client.UNAUTHORIZED)

    return user_datastore.get_user(token_data['user_id'])


@auth.route("/restore", methods=['POST'])
def restore():
    user = _get_user_from_auth_token(request.json['auth_token'])
    if not user:
        abort(http.client.FORBIDDEN)

    assert user.id == request.json['id']
    return jsonify(request.json)


def _get_anonymous_user():
    user = user_datastore.get_user("anonymous@infinidat.com")
    if not user:
        user = user_datastore.create_user(
            email="anonymous@infinidat.com",
            name="Anonymous")
        user_datastore.db.session.commit()

    return user


def require_user(allow_anonymous):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_token = request.headers.get('X-Authentication-Token')
            user = None
            if auth_token:
                user = _get_user_from_auth_token(auth_token)

            if not user:
                if not allow_anonymous:
                    abort(http.client.FORBIDDEN)
                else:
                    user = _get_anonymous_user()

            kwargs['user'] = user
            return f(*args, **kwargs)

        return wrapper
    return decorator
