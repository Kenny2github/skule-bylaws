import io
from pathlib import Path
import subprocess

import jinja2
from werkzeug.exceptions import UnsupportedMediaType, Forbidden, NotFound
from flask import Blueprint, request

from mds_to_html import get_data, parse_lines

bp = Blueprint('parse', __name__)

@bp.route('/parse', methods=['POST'])
def parse():
    if not (request.content_type or '').startswith('text/markdown'):
        raise UnsupportedMediaType(
            'text/markdown required'
        )
    text = request.data.decode('utf8')
    return parse_lines(text)

@bp.route('/parse/<string:ref>/<path:path>')
def parse_file(ref: str, path: str):
    if not path.endswith('.md'):
        raise NotFound()
    p = Path(path).resolve()
    if not p.is_relative_to(Path.cwd()):
        raise Forbidden()
    if not ref.translate({ord('-'): None}).isidentifier():
        raise Forbidden()
    try:
        content = subprocess.check_output(
            ['git', 'show', f'{ref}:{path}'],
            stderr=subprocess.STDOUT, encoding='utf8'
        )
    except subprocess.CalledProcessError as exc:
        raise NotFound(exc.output)
    metadata, chapters = get_data(io.StringIO(content))
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent.parent.absolute()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template('text.jinja2')
    return template.render(**metadata, chapters=chapters)
