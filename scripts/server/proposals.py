from werkzeug.exceptions import BadRequest
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
