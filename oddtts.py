import asyncio
import os
import time
import logging
from flask import Flask, request, jsonify, send_file, Response, render_template_string
from flask_cors import CORS

import oddtts.oddtts_config as config
from oddtts.base_tts_driver import OddTTSDriver
from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams
from oddtts.router.front import bp as front_bp

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

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
    logger.debug(f"[辅助] generate_tts_file调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    return await single_tts_driver.generate_tts_file(type=type, text=text, tts_params=tts_params)

async def generate_tts_bytes(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav"):
    logger.debug(f"[辅助] generate_tts_bytes调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    return await single_tts_driver.generate_tts_bytes(type=type, text=text, tts_params=tts_params)

async def generate_tts_stream(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav"):
    logger.debug(f"[辅助] generate_tts_stream调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    tts_params = TTSParams(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format)
    async for chunk in single_tts_driver.generate_tts_stream(type=type, text=text, tts_params=tts_params):
        yield chunk

def load_voices():
    global voices, voice_map, voice_options
    logger.info("[系统] 开始加载语音列表")
    
    import asyncio
    type = config.oddtts_cfg["tts_type"]
    voices = asyncio.run(get_voices(type))
    voice_map = {v["name"]: v for v in voices if v.get("name")}
    voice_options = [v["name"] for v in voices if v.get("name")]
    
    logger.info(f"[系统] 语音列表加载完成 - 数量: {len(voices)}, 类型: {type}")

load_voices()

# 健康检查
@app.route('/oddtts/health')
def health_check():
    start_time = time.time()
    logger.info("[请求] 健康检查接口")
    
    result = jsonify({"status": "healthy", "message": "API服务运行正常"})
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] 健康检查完成 - 耗时: {elapsed_time:.3f}秒")
    
    return result

# 1. 获取语音列表API
@app.route('/v1/audio/voice/list', methods=['GET'])
def api_get_voices():
    start_time = time.time()
    logger.info("[请求] 获取语音列表接口")
    
    type = config.oddtts_cfg["tts_type"]
    voices_list = asyncio.run(get_voices(type))
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] 获取语音列表完成 - 语音数量: {len(voices_list)}, 耗时: {elapsed_time:.3f}秒")
    
    return jsonify(voices_list)

# 2. 获取特定语音详情API
@app.route('/v1/audio/voice/list/<voice_name>', methods=['GET'])
def api_get_voice_details(voice_name):
    start_time = time.time()
    logger.info(f"[请求] 获取语音详情接口 - 语音名称: {voice_name}")
    
    global voices
    if not voices:
        load_voices()
    
    for item in voices:
        if item.get("short_name") == voice_name:
            elapsed_time = time.time() - start_time
            logger.info(f"[响应] 获取语音详情成功 - 耗时: {elapsed_time:.3f}秒")
            return jsonify(item)
    
    elapsed_time = time.time() - start_time
    logger.warning(f"[响应] 语音未找到 - 语音名称: {voice_name}, 耗时: {elapsed_time:.3f}秒")
    return jsonify({"error": f"Voice '{voice_name}' not found"}), 404

# 3. TTS生成API - 返回文件路径
@app.route('/api/oddtts/file', methods=['POST'])
def api_tts_file():
    start_time = time.time()
    logger.info("[请求] TTS文件生成接口")
    
    global voices
    data = request.json
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")
    
    logger.info(f"[参数] 文本长度: {len(text) if text else 0}, 语音: {voice}, 语速: {rate}, 音量: {volume}, 音调: {pitch}, 格式: {response_format}")
    
    type = config.oddtts_cfg["tts_type"]
    try:
        audio_path = asyncio.run(generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format))
        
        elapsed_time = time.time() - start_time
        logger.info(f"[响应] TTS文件生成成功 - 文件路径: {audio_path}, 格式: {response_format}, 耗时: {elapsed_time:.3f}秒")
        
        return jsonify({"status": "success", "file_path": audio_path, "format": response_format})
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] TTS文件生成失败 - 错误信息: {str(e)}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500

# 4. TTS生成API - 返回Base64编码
@app.route('/api/oddtts/base64', methods=['POST'])
def api_tts_base64():
    start_time = time.time()
    logger.info("[请求] TTS Base64接口")
    
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
    
    logger.info(f"[参数] 文本长度: {len(text) if text else 0}, 语音: {voice}, 语速: {rate}, 音量: {volume}, 音调: {pitch}, 格式: {response_format}")
    
    try:
        audio_bytes = asyncio.run(generate_tts_bytes(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format))
        base64_str = base64.b64encode(audio_bytes).decode('utf-8')
        
        elapsed_time = time.time() - start_time
        logger.info(f"[响应] TTS Base64生成成功 - 数据大小: {len(audio_bytes)} bytes, 格式: {response_format}, 耗时: {elapsed_time:.3f}秒")
        
        return jsonify({"status": "success", "base64": base64_str, "format": response_format})
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] TTS Base64生成失败 - 错误信息: {str(e)}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500

# 5. TTS生成API - 流式响应
@app.route('/api/oddtts/stream', methods=['POST'])
def api_tts_stream():
    start_time = time.time()
    logger.info("[请求] TTS流式接口")
    
    try:
        data = request.json
    except Exception:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 请求格式错误 - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "请求必须是JSON格式"}), 400
    
    type = config.oddtts_cfg["tts_type"]
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    locale = data.get("locale", "zh-CN")
    response_format = data.get("response_format", "wav")
    
    logger.info(f"[参数] 文本长度: {len(text) if text else 0}, 语音: {voice}, 语速: {rate}, 音量: {volume}, 音调: {pitch}, 格式: {response_format}")
    
    if not text:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 缺少必需参数: text - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "缺少必需参数: text"}), 400
    if not voice:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 缺少必需参数: voice - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "缺少必需参数: voice"}), 400
    
    generation_start_time = time.time()
    
    async def async_generate():
        try:
            async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format):
                yield chunk
        
            generation_time = time.time() - generation_start_time
            logger.info(f"[完成] TTS流式生成完成 - 格式: {response_format}, 生成耗时: {generation_time:.3f}秒")
        except Exception as e:
            generation_time = time.time() - generation_start_time
            logger.error(f"[错误] TTS流式生成失败 - 错误信息: {str(e)}, 生成耗时: {generation_time:.3f}秒")
            yield str(e).encode('utf-8')
    
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
        elapsed_time = time.time() - start_time
        logger.info(f"[响应] TTS流式接口响应成功 - MIME类型: {mimetype}, 总耗时: {elapsed_time:.3f}秒")
        return Response(generate(), mimetype=mimetype)
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] TTS流式接口响应失败 - 错误信息: {str(e)}, 总耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500

# 播放音频文件
@app.route('/play')
def play_audio():
    start_time = time.time()
    logger.info("[请求] 播放音频接口")
    
    import urllib.parse
    file_path = request.args.get('path', '')
    
    logger.info(f"[参数] 文件路径: {file_path}")
    
    if file_path:
        file_path = urllib.parse.unquote(file_path)
        if os.path.exists(file_path):
            elapsed_time = time.time() - start_time
            logger.info(f"[响应] 播放音频成功 - 文件: {file_path}, 耗时: {elapsed_time:.3f}秒")
            return send_file(file_path, mimetype='audio/mpeg')
    
    elapsed_time = time.time() - start_time
    logger.warning(f"[响应] 文件未找到 - 路径: {file_path}, 耗时: {elapsed_time:.3f}秒")
    return "File not found", 404

# 下载音频文件
@app.route('/download')
def download_audio():
    start_time = time.time()
    logger.info("[请求] 下载音频接口")
    
    import urllib.parse
    file_path = request.args.get('path', '')
    
    logger.info(f"[参数] 文件路径: {file_path}")
    
    if file_path:
        file_path = urllib.parse.unquote(file_path)
        if os.path.exists(file_path):
            elapsed_time = time.time() - start_time
            logger.info(f"[响应] 下载音频成功 - 文件: {file_path}, 耗时: {elapsed_time:.3f}秒")
            return send_file(file_path, as_attachment=True, download_name='oddtts_audio.mp3', mimetype='audio/mpeg')
    
    elapsed_time = time.time() - start_time
    logger.warning(f"[响应] 文件未找到 - 路径: {file_path}, 耗时: {elapsed_time:.3f}秒")
    return "File not found", 404

# OpenAI兼容API
@app.route('/v1/models', methods=['GET'])
def openai_list_models():
    start_time = time.time()
    logger.info("[请求] OpenAI模型列表接口")
    
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
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] OpenAI模型列表完成 - 模型数量: {len(models)}, 耗时: {elapsed_time:.3f}秒")
    
    return jsonify({
        "object": "list",
        "data": models,
        "model": type.value if hasattr(type, 'value') else str(type)
    })

@app.route('/v1/audio/speech', methods=['POST'])
def openai_create_speech():
    start_time = time.time()
    logger.info("[请求] OpenAI speech接口")
    
    try:
        data = request.json
    except Exception:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 请求格式错误 - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "请求必须是JSON格式"}), 400
    
    text = data.get("input")
    if not text:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 缺少必需参数: input - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "缺少必需参数: input"}), 400
    
    voice = data.get("voice")
    if not voice:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 缺少必需参数: voice - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "缺少必需参数: voice"}), 400
    
    speed = data.get("speed", 1.0)
    response_format = data.get("response_format", "mp3")
    
    if speed < 0.25 or speed > 4.0:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] speed参数错误 - 值: {speed}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "speed参数必须在0.25-4.0之间"}), 400
    
    rate = int((speed - 1.0) * 50)
    locale = data.get("locale", "zh-CN")
    type = config.oddtts_cfg["tts_type"]
    
    logger.info(f"[参数] 文本长度: {len(text)}, 语音: {voice}, 语速: {speed}, 格式: {response_format}")
    
    generation_start_time = time.time()
    
    async def async_generate():
        try:
            async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=0, pitch=0, locale=locale, response_format=response_format):
                yield chunk
            
            generation_time = time.time() - generation_start_time
            logger.info(f"[完成] OpenAI speech生成完成 - 格式: {response_format}, 生成耗时: {generation_time:.3f}秒")
        except Exception as e:
            generation_time = time.time() - generation_start_time
            logger.error(f"[错误] OpenAI speech生成失败 - 错误信息: {str(e)}, 生成耗时: {generation_time:.3f}秒")
            yield str(e).encode('utf-8')
    
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
        elapsed_time = time.time() - start_time
        logger.info(f"[响应] OpenAI speech接口响应成功 - MIME类型: {mimetype}, 总耗时: {elapsed_time:.3f}秒")
        return Response(generate(), mimetype=mimetype, headers={"Content-Disposition": f"attachment; filename=speech.{response_format}"})
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] OpenAI speech接口响应失败 - 错误信息: {str(e)}, 总耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500