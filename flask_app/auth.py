import random
import string
import os
import http.client
from functools import wraps
from httplib2 import Http
import logbook
from redis import StrictRedis
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
    redis = StrictRedis(host='localhost', port=6379, db=0)
    auth_token = redis.get("auth_tokens:{}".format(user.id))
    if not auth_token:
        auth_token = "".join([random.choice(string.ascii_letters) for i in range(50)])
        redis.set("auth_tokens:{}".format(user.id), auth_token)
        redis.set("users:{}".format(auth_token), user.id)
    else:
        auth_token = auth_token.decode("ASCII")
        assert int(redis.get("users:{}".format(auth_token))) == user.id

    login_user(user)
    return jsonify({
        'id': user.id,
        'auth_token': auth_token,
    })


def _get_user_from_auth_token(auth_token):
    redis = StrictRedis(host='localhost', port=6379, db=0)
    uid = int(redis.get("users:{}".format(auth_token)))
    if not uid:
        return None
    return user_datastore.get_user(uid)


@auth.route("/restore", methods=['POST'])
def restore():
    user = _get_user_from_auth_token(request.json['auth_token'])
    if not user:
        return '', http.client.FORBIDDEN

    assert user.id == request.json['id']
    return jsonify(request.json)


def require_user(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_token = request.headers.get('X-Authentication-Token')
        email = request.headers.get('X-Authentication-Email')
        user = None
        if auth_token:
            user = _get_user_from_auth_token(auth_token)
        elif email:
            user = user_datastore.get_user(email)

        if not user:
            return "", http.client.FORBIDDEN

        kwargs['user'] = user
        return f(*args, **kwargs)

    return wrapper
