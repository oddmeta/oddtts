import asyncio
import io
import os
import time
import tempfile
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, send_file
from flask_cors import CORS
from flask import jsonify, Response
from werkzeug.utils import secure_filename

import oddtts.oddtts_config as config
from oddtts.models.base_tts_driver import OddTTSDriver
from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams
from oddtts.oddtts_log import logger
from oddtts.voice_clone import get_voice_clone_manager

single_tts_driver = OddTTSDriver(config.oddtts_cfg['tts_type'])

bp_api = Blueprint('api', __name__, url_prefix='')

voices = []
voice_map = {}
voice_options = []

def load_voices():
    global voices, voice_map, voice_options
    logger.info("[系统] 开始加载语音列表")
    
    import asyncio
    type = config.oddtts_cfg["tts_type"]
    voices = asyncio.run(get_voices(type))
    voice_map = {v["name"]: v for v in voices if v.get("name")}
    voice_options = [v["name"] for v in voices if v.get("name")]
    
    logger.info(f"[系统] 语音列表加载完成 - 数量: {len(voices)}, 类型: {type}")

async def get_voices(type: ODDTTS_TYPE):
    if single_tts_driver is None:
        return []
    return await single_tts_driver.get_voices(type=type)

async def generate_tts_file(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav", prompt_audio_path: str | None = None):
    logger.debug(f"[辅助] generate_tts_file调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    tts_params = TTSParams(voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path)
    if single_tts_driver is None:
        return ""
    return await single_tts_driver.generate_tts_file(tts_type=type, text=text, tts_params=tts_params)

async def generate_tts_bytes(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav", prompt_audio_path: str | None = None):
    logger.debug(f"[辅助] generate_tts_bytes调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    tts_params = TTSParams(voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path)
    if single_tts_driver is None:
        return ""
    return await single_tts_driver.generate_tts_bytes(tts_type=type, text=text, tts_params=tts_params)

async def generate_tts_stream(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav", prompt_audio_path: str | None = None):
    logger.debug(f"[辅助] generate_tts_stream调用 - 类型: {type}, 文本长度: {len(text)}, 语音: {voice}, 格式: {response_format}")
    if single_tts_driver is None:
        return
    tts_params = TTSParams(voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path)
    async for chunk in single_tts_driver.generate_tts_stream(tts_type=type, text=text, tts_params=tts_params):
        yield chunk



# 健康检查
@bp_api.route('/oddtts/health')
def health_check():
    start_time = time.time()
    logger.info("[请求] 健康检查接口")
    
    result = jsonify({"status": "healthy", "message": "API服务运行正常"})
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] 健康检查完成 - 耗时: {elapsed_time:.3f}秒")
    
    return result

# 1. 获取语音列表API
@bp_api.route('/v1/audio/voice/list', methods=['GET'])
def api_get_voices():
    start_time = time.time()
    logger.info("[请求] 获取语音列表接口")
    
    type = config.oddtts_cfg["tts_type"]
    voices_list = asyncio.run(get_voices(type))
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] 获取语音列表完成 - 语音数量: {len(voices_list)}, 耗时: {elapsed_time:.3f}秒")
    
    return jsonify(voices_list)

# 2. 获取特定语音详情API
@bp_api.route('/v1/audio/voice/list/<voice_name>', methods=['GET'])
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
@bp_api.route('/api/oddtts/file', methods=['POST'])
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
    
    prompt_audio_path = data.get("prompt_audio_path")
    
    type = config.oddtts_cfg["tts_type"]
    generation_start = time.time()
    try:
        audio_path = asyncio.run(generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path))
        generation_time = time.time() - generation_start

        # 计算音频时长和 RTF
        audio_duration = 0.0
        rtf = 0.0
        if audio_path and os.path.exists(audio_path):
            try:
                import soundfile as sf
                info = sf.info(audio_path)
                audio_duration = info.duration
                if audio_duration > 0:
                    rtf = generation_time / audio_duration
            except Exception:
                pass

        elapsed_time = time.time() - start_time
        logger.info(
            f"[响应] TTS文件生成成功 - 文件路径: {audio_path}, 格式: {response_format}, "
            f"总耗时: {elapsed_time:.3f}秒, 合成耗时: {generation_time:.3f}秒, "
            f"音频时长: {audio_duration:.2f}秒, RTF: {rtf:.3f}"
        )

        return jsonify({
            "status": "success",
            "file_path": audio_path,
            "format": response_format,
            "generation_time": round(generation_time, 3),
            "audio_duration": round(audio_duration, 2),
            "rtf": round(rtf, 3),
        })
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] TTS文件生成失败 - 错误信息: {str(e)}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500

# 4. TTS生成API - 返回Base64编码
@bp_api.route('/api/oddtts/base64', methods=['POST'])
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
    
    prompt_audio_path = data.get("prompt_audio_path")
    
    try:
        audio_bytes = asyncio.run(generate_tts_bytes(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path))
        if not audio_bytes:
            base64_str = ""
        else:
            base64_str = base64.b64encode(audio_bytes).decode('utf-8')
        
        elapsed_time = time.time() - start_time
        logger.info(f"[响应] TTS Base64生成成功 - 数据大小: {len(audio_bytes)} bytes, 格式: {response_format}, 耗时: {elapsed_time:.3f}秒")
        
        return jsonify({"status": "success", "base64": base64_str, "format": response_format})
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] TTS Base64生成失败 - 错误信息: {str(e)}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": str(e)}), 500

# 5. TTS生成API - 流式响应
@bp_api.route('/api/oddtts/stream', methods=['POST'])
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
    prompt_audio_path = data.get("prompt_audio_path")
    
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
            async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path):
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
@bp_api.route('/play')
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
@bp_api.route('/download')
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
@bp_api.route('/v1/models', methods=['GET'])
def openai_list_models():
    start_time = time.time()
    logger.info("[请求] OpenAI模型列表接口")
    
    type = config.oddtts_cfg["tts_type"]
    models = []
    models.append({
        "id": f"oddtts-{type.name}",
        "object": "model",
        "created": 1700000000,
        "owned_by": "oddtts",
        "permission": [],
        "root": type.name,
        "parent": None
    })
    
    elapsed_time = time.time() - start_time
    logger.info(f"[响应] OpenAI模型列表完成 - 模型数量: {len(models)}, 耗时: {elapsed_time:.3f}秒")
    
    return jsonify({
        "object": "list",
        "data": models,
        "model": type.value if hasattr(type, 'value') else str(type)
    })

@bp_api.route('/v1/audio/speech', methods=['POST'])
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
        if voice_options:
            voice = voice_options[0]
            logger.info(f"[参数] 未指定 voice，使用默认: {voice}")
        else:
            elapsed_time = time.time() - start_time
            logger.warning(f"[响应] 无可用音色 - 耗时: {elapsed_time:.3f}秒")
            return jsonify({"error": "无可用音色"}), 400
    
    speed = data.get("speed", 1.0)
    response_format = data.get("response_format", "mp3")
    
    if speed < 0.25 or speed > 4.0:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] speed参数错误 - 值: {speed}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"error": "speed参数必须在0.25-4.0之间"}), 400
    
    rate = int((speed - 1.0) * 50)
    locale = data.get("locale", "zh-CN")
    type = config.oddtts_cfg["tts_type"]
    prompt_audio_path = data.get("prompt_audio_path")
    
    logger.info(f"[参数] 文本长度: {len(text)}, 语音: {voice}, 语速: {speed}, 格式: {response_format}")
    
    generation_start_time = time.time()
    
    async def async_generate():
        audio_buffer = io.BytesIO()
        try:
            async for chunk in generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=0, pitch=0, locale=locale, response_format=response_format, prompt_audio_path=prompt_audio_path):
                audio_buffer.write(chunk)
                yield chunk
            
            generation_time = time.time() - generation_start_time

            # 计算音频时长和 RTF
            audio_duration = 0.0
            rtf = 0.0
            audio_buffer.seek(0)
            try:
                import soundfile as sf
                info = sf.info(audio_buffer)
                audio_duration = info.duration
                if audio_duration > 0:
                    rtf = generation_time / audio_duration
            except Exception:
                pass

            logger.info(
                f"[完成] OpenAI speech生成完成 - 格式: {response_format}, 生成耗时: {generation_time:.3f}秒, "
                f"音频时长: {audio_duration:.2f}秒, RTF: {rtf:.3f}"
            )
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

# 配置管理 API
@bp_api.route('/api/config/tts-types', methods=['GET'])
def api_get_tts_types():
    
    tts_types = []
    for t in ODDTTS_TYPE:
        tts_types.append({
            'value': t.value,
            'name': t.name,
            'description': t.description,
            'enable': t.enable
        })
    
    current_type = config.oddtts_cfg.get('tts_type')
    current_info = None
    if current_type:
        current_info = {
            'value': current_type.value,
            'name': current_type.name,
            'description': current_type.description,
            'enable': current_type.enable
        }
    
    return jsonify({
        'types': tts_types,
        'current': current_info
    })

@bp_api.route('/api/config/save', methods=['POST'])
def api_save_config():
    global single_tts_driver

    try:
        data = request.json
        tts_type_value = data.get('tts_type')
        
        if tts_type_value is None:
            return jsonify({'success': False, 'error': '缺少 tts_type 参数'}), 400
                
        try:
            tts_type = ODDTTS_TYPE(tts_type_value)
        except ValueError:
            return jsonify({'success': False, 'error': '无效的 TTS 类型'}), 400
        
        config_file_path = os.path.join(os.path.dirname(__file__), '..', 'oddtts_config.py')
        
        if not os.path.exists(config_file_path):
            return jsonify({'success': False, 'error': '配置文件不存在'}), 404
        
        with open(config_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        pattern = r'"tts_type":\s*ODDTTS_TYPE\.\w+'
        replacement = f'"tts_type": ODDTTS_TYPE.{tts_type.name}'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            if config.oddtts_cfg.get('tts_type') == tts_type:
                return jsonify({
                    'success': True,
                    'message': '配置已相同，无需更新'
                })
            else:
                return jsonify({'success': False, 'error': '未找到配置项'}), 400
        
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"[配置] TTS类型已更新: {tts_type.name}")
        
        # 更新内存中的配置
        config.oddtts_cfg['tts_type'] = tts_type
        
        # 重新初始化 TTS 驱动
        single_tts_driver = None
        single_tts_driver = OddTTSDriver(tts_type)
        
        # 预加载新引擎的模型（下载模型、克隆仓库、初始化 runtime）
        try:
            import asyncio
            asyncio.run(single_tts_driver.preload())
        except Exception as e:
            logger.warning(f"[配置] 新引擎预加载失败（可稍后自动重试）: {e}")
        
        # 重新加载语音列表
        load_voices()
        
        return jsonify({
            'success': True,
            'message': '配置已保存并已自动生效'
        })
        
    except Exception as e:
        logger.error(f"[错误] 保存配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# 音色克隆管理 API
# =============================================================================

@bp_api.route('/api/voice/clone', methods=['POST'])
def api_clone_voice():
    """上传参考音频并注册克隆音色（multipart/form-data）。

    Form 字段:
        - audio: 音频文件（wav/mp3/flac/m4a/ogg 等）
        - voice_id: 音色标识（必填，只允许字母/数字/下划线/连字符）
        - display_name: 展示名称（可选，默认同 voice_id）
        - engine: 引擎名（可选，默认从当前 TTS 类型推导）
        - locale: 语种（可选，默认 zh-CN）
        - gender: 性别（可选，默认 Unknown）
    """
    start_time = time.time()
    logger.info("[请求] 克隆音色上传接口")

    try:
        if "audio" not in request.files:
            return jsonify({"success": False, "error": "缺少音频文件字段: audio"}), 400

        audio_file = request.files["audio"]
        if audio_file.filename == "":
            return jsonify({"success": False, "error": "音频文件名为空"}), 400

        voice_id = request.form.get("voice_id", "").strip()
        if not voice_id:
            return jsonify({"success": False, "error": "缺少 voice_id 参数"}), 400

        display_name = request.form.get("display_name", voice_id).strip()
        engine = request.form.get("engine", "").strip()
        locale = request.form.get("locale", "zh-CN").strip()
        gender = request.form.get("gender", "Unknown").strip()

        # 未指定 engine 时，从当前 TTS 类型推导
        if not engine:
            current_type = config.oddtts_cfg.get("tts_type")
            if current_type == ODDTTS_TYPE.ODDTTS_MOSS_NANO:
                engine = "moss_nano"
            else:
                engine = current_type.name.lower().replace("oddtts_", "")

        # 保存上传文件到临时目录
        original_filename = secure_filename(audio_file.filename)
        tmp_dir = tempfile.mkdtemp(prefix="oddtts_clone_")
        tmp_path = os.path.join(tmp_dir, original_filename)
        audio_file.save(tmp_path)

        manager = get_voice_clone_manager()
        meta = manager.save_voice(
            engine=engine,
            voice_id=voice_id,
            display_name=display_name,
            audio_file_path=tmp_path,
            locale=locale,
            gender=gender,
        )

        # 清理临时文件
        try:
            import shutil
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

        # 重新加载语音列表，让新音色立即生效
        load_voices()

        elapsed_time = time.time() - start_time
        logger.info(f"[响应] 克隆音色上传成功 - engine={engine}, voice_id={voice_id}, 耗时: {elapsed_time:.3f}秒")

        return jsonify({
            "success": True,
            "voice": {
                "voice_id": meta["voice_id"],
                "display_name": meta["display_name"],
                "engine": meta["engine"],
                "locale": meta["locale"],
                "gender": meta["gender"],
                "created_at": meta["created_at"],
            },
        })

    except ValueError as e:
        elapsed_time = time.time() - start_time
        logger.warning(f"[响应] 克隆音色参数错误 - {e}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] 克隆音色上传失败 - {e}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": False, "error": str(e)}), 500


@bp_api.route('/api/voice/clone/list', methods=['GET'])
def api_list_cloned_voices():
    """列出所有克隆音色，可按 engine 筛选。"""
    start_time = time.time()
    logger.info("[请求] 克隆音色列表接口")

    try:
        engine = request.args.get("engine", "").strip() or None
        manager = get_voice_clone_manager()
        voices_list = manager.list_voices(engine)

        elapsed_time = time.time() - start_time
        logger.info(f"[响应] 克隆音色列表 - 数量: {len(voices_list)}, 耗时: {elapsed_time:.3f}秒")

        return jsonify({
            "success": True,
            "count": len(voices_list),
            "voices": voices_list,
        })
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] 克隆音色列表失败 - {e}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": False, "error": str(e)}), 500


@bp_api.route('/api/voice/clone/<engine>/<voice_id>', methods=['DELETE'])
def api_delete_cloned_voice(engine, voice_id):
    """删除指定克隆音色。"""
    start_time = time.time()
    logger.info(f"[请求] 删除克隆音色 - engine={engine}, voice_id={voice_id}")

    try:
        manager = get_voice_clone_manager()
        ok = manager.delete_voice(engine, voice_id)
        if not ok:
            return jsonify({"success": False, "error": "音色不存在或删除失败"}), 404

        # 重新加载语音列表
        load_voices()

        elapsed_time = time.time() - start_time
        logger.info(f"[响应] 克隆音色删除成功 - 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": True, "message": "音色已删除"})
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] 克隆音色删除失败 - {e}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": False, "error": str(e)}), 500


@bp_api.route('/api/voice/clone/audio/<engine>/<voice_id>', methods=['GET'])
def api_play_cloned_voice_audio(engine, voice_id):
    """试听克隆音色的参考音频。"""
    start_time = time.time()
    logger.info(f"[请求] 试听克隆音色参考音频 - engine={engine}, voice_id={voice_id}")

    try:
        manager = get_voice_clone_manager()
        audio_path = manager.get_audio_path(engine, voice_id)
        if not audio_path or not os.path.exists(audio_path):
            return jsonify({"success": False, "error": "参考音频不存在"}), 404

        elapsed_time = time.time() - start_time
        logger.info(f"[响应] 返回参考音频 - 路径: {audio_path}, 耗时: {elapsed_time:.3f}秒")
        return send_file(audio_path, mimetype="audio/wav")
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[错误] 试听克隆音色失败 - {e}, 耗时: {elapsed_time:.3f}秒")
        return jsonify({"success": False, "error": str(e)}), 500