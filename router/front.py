
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, send_file
from werkzeug.utils import secure_filename

import oddtts.oddtts_config as config

# from oddtts.log import logger
# from oddtts.router.odd_tts_session import session_required
# from oddtts.logic import hotwords, sensitivewords, users

bp = Blueprint('front', __name__, url_prefix='')


@bp.route('/')
def index():
    return render_template('index.html', servercfg=config, username=session.get("user", ""))
