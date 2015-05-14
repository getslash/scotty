import re
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


class InvalidEmail(Exception):
    pass


_EMAIL = re.compile("^.*?@infinidat.com$")


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
        return '', http.client.UNAUTHORIZED

    user = get_or_create_user(user_info['email'], user_info['name'])

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
                    return "", http.client.FORBIDDEN
                else:
                    user = _get_anonymous_user()

            kwargs['user'] = user
            return f(*args, **kwargs)

        return wrapper
    return decorator
