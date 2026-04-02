
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, send_file
from werkzeug.utils import secure_filename

import oddtts.oddtts_config as config

# from oddtts.log import logger

bp = Blueprint('front', __name__, url_prefix='')

@bp.route('/favicon.ico')
def favicon():
    return send_file('static/favicon.ico')
@bp.route('/')
def index():
    return render_template('index.html', servercfg=config, username=session.get("user", ""))
