import os
import io
import tempfile
import time

import requests
import numpy as np
import soundfile as sf

from oddtts.oddtts_params import new_uuid, TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts.oddtts_config import oddtts_cfg
from oddtts.oddtts_log import setup_logger
from oddtts.voice_clone import get_voice_clone_manager

logger = setup_logger(__name__)

ENGINE_NAME = "gptsovits"

# GPT-SoVITS API 默认地址（需用户本地启动推理服务，如: python api.py 或 python api_v2.py）
DEFAULT_GPTSOVITS_API_URL = "http://127.0.0.1:9880"

# 语言映射表: locale -> GPT-SoVITS 语言代码
LOCALE_TO_GSV_LANG = {
    "zh-CN": "zh",
    "zh-TW": "zh",
    "zh-HK": "yue",
    "en-US": "en",
    "en-GB": "en",
    "ja-JP": "ja",
    "ko-KR": "ko",
}

# 内置音色（GPT-SoVITS 本质依赖参考音频，此处预留扩展）
gptsovits_voices = {}


class OddGptSovitsAPI:
    """OddTTS GPT-SoVITS v2ProPlus 引擎封装。

    使用方式:
        1. 本地启动 GPT-SoVITS 推理服务（如: python api_v2.py）
        2. 在 oddtts_config.py / config.json 中配置 gptsovits_api_url
           （默认 http://127.0.0.1:9880）
        3. 通过 VoiceCloneManager 或 API 上传克隆音色（参考音频 + 参考文本）
        4. 调用 generate_tts_file / generate_tts_bytes 进行合成
    """

    def __init__(self) -> None:
        self.api_url = self._resolve_api_url()
        self.session = requests.Session()
        self._last_sample_rate = 32000

    def _resolve_api_url(self) -> str:
        """从配置或环境变量解析 GPT-SoVITS API 地址。"""
        url = oddtts_cfg.get("gptsovits_api_url", DEFAULT_GPTSOVITS_API_URL)
        env_url = os.environ.get("GPTSOVITS_API_URL")
        if env_url:
            url = env_url
        return url.rstrip("/")

    def _resolve_voice_and_prompt(self, tts_params: TTSParams) -> tuple[str | None, str | None]:
        """解析 voice -> (参考音频路径, 参考文本)。

        优先级:
            1. TTSParams.prompt_audio_path（即时上传 / API 指定）
            2. VoiceCloneManager 中已保存的克隆音色
            3. 默认回退（第一个可用克隆音色）
        """
        # 即时上传模式
        prompt_audio_path = getattr(tts_params, "prompt_audio_path", None)
        if prompt_audio_path and os.path.exists(prompt_audio_path):
            prompt_text = getattr(tts_params, "prompt_text", None)
            return prompt_audio_path, prompt_text

        requested = tts_params.voice
        manager = get_voice_clone_manager()

        # 查找指定音色
        prompt_path = manager.get_audio_path(ENGINE_NAME, requested)
        if prompt_path:
            prompt_text = manager.get_prompt_text(ENGINE_NAME, requested)
            logger.info(
                f"[GPT-SoVITS] 使用克隆音色: {requested}, 参考音频: {prompt_path}"
            )
            return prompt_path, prompt_text

        # 回退到第一个可用克隆音色
        cloned = manager.list_voices(ENGINE_NAME)
        if cloned:
            fallback = cloned[0]["name"]
            prompt_path = manager.get_audio_path(ENGINE_NAME, fallback)
            prompt_text = manager.get_prompt_text(ENGINE_NAME, fallback)
            logger.warning(
                f"[GPT-SoVITS] 未知音色 '{requested}'，回退到 '{fallback}'"
            )
            return prompt_path, prompt_text

        logger.warning("[GPT-SoVITS] 未找到任何克隆音色，将使用无参考模式")
        return None, None

    def _call_api(
        self,
        text: str,
        ref_audio_path: str | None,
        prompt_text: str | None,
        text_language: str,
        rate: int = 0,
    ) -> np.ndarray:
        """同步调用 GPT-SoVITS API，返回 numpy 音频数组。"""
        # 语速转换: rate(%) -> speed(倍速)
        speed = max(0.5, min(2.0, 1.0 + rate / 100))

        # prompt_lang 与 text_lang 保持一致
        prompt_lang = text_language

        payload: dict = {
            "text": text,
            "text_lang": text_language,
            "prompt_lang": prompt_lang,
            "speed_factor": speed,
        }

        if ref_audio_path and os.path.exists(ref_audio_path):
            payload["ref_audio_path"] = ref_audio_path
        if prompt_text:
            payload["prompt_text"] = prompt_text

        # 优先尝试 /tts 端点，再回退到 /
        endpoints = ["/tts", "/"]
        last_err = None
        resp = None
        for endpoint in endpoints:
            url = f"{self.api_url}{endpoint}"
            try:
                logger.info(
                    f"[GPT-SoVITS] 请求 {url}, 文本长度={len(text)}, speed={speed}"
                )
                resp = self.session.post(url, json=payload, timeout=300)
                resp.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if resp is not None and resp.status_code == 404:
                    last_err = e
                    continue
                raise RuntimeError(
                    f"[GPT-SoVITS] API HTTP 错误: {e}, 响应: {resp.text[:500] if resp else 'N/A'}"
                )
            except requests.exceptions.ConnectionError as e:
                raise RuntimeError(
                    f"[GPT-SoVITS] 无法连接到 GPT-SoVITS 服务 ({self.api_url})。"
                    f"请确保已启动推理服务（如: python api.py / api_v2.py）。详情: {e}"
                )
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"[GPT-SoVITS] API 请求异常: {e}")
        else:
            raise RuntimeError(f"[GPT-SoVITS] API 请求失败: {last_err}")

        # 解析返回的 WAV 音频
        audio_bytes = resp.content
        if not audio_bytes or len(audio_bytes) < 44:  # WAV 头最小 44 字节
            raise RuntimeError("[GPT-SoVITS] API 返回的音频数据为空或无效")

        with io.BytesIO(audio_bytes) as wav_buf:
            wav_buf.seek(0)
            audio, sr = sf.read(wav_buf, dtype=np.float32)

        self._last_sample_rate = sr

        # 统一为 2D 数组 (samples, channels)
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)

        return audio

    async def preload(self) -> None:
        """预加载: 检测 GPT-SoVITS API 服务是否可达。"""
        logger.info(f"[预加载] 检测 GPT-SoVITS API ({self.api_url})...")
        try:
            resp = self.session.get(self.api_url, timeout=5)
            logger.info(f"[预加载] GPT-SoVITS API 响应状态: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"[预加载] GPT-SoVITS API 未就绪 ({self.api_url})。"
                f"请启动推理服务后再使用该引擎。"
            )
        except Exception as e:
            logger.warning(f"[预加载] GPT-SoVITS API 检测异常: {e}")
        logger.info("[预加载] GPT-SoVITS 引擎预加载完成")

    async def get_voices(self) -> list[dict[str, str]]:
        """返回可用音色列表（内置 + 克隆）。"""
        builtin = list(gptsovits_voices.values())
        cloned = get_voice_clone_manager().list_voices(ENGINE_NAME)
        return builtin + cloned

    async def _generate_audio(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """生成语音，返回 numpy 音频数组。"""
        if not text:
            text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。Good good study, day day up."

        ref_audio_path, prompt_text = self._resolve_voice_and_prompt(tts_params)

        locale = getattr(tts_params, "locale", "zh-CN")
        text_language = LOCALE_TO_GSV_LANG.get(locale, "zh")

        start_time = time.time()
        audio = self._call_api(
            text=text,
            ref_audio_path=ref_audio_path,
            prompt_text=prompt_text,
            text_language=text_language,
            rate=getattr(tts_params, "rate", 0),
        )
        logger.info(f"[GPT-SoVITS] 合成完成，耗时: {time.time() - start_time:.2f}s")
        return audio

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        logger.info(
            f"[GPT-SoVITS] 生成语音文件: voice={tts_params.voice}, "
            f"locale={tts_params.locale}, format={tts_params.response_format}"
        )
        audio_numpy = await self._generate_audio(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav")
        result = convert_ndarray_to_format(
            audio_numpy, self._last_sample_rate, output_format
        )
        if isinstance(result, str):
            return result
        raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        logger.info(
            f"[GPT-SoVITS] 生成语音字节流: voice={tts_params.voice}, "
            f"format={tts_params.response_format}"
        )
        audio_numpy = await self._generate_audio(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav")
        result = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=self._last_sample_rate,
        )
        if isinstance(result, bytes):
            return result
        raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        logger.info(
            f"[GPT-SoVITS] 生成语音流: voice={tts_params.voice}, "
            f"format={tts_params.response_format}"
        )
        audio_numpy = await self._generate_audio(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav")
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=self._last_sample_rate,
        )
        yield audio_data
