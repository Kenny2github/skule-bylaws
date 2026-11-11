import sys
from dotenv import load_dotenv
sys.path.append('scripts')
load_dotenv()

from .app import app
from . import auth
from . import parse
from . import proposals

__all__ = [
    'app',
]

app.register_blueprint(auth.bp)
app.register_blueprint(parse.bp)
app.register_blueprint(proposals.bp)
