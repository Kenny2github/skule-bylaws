from werkzeug.exceptions import (
    BadRequest, Forbidden, UnsupportedMediaType,
    RequestEntityTooLarge, UnprocessableEntity
)
from flask import Blueprint, request, jsonify

from .db import Proposal

bp = Blueprint('proposals', __name__)

@bp.route('/proposals', methods=['GET'])
def proposals():
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 20))
    except ValueError:
        raise BadRequest('Non-integer offset/limit')
    if limit > 50:
        raise BadRequest('Limit too large')
    return jsonify(Proposal.page(offset, limit))

@bp.route('/proposals', methods=['PUT'])
def new_proposal():
    if not (request.content_type or '').startswith('text/plain'):
        raise UnsupportedMediaType(
            'text/markdown required'
        )
    if (request.content_length or 1024) > 512:
        raise RequestEntityTooLarge('max 512')
    summary = request.data.decode('utf8')
    proposal = Proposal.add(summary)
    return jsonify(proposal)

@bp.route('/proposals/<int:id>', methods=['PATCH'])
def update_proposal(id: int):
    updates = request.json
    if not isinstance(updates, dict):
        raise UnprocessableEntity(f'{type(updates)!r}')
    proposal = Proposal.get_or_404(id)
    try:
        proposal.update(**updates)
    except TypeError as exc:
        raise Forbidden(str(exc)) from None
    return jsonify(proposal)
