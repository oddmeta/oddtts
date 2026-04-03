from flask import Flask
from flask_cors import CORS

from oddtts.router.front import bp as bp_front
from oddtts.router.api import bp_api, load_voices

from oddtts.oddtts_log import setup_logger

logger = setup_logger(__name__)

app = Flask(__name__)
CORS(app)
app.register_blueprint(bp_api)
app.register_blueprint(bp_front)

load_voices()



