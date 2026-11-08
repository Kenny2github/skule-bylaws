import sys
sys.path.append('scripts')
from .app import app
from . import auth
from . import parse

__all__ = [
    'app',
]

app.register_blueprint(auth.bp)
app.register_blueprint(parse.bp)
