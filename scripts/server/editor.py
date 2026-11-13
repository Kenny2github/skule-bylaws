from glob import glob

from werkzeug.exceptions import BadRequest
from flask import Blueprint, request

from .db import Proposal, Amendment
from .parse import jinja_env, validate_path, get_chapters
from .amend import apply_amendments

bp = Blueprint('editor', __name__)

index_template = jinja_env.get_template('server/index.jinja2')
proposal_template = jinja_env.get_template('server/proposal.jinja2')
proposal_file_template = jinja_env.get_template('server/proposal_file.jinja2')

@bp.route('/editor')
def index():
    if 'file' in request.args and 'proposal' in request.args:
        try:
            proposal_id = int(request.args['proposal'])
        except ValueError:
            pass
        else:
            return proposal_file(proposal_id, request.args['file'])
    if 'proposal' in request.args:
        try:
            proposal_id = int(request.args['proposal'])
        except ValueError:
            pass
        else:
            return proposal(proposal_id)
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 20))
    except ValueError:
        raise BadRequest('Non-integer offset/limit')
    if limit > 50:
        raise BadRequest('Limit too large')
    proposals = Proposal.page(offset, limit)
    return index_template.render(
        pending=[p for p in proposals if p.adopted is None],
        passed=[p for p in proposals if p.adopted is not None],
    )

def proposal(id: int):
    proposal = Proposal.get_or_404(id)
    amended_files = set(Amendment.get_paths(proposal))
    files = {}
    for filename in sorted(glob('**/*.md', recursive=True)):
        if 'README' in filename or 'LICENSE' in filename:
            continue
        files[filename] = filename in amended_files
    return proposal_template.render(
        proposal=proposal,
        files=files
    )

def proposal_file(id: int, path: str):
    proposal = Proposal.get_or_404(id)
    validate_path(proposal.base_ref, path)
    metadata, chapters = get_chapters(proposal.base_ref, path)
    amendments = Amendment.get_for_file(proposal, path)
    apply_amendments(chapters, amendments)
    return proposal_file_template.render(
        **metadata, chapters=chapters, proposal=proposal
    )
