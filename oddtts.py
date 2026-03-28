import asyncio
import os
from flask import Flask, request, jsonify, send_file, Response, render_template_string
from flask_cors import CORS

import oddtts.oddtts_config as config
from oddtts.base_tts_driver import OddTTSDriver
from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams
from oddtts.router.front import bp as front_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(front_bp)

single_tts_driver = OddTTSDriver(config.oddtts_cfg['tts_type'])
voices = []
voice_map = {}
voice_options = []
voice_short_names = []


async def get_voices(type: ODDTTS_TYPE):
    return await single_tts_driver.get_voices(type=type)

async def generate_tts_file(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav"):
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    return await single_tts_driver.generate_tts_file(type=type, text=text, tts_params=tts_params)

async def generate_tts_bytes(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav"):
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    return await single_tts_driver.generate_tts_bytes(type=type, text=text, tts_params=tts_params)

async def generate_tts_stream(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav"):
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    async for chunk in single_tts_driver.generate_tts_stream(type=type, text=text, tts_params=tts_params):
        yield chunk

def load_voices():
    global voices, voice_map, voice_options
    import asyncio
    type = config.oddtts_cfg["tts_type"]
    voices = asyncio.run(get_voices(type))
    voice_map = {v["name"]: v for v in voices if v.get("name")}
    voice_options = [v["name"] for v in voices if v.get("name")]

load_voices()

# 健康检查
@app.route('/oddtts/health')
def health_check():
    return jsonify({"status": "healthy", "message": "API服务运行正常"})

# 1. 获取语音列表API
@app.route('/v1/audio/voice/list', methods=['GET'])
def api_get_voices():
    type = config.oddtts_cfg["tts_type"]
    return jsonify(asyncio.run(get_voices(type)))

# 2. 获取特定语音详情API
@app.route('/v1/audio/voice/list/<voice_name>', methods=['GET'])
def api_get_voice_details(voice_name):
    global voices
    if not voices:
        load_voices()
    for item in voices:
        if item.get("short_name") == voice_name:
            return jsonify(item)
    return jsonify({"error": f"Voice '{voice_name}' not found"}), 404

# 3. TTS生成API - 返回文件路径
@app.route('/api/oddtts/file', methods=['POST'])
def api_tts_file():
    global voices
    data = request.json
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")
    
    type = config.oddtts_cfg["tts_type"]
    try:
        audio_path = asyncio.run(generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format))
        return jsonify({"status": "success", "file_path": audio_path, "format": response_format})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. TTS生成API - 返回Base64编码
@app.route('/api/oddtts/base64', methods=['POST'])
def api_tts_base64():
    import base64
    data = request.json
    type = config.oddtts_cfg["tts_type"]
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")
    
    try:
        audio_bytes = asyncio.run(generate_tts_bytes(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format))
        base64_str = base64.b64encode(audio_bytes).decode('utf-8')
        return jsonify({"status": "success", "base64": base64_str, "format": response_format})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. TTS生成API - 流式响应
@app.route('/api/oddtts/stream', methods=['POST'])
def api_tts_stream():
    try:
        data = request.json
    except Exception:
        return jsonify({"error": "请求必须是JSON格式"}), 400
    
    type = config.oddtts_cfg["tts_type"]
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")
    
    if not text:
        return jsonify({"error": "缺少必需参数: text"}), 400
    if not voice:
        return jsonify({"error": "缺少必需参数: voice"}), 400
    
    async def async_generate():
        async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format):
            yield chunk
    
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async_gen = async_generate()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
                except Exception as e:
                    yield str(e).encode('utf-8')
                    break
        finally:
            loop.close()
    
    try:
        mimetype = "audio/mpeg" if response_format == "mp3" else "audio/wav"
        return Response(generate(), mimetype=mimetype)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 播放音频文件
@app.route('/play')
def play_audio():
    import urllib.parse
    file_path = request.args.get('path', '')
    if file_path:
        file_path = urllib.parse.unquote(file_path)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='audio/mpeg')
    return "File not found", 404

# 下载音频文件
@app.route('/download')
def download_audio():
    import urllib.parse
    file_path = request.args.get('path', '')
    if file_path:
        file_path = urllib.parse.unquote(file_path)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name='oddtts_audio.mp3', mimetype='audio/mpeg')
    return "File not found", 404

# OpenAI兼容API
@app.route('/v1/models', methods=['GET'])
def openai_list_models():
    type = config.oddtts_cfg["tts_type"]
    voice_list = asyncio.run(get_voices(type))
    models = []
    for v in voice_list:
        if v.get("name"):
            models.append({
                "id": v["name"],
                "object": "model",
                "created": 1700000000,
                "owned_by": "oddtts",
                "permission": [],
                "root": v["name"],
                "parent": None
            })
    return jsonify({
        "object": "list",
        "data": models,
        "model": type.value if hasattr(type, 'value') else str(type)
    })

@app.route('/v1/audio/speech', methods=['POST'])
def openai_create_speech():
    try:
        data = request.json
    except Exception:
        return jsonify({"error": "请求必须是JSON格式"}), 400
    
    text = data.get("input")
    if not text:
        return jsonify({"error": "缺少必需参数: input"}), 400
    
    voice = data.get("voice")
    if not voice:
        return jsonify({"error": "缺少必需参数: voice"}), 400
    
    speed = data.get("speed", 1.0)
    response_format = data.get("response_format", "mp3")
    
    if speed < 0.25 or speed > 4.0:
        return jsonify({"error": "speed参数必须在0.25-4.0之间"}), 400
    
    rate = int((speed - 1.0) * 50)

    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")

    type = config.oddtts_cfg["tts_type"]

    async def async_generate():
        async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=0, pitch=0, locale="zh-CN", response_format=response_format):
            yield chunk
    
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async_gen = async_generate()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
                except Exception as e:
                    yield str(e).encode('utf-8')
                    break
        finally:
            loop.close()
    
    try:
        mimetype = "audio/mpeg" if response_format == "mp3" else "audio/wav"
        return Response(generate(), mimetype=mimetype, headers={"Content-Disposition": f"attachment; filename=speech.{response_format}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500