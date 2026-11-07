import os

from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ['SESSION_KEY']

if bool(int(os.environ.get('BEHIND_PROXY', False))):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
