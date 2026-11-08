import os

from werkzeug.exceptions import Unauthorized
from flask import Blueprint, jsonify, request, session, g, redirect
from authlib.integrations.flask_client import OAuth

from .app import app

oauth = OAuth(app)

GOOGLE_TOKEN = 'google-token'
RETURN_TO = 'return-to'

bp = Blueprint('auth', __name__)

@bp.route('/oauth')
def oauth_start():
    meta_url = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='google',
        client_id=os.environ['GOOGLE_CLIENT_ID'],
        client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=meta_url,
        client_kwargs={'scope': 'openid email profile'}
    )
    session[RETURN_TO] = request.args.get('return_to', '/')
    return oauth.google.authorize_redirect(os.environ['GOOGLE_REDIRECT_URI'])

@bp.route('/oauth/callback')
def oauth_callback():
    session[GOOGLE_TOKEN] = oauth.google.authorize_access_token()
    return redirect(session.get(RETURN_TO, '/'))

def oauth_user():
    user = session.get(GOOGLE_TOKEN)
    if user is None:
        raise Unauthorized()
    return user['userinfo']

@bp.route('/oauth/verify')
def oauth_verify():
    return jsonify(oauth_user())

@bp.before_app_request
def verify_auth():
    if request.path.startswith('/oauth'):
        return
    g.user = oauth_user()
