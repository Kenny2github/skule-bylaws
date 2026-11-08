from werkzeug.exceptions import UnsupportedMediaType
from flask import Blueprint, request
from mds_to_html import parse_lines

bp = Blueprint('parse', __name__)

@bp.route('/parse', methods=['POST'])
def parse():
    if not (request.content_type or '').startswith('text/markdown'):
        raise UnsupportedMediaType(
            'text/markdown required'
        )
    text = request.data.decode('utf8')
    return parse_lines(text)
