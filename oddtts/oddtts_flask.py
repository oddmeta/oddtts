from flask import Flask
from flask_cors import CORS
from flask_sock import Sock

from .router.front import bp as bp_front
from .router.api import bp_api, load_voices

flask_app = Flask(__name__)
# 显式配置 CORS：允许所有来源、方法、请求头，确保 OPTIONS 预检和 404/500 等错误响应也能正常跨域
CORS(flask_app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"], allow_headers="*", supports_credentials=False)
flask_app.register_blueprint(bp_api)
flask_app.register_blueprint(bp_front)

sock = Sock(flask_app)

# 注册 WebSocket 路由（避免循环导入，放在 sock 创建之后）
from .router.api import websocket_speech
sock.route('/v1/audio/speech/ws')(websocket_speech)

load_voices()