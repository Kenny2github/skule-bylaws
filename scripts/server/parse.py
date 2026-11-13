import io
from pathlib import Path
import re
import subprocess

import jinja2
from werkzeug.exceptions import UnsupportedMediaType, Forbidden, NotFound
from flask import Blueprint, jsonify, request

from mds_to_html import Section, get_data, parse_lines

bp = Blueprint('parse', __name__)

@bp.route('/parse', methods=['POST'])
def parse():
    if not (request.content_type or '').startswith('text/markdown'):
        raise UnsupportedMediaType(
            'text/markdown required'
        )
    text = request.data.decode('utf8')
    return parse_lines(text)

def validate_path(ref: str, path: str) -> None:
    if not path.endswith('.md'):
        raise NotFound()
    p = Path(path).resolve()
    if not p.is_relative_to(Path.cwd()):
        raise Forbidden()
    if not re.match(r'^[0-9a-zA-Z_-]+$', ref):
        raise Forbidden()

def get_chapters(ref: str, path: str) -> tuple[dict[str, str], list[Section]]:
    try:
        content = subprocess.check_output(
            ['git', 'show', f'{ref}:{path}'],
            stderr=subprocess.STDOUT, encoding='utf8'
        )
    except subprocess.CalledProcessError as exc:
        raise NotFound(exc.output)
    return get_data(io.StringIO(content))

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).parent.parent.absolute()),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=True,
)
text_template = jinja_env.get_template('text.jinja2')

def parse_chapters(metadata: dict[str, str], chapters: list[Section]):
    return text_template.render(**metadata, chapters=chapters)

@bp.route('/parse/<string:ref>/<path:path>')
def parse_file(ref: str, path: str):
    validate_path(ref, path)
    metadata, chapters = get_chapters(ref, path)
    return jsonify(
        meta=metadata,
        html=parse_chapters(metadata, chapters)
    )
