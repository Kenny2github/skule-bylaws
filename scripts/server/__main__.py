import os
from dotenv import load_dotenv
load_dotenv()
from . import app

app.run(
    host='127.0.0.1',
    port=int(os.environ['FLASK_PORT']),
    debug=bool(int(os.environ.get('FLASK_DEBUG', False)))
)
