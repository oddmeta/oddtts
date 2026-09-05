import os
import sys
import json
import time
import shutil
import subprocess
import importlib.util

import numpy as np

from oddtts.utils.model_utils import download_model, resolve_model_dir
from oddtts.oddtts_params import new_uuid, TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts.oddtts_log import setup_logger
from oddtts.voice_clone import get_voice_clone_manager

logger = setup_logger(__name__)

ONNX_REPO_ID = os.environ.get("AUDIO8_ONNX_REPO_ID", "Audio8/audio8-TTS-0.1B-ONNX-INT8")
OFFICIAL_REPO_DIR = "Audio8_TTS"
SAMPLE_RATE = 44100

ENGINE_NAME = "audio8_0_1b_onnx_int8"

Audio8_voices = {
    "default_voice": {
        "name": "default_voice",
        "gender": "Unknown",
        "locale": "zh-CN",
        "short_name": "default_voice",
    },
}


class Audio8_0_1b_OnnxInt8_API:

    def __init__(self) -> None:
        self.runtime = None

    async def preload(self) -> None:
        logger.info("[预加载] 开始预加载 Audio8 TTS 模型...")
        self._ensure_model()
        self._ensure_runtime()
        self._init_runtime()
        logger.info("[预加载] Audio8 TTS 模型预加载完成")

    async def get_voices(self) -> list[dict[str, str]]:
        voices_dir = self._voices_dir()
        if os.path.isdir(voices_dir):
            for name in os.listdir(voices_dir):
                meta_path = os.path.join(voices_dir, name, "meta.json")
                if os.path.isfile(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        Audio8_voices[name] = {
                            "name": name,
                            "gender": meta.get("gender", "Unknown"),
                            "locale": meta.get("locale", "zh-CN"),
                            "short_name": name,
                        }
                    except Exception:
                        pass

        # 合并 VoiceCloneManager 中的克隆音色
        try:
            manager = get_voice_clone_manager()
            for v in manager.list_voices(ENGINE_NAME):
                name = v["name"]
                if name not in Audio8_voices:
                    Audio8_voices[name] = {
                        "name": name,
                        "gender": v.get("gender", "Unknown"),
                        "locale": v.get("locale", "zh-CN"),
                        "short_name": name,
                        "is_cloned": True,
                    }
        except Exception as e:
            logger.warning(f"[Audio8] 获取克隆音色列表失败: {e}")

        return list(Audio8_voices.values())

    def _model_dir(self) -> str:
        from oddtts.oddtts_params import ODDTTS_TYPE
        return resolve_model_dir(ODDTTS_TYPE.ODDTTS_AUDIO8_0_1B_ONNX_INT8.model_key, env_var="AUDIO8_MODEL_DIR")

    def _repo_dir(self) -> str:
        # 1. 项目根目录（开发模式）
        repo_dir = os.path.join(os.path.dirname(__file__), "..", "..", OFFICIAL_REPO_DIR)
        if os.path.isdir(repo_dir):
            return repo_dir
        # 2. pip 安装后的 vendor 目录
        try:
            import oddtts
            pkg_dir = os.path.dirname(os.path.abspath(oddtts.__file__))
            vendor = os.path.join(pkg_dir, "vendor", OFFICIAL_REPO_DIR)
            if os.path.isdir(vendor):
                return vendor
        except Exception:
            pass
        return repo_dir

    def _runtime_dir(self) -> str:
        return os.path.join(self._repo_dir(), "onnx_runtime_0_1b_int8")

    def _voices_dir(self) -> str:
        return os.path.join(self._runtime_dir(), "voices")

    def _ensure_model(self):
        model_dir = self._model_dir()
        if os.path.isdir(model_dir) and os.path.isfile(os.path.join(model_dir, "slow_ar_int8.onnx")):
            logger.info(f"[Audio8] 模型已存在: {model_dir}")
            return
        logger.info(f"[Audio8] 开始下载 ONNX INT8 模型: {ONNX_REPO_ID}")
        for src in ["modelscope", "huggingface"]:
            try:
                download_model(repo_id=ONNX_REPO_ID, local_dir=model_dir, source=src)
                logger.info(f"[Audio8] 模型下载成功: {model_dir}")
                return
            except Exception as e:
                logger.warning(f"[Audio8] [{src}] 下载失败: {e}")
        raise RuntimeError(f"[Audio8] 模型下载失败，请手动下载 {ONNX_REPO_ID} 到 {model_dir}")

    def _ensure_runtime(self):
        repo_dir = self._repo_dir()
        if os.path.isdir(repo_dir) and os.path.isdir(self._runtime_dir()):
            logger.info(f"[Audio8] Runtime 已存在: {self._runtime_dir()}")
            return
        logger.info("[Audio8] 克隆官方仓库...")
        try:
            subprocess.check_call(
                ["git", "clone", "--depth", "1", "https://github.com/Audio8-AI/Audio8_TTS.git", repo_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("[Audio8] 仓库克隆成功")
        except Exception as e:
            raise RuntimeError(f"[Audio8] 仓库克隆失败: {e}")

    def _init_runtime(self):
        if self.runtime is not None:
            return

        self._ensure_model()
        self._ensure_runtime()

        runtime_dir = self._runtime_dir()
        if runtime_dir not in sys.path:
            sys.path.insert(0, runtime_dir)

        # 清理可能已被 0.6B runtime 缓存的 arktts_runtime 模块
        # 两个 runtime 共用模块名但实现不同，必须强制重新导入
        stale_keys = [k for k in sys.modules if k.startswith("arktts_runtime")]
        for k in stale_keys:
            del sys.modules[k]

        import pathlib
        _original_read_text = pathlib.Path.read_text

        def _patched_read_text(self, encoding=None, errors=None):
            if encoding is None:
                encoding = "utf-8"
            return _original_read_text(self, encoding=encoding, errors=errors)

        pathlib.Path.read_text = _patched_read_text

        try:
            from arktts_runtime.runtime import ArkTtsRuntime

            voices_dir = self._voices_dir()
            default_voice_dir = os.path.join(voices_dir, "default_voice")
            os.makedirs(default_voice_dir, exist_ok=True)

            ref_codes_src = os.path.join(self._model_dir(), "reference_codes.npy")
            ref_codes_dst = os.path.join(default_voice_dir, "codes.npy")
            meta_path = os.path.join(default_voice_dir, "meta.json")

            if os.path.exists(ref_codes_src) and not os.path.exists(ref_codes_dst):
                shutil.copy2(ref_codes_src, ref_codes_dst)
                logger.info("[Audio8] 已复制内置参考音色 codes.npy")

            if not os.path.exists(meta_path):
                ref_text = "Reference audio for voice cloning."
                manifest_path = os.path.join(self._model_dir(), "runtime_manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                        ref_text = manifest.get("reference_text", ref_text)
                    except Exception:
                        pass
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump({"name": "default_voice", "reference_text": ref_text}, f, ensure_ascii=False)
                logger.info("[Audio8] 已创建默认音色 meta.json")

            self.runtime = ArkTtsRuntime(
                model_dir=self._model_dir(),
                voices_dir=voices_dir,
            )
            logger.info(f"[Audio8] Runtime 初始化成功，采样率: {self.runtime.manifest['sample_rate']} Hz")
        except Exception as e:
            pathlib.Path.read_text = _original_read_text
            raise RuntimeError(f"[Audio8] Runtime 初始化失败: {e}")

    def _register_voice(self, voice_name: str, audio_path: str, reference_text: str = "") -> bool:
        """将参考音频注册为 Audio8 runtime 可用的音色。

        使用 VoiceRegistration 将音频编码为 codes.npy，存入 runtime 的 voices 目录。
        返回 True 表示注册成功。
        """
        if self.runtime is None:
            return False

        try:
            from arktts_runtime.registration import VoiceRegistration
        except ImportError:
            logger.warning("[Audio8] VoiceRegistration 模块不可用")
            return False

        try:
            reg = VoiceRegistration(
                registration_dir=self._model_dir(),
                voices_root=self._voices_dir(),
                model_fingerprint=str(self.runtime.manifest.get("model_fingerprint", "")),
            )
            status = reg.status()
            if not status["available"]:
                logger.warning(f"[Audio8] VoiceRegistration 不可用: {status['reason']}")
                return False

            with open(audio_path, "rb") as f:
                audio_data = f.read()

            if not reference_text:
                reference_text = "Reference audio for voice cloning."

            meta = reg.register(
                data=audio_data,
                filename=os.path.basename(audio_path),
                text=reference_text,
                name=voice_name,
                overwrite=True,
            )
            logger.info(f"[Audio8] 音色注册成功: {voice_name}, shape={meta.get('shape')}")
            return True
        except Exception as e:
            logger.warning(f"[Audio8] 音色注册失败 ({voice_name}): {e}")
            return False

    def _resolve_voice(self, tts_params: TTSParams) -> str:
        """解析音色名称，支持克隆音色和即时上传模式。

        优先级：
        1. prompt_audio_path（即时上传）→ 注册到 runtime 后使用
        2. 已注册的内置/runtime 音色
        3. VoiceCloneManager 中的克隆音色 → 注册到 runtime 后使用
        4. 回退到 default_voice
        """
        if self.runtime is None:
            self._init_runtime()

        # 1. 即时上传模式：prompt_audio_path
        prompt_audio_path = getattr(tts_params, "prompt_audio_path", None)
        if prompt_audio_path and os.path.isfile(prompt_audio_path):
            temp_name = f"_instant_{new_uuid()[:8]}"
            if self._register_voice(temp_name, prompt_audio_path):
                logger.info(f"[Audio8] 即时上传音色注册成功: {temp_name}")
                return temp_name
            logger.warning("[Audio8] 即时上传音色注册失败，回退到 default_voice")
            return "default_voice"

        # 2. 指定的音色名
        requested = tts_params.voice
        if requested:
            # 检查是否已在 runtime voices 目录中注册
            voice_dir = os.path.join(self._voices_dir(), requested)
            if os.path.isdir(voice_dir) and os.path.isfile(os.path.join(voice_dir, "codes.npy")):
                return requested

            # 3. 尝试从 VoiceCloneManager 查找克隆音色
            manager = get_voice_clone_manager()
            audio_path = manager.get_audio_path(ENGINE_NAME, requested)
            if audio_path and os.path.isfile(audio_path):
                if self._register_voice(requested, audio_path):
                    logger.info(f"[Audio8] 克隆音色注册成功: {requested}")
                    return requested
                logger.warning(f"[Audio8] 克隆音色注册失败: {requested}，回退到 default_voice")

        # 4. 回退
        return "default_voice"

    def _synthesize(self, text: str, tts_params: TTSParams) -> np.ndarray:
        if self.runtime is None:
            self._init_runtime()

        voice = self._resolve_voice(tts_params)

        max_new_tokens = 1024
        temperature = 0.7
        top_p = 0.9
        top_k = 50
        seed = 42

        start_time = time.time()
        audio, codes = self.runtime.synthesize(
            text=text,
            voice=voice,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            seed=seed,
        )
        elapsed = time.time() - start_time
        logger.info(f"[Audio8] 合成完成，耗时: {elapsed:.2f}s，音频时长: {len(audio) / SAMPLE_RATE:.2f}s")

        return audio.astype(np.float32)

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        logger.info(f"[Audio8] 生成语音文件: voice={tts_params.voice}, format={tts_params.response_format}")

        audio_numpy = self._synthesize(text, tts_params)

        output_format = tts_params.response_format if hasattr(tts_params, "response_format") else "wav"
        result = convert_ndarray_to_format(audio_numpy, SAMPLE_RATE, output_format)

        if isinstance(result, str):
            return result
        raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        logger.info(f"[Audio8] 生成语音字节流: voice={tts_params.voice}, format={tts_params.response_format}")

        audio_numpy = self._synthesize(text, tts_params)

        output_format = tts_params.response_format if hasattr(tts_params, "response_format") else "wav"
        result = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )

        if isinstance(result, bytes):
            return result
        raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        logger.info(f"[Audio8] 生成语音流: voice={tts_params.voice}, format={tts_params.response_format}")

        audio_numpy = self._synthesize(text, tts_params)

        output_format = tts_params.response_format if hasattr(tts_params, "response_format") else "wav"
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )

        yield audio_data
