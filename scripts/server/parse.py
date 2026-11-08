from werkzeug.exceptions import UnsupportedMediaType
from flask import Blueprint, request
import cmarkgfm
from mds_to_html import crossref

bp = Blueprint('parse', __name__)

@bp.route('/parse', methods=['POST'])
def parse():
    if not (request.content_type or '').startswith('text/markdown'):
        raise UnsupportedMediaType(
            'text/markdown required'
        )
    text = request.data.decode('utf8')
    return crossref(cmarkgfm.github_flavored_markdown_to_html(text)) \
        .removeprefix('<p>').removesuffix('</p>')
