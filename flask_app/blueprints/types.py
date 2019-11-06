from flask import Response
from typing import Union, Tuple

ServerResponse = Union[Response, Tuple[str, int]]
DBOperationResponse = Union[str, Tuple[str, int]]
