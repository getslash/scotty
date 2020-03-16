from typing import Tuple, Union

from flask import Response

ServerResponse = Union[Response, Tuple[str, int]]
DBOperationResponse = Union[str, Tuple[str, int]]
