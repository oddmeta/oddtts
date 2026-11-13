from flask import Flask
from flask_cors import CORS

from .router.front import bp as bp_front
from .router.api import bp_api, load_voices

flask_app = Flask(__name__)
CORS(flask_app)
flask_app.register_blueprint(bp_api)
flask_app.register_blueprint(bp_front)

load_voices()