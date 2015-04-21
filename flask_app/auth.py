import random
import string
import os
import http.client
from functools import wraps
from httplib2 import Http
import logbook
from oauth2client.client import flow_from_clientsecrets
from apiclient.discovery import build
from flask import request, jsonify, Blueprint
from flask.ext.security import SQLAlchemyUserDatastore
from flask_security.utils import verify_and_update_password, login_user
from flask_security.decorators import auth_token_required
from .app import create_app
from .models import Role, User, db


auth = Blueprint("auth", __name__, template_folder="templates")

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)

_USERS = {}
_SECRETS = {}


def _get_info(credentials):
    http_client = Http()
    if credentials.access_token_expired:
        credentials.refresh(http_client)
    credentials.authorize(http_client)
    service = build('oauth2', 'v2', http=http_client)
    return service.userinfo().get().execute()


@auth.route("/login", methods=['POST'])
def login():
    flow = flow_from_clientsecrets(
        os.path.join(os.path.dirname(__file__), 'client_secret.json'),
        scope="https://www.googleapis.com/auth/userinfo.profile",
        redirect_uri=request.host_url[:-1])
    credentials = flow.step2_exchange(request.json['authorizationCode'])

    user_info = _get_info(credentials)
    if user_info.get('hd') != 'infinidat.com':
        return '', http.client.UNAUTHORIZED

    user = user_datastore.get_user(user_info['email'])
    if not user:
        user = user_datastore.create_user(
            email=user_info['email'],
            name=user_info['name'])
        user_datastore.db.session.commit()

    user.credentials = credentials

    if user.id not in _SECRETS:
        secret = "".join([random.choice(string.ascii_letters) for i in range(50)])
        assert secret not in _USERS
        _USERS[secret] = user
        _SECRETS[user.id] = secret
    else:
        secret = _SECRETS[user.id]
        assert _USERS[secret].id == user.id

    login_user(user)
    return jsonify({
        'id': user.id,
        'secret': secret,
    })


@auth.route("/restore", methods=['POST'])
def restore():
    user = _USERS.get(request.json['secret'])
    if not user:
        return '', http.client.FORBIDDEN
    assert user.id == request.json['id']

    user_info = _get_info(user.credentials)
    if user.name != user_info['name']:
        user.name = user_info['name']
        request.json['name'] = user.name
        user_datastore.db.session.commit()

    return jsonify(request.json)


def require_user(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_token = request.headers.get('Authentication-Token')
        user = _USERS.get(auth_token)
        if not user:
            return "", http.client.FORBIDDEN

        kwargs['user'] = user
        return f(*args, **kwargs)

    return wrapper
