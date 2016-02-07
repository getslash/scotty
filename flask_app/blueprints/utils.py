import re
import http
from functools import wraps
from jsonschema import Draft4Validator
import logbook
from flask import request, abort


def validate_schema(schema):
    validator = Draft4Validator(schema)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.json:
                abort(http.client.BAD_REQUEST)

            try:
                validator.validate(request.json)
            except Exception as e:
                logbook.error(e)
                abort(http.client.BAD_REQUEST)

            return f(*args, **kwargs)
        return wrapper
    return decorator


# https://stackoverflow.com/questions/2532053/validate-a-hostname-string?answertab=votes#tab-top
_ALLOWED_HOSTNAMES = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    return all(_ALLOWED_HOSTNAMES.match(x) for x in hostname.split("."))
