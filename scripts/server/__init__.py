from .app import app
from . import auth

__all__ = [
    'app',
]

app.register_blueprint(auth.bp, url_prefix='/api')
