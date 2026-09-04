import os
import sys
import tempfile
import importlib.util

import numpy as np

from oddtts.utils.model_utils import download_model
from oddtts.oddtts_params import TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts.oddtts_log import setup_logger
from oddtts.voice_clone import get_voice_clone_manager

logger = setup_logger(__name__)

# 引擎标识（用于 VoiceCloneManager）
ENGINE_NAME = "moss_nano"

# 模型下载配置（优先 ModelScope，回退 HuggingFace）
TTS_MODELSCOPE_ID = "openmoss/MOSS-TTS-Nano-100M-ONNX"
TTS_HF_ID = "OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX"
CODEC_MODELSCOPE_ID = "openmoss/MOSS-Audio-Tokenizer-Nano-ONNX"
CODEC_HF_ID = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"

MODEL_DIR = os.path.abspath(os.path.join("models", "moss_tts_nano"))
SAMPLE_RATE = 48000

# 内置音色列表
MossNano_voices = {
    "Junhao": {
        "name": "Junhao",
        "gender": "Male",
        "locale": "zh-CN",
        "short_name": "Junhao",
    },
}


def _get_vendor_dir() -> str | None:
    """获取 pip 安装后 vendoring 的 moss-tts-nano 目录"""
    try:
        import oddtts
        pkg_dir = os.path.dirname(os.path.abspath(oddtts.__file__))
        vendor = os.path.join(pkg_dir, "vendor", "moss-tts-nano")
        if os.path.isdir(vendor):
            return vendor
    except Exception:
        pass
    return None


class MossNanoAPI:
    """MOSS-TTS-Nano 0.1B ONNX 引擎 API"""

    def __init__(self) -> None:
        self.runtime = None

    def _ensure_models(self) -> None:
        """确保 ONNX 模型已下载（优先 ModelScope）"""
        os.makedirs(MODEL_DIR, exist_ok=True)

        tts_dir = os.path.join(MODEL_DIR, "MOSS-TTS-Nano-100M-ONNX")
        codec_dir = os.path.join(MODEL_DIR, "MOSS-Audio-Tokenizer-Nano-ONNX")

        # 检查并下载 TTS 模型
        manifest_path = os.path.join(tts_dir, "browser_poc_manifest.json")
        if os.path.isfile(manifest_path):
            logger.info(f"[MossNano] TTS 模型已存在: {tts_dir}")
        else:
            logger.info("[MossNano] 开始下载 TTS ONNX 模型...")
            for repo_id in [TTS_MODELSCOPE_ID, TTS_HF_ID]:
                try:
                    download_model(repo_id=repo_id, local_dir=tts_dir, source="auto")
                    logger.info(f"[MossNano] TTS 模型下载成功: {repo_id}")
                    break
                except Exception as e:
                    logger.warning(f"[MossNano] [{repo_id}] 下载失败: {e}")
            else:
                raise RuntimeError("[MossNano] TTS ONNX 模型下载失败，请检查网络或手动下载")

        # 检查并下载 Codec 模型
        if os.path.isdir(codec_dir) and any(os.scandir(codec_dir)):
            logger.info(f"[MossNano] Codec 模型已存在: {codec_dir}")
        else:
            logger.info("[MossNano] 开始下载 Codec ONNX 模型...")
            for repo_id in [CODEC_MODELSCOPE_ID, CODEC_HF_ID]:
                try:
                    download_model(repo_id=repo_id, local_dir=codec_dir, source="auto")
                    logger.info(f"[MossNano] Codec 模型下载成功: {repo_id}")
                    break
                except Exception as e:
                    logger.warning(f"[MossNano] [{repo_id}] 下载失败: {e}")
            else:
                raise RuntimeError("[MossNano] Codec ONNX 模型下载失败，请检查网络或手动下载")

    def _init_runtime(self) -> None:
        """初始化 OnnxTtsRuntime（自动确保模型已下载）"""
        if self.runtime is not None:
            return

        # 1. 优先使用 pip 安装时 vendoring 的目录
        vendor_dir = _get_vendor_dir()
        if vendor_dir and vendor_dir not in sys.path:
            sys.path.insert(0, vendor_dir)
            logger.info(f"[MossNano] 使用 vendoring 目录: {vendor_dir}")

        # 2. 回退：检查是否已通过 pip install -e 安装
        if importlib.util.find_spec("onnx_tts_runtime") is None:
            raise RuntimeError(
                "[MossNano] 无法找到 onnx_tts_runtime 模块。\n"
                "若从源码运行，请执行: cd tests/moss-tts-nano && pip install -e .\n"
                "若通过 pip 安装 oddtts，请确认 whl 构建时包含了 vendor 目录。"
            )

        # 3. 确保模型已下载
        self._ensure_models()

        try:
            from onnx_tts_runtime import OnnxTtsRuntime

            cpu_threads = min(os.cpu_count() or 4, 8)
            self.runtime = OnnxTtsRuntime(
                model_dir=MODEL_DIR,
                thread_count=cpu_threads,
                execution_provider="cpu",
            )
            logger.info(
                f"[MossNano] Runtime 初始化成功，线程数: {cpu_threads}, 采样率: {SAMPLE_RATE} Hz"
            )
        except ImportError as e:
            raise RuntimeError(
                "[MossNano] 导入 onnx_tts_runtime 失败，可能缺少依赖（如 torch）。\n"
                "建议执行: cd tests/moss-tts-nano && pip install -e ."
            ) from e
        except Exception as e:
            raise RuntimeError(f"[MossNano] Runtime 初始化失败: {e}") from e

    async def preload(self) -> None:
        """预加载模型"""
        logger.info("[预加载] 开始预加载 MOSS-TTS-Nano 模型...")
        self._ensure_models()
        self._init_runtime()
        logger.info("[预加载] MOSS-TTS-Nano 模型预加载完成")

    async def get_voices(self) -> list[dict[str, str]]:
        """返回内置音色 + 克隆音色列表。"""
        builtin = list(MossNano_voices.values())
        cloned = get_voice_clone_manager().list_voices(ENGINE_NAME)
        return builtin + cloned

    def _resolve_voice_and_prompt(self, tts_params: TTSParams) -> tuple[str, str | None]:
        """解析 voice 和 prompt_audio_path。

        返回 (voice, prompt_audio_path):
        - 内置音色: voice=内置名, prompt_audio_path=None
        - 克隆音色: voice=内置fallback, prompt_audio_path=克隆音频路径
        - 优先使用 TTSParams.prompt_audio_path（即时上传模式）
        """
        # 1. 如果 params 直接带了 prompt_audio_path（即时上传 / API 指定），优先使用
        if getattr(tts_params, "prompt_audio_path", None):
            voice = tts_params.voice if tts_params.voice in MossNano_voices else "Junhao"
            return voice, tts_params.prompt_audio_path

        requested = tts_params.voice

        # 2. 请求的是内置音色
        if requested in MossNano_voices:
            return requested, None

        # 3. 尝试从克隆库查找
        manager = get_voice_clone_manager()
        prompt_path = manager.get_audio_path(ENGINE_NAME, requested)
        if prompt_path:
            # 克隆模式下 voice 传内置 fallback 用于文本预处理
            fallback = "Junhao"
            logger.info(f"[MossNano] 使用克隆音色: {requested}, 参考音频: {prompt_path}")
            return fallback, prompt_path

        # 4. 未知音色，回退到默认内置音色
        logger.warning(f"[MossNano] 未知音色 '{requested}'，回退到 Junhao")
        return "Junhao", None

    def _synthesize(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """内部合成方法，返回 numpy 音频数组"""
        if self.runtime is None:
            self._init_runtime()

        voice, prompt_audio_path = self._resolve_voice_and_prompt(tts_params)

        # 检测 WeTextProcessing 是否可用（Windows 上需先 conda install pynini）
        try:
            import tn
            has_tn = True
        except ImportError:
            has_tn = False
            logger.warning("[MossNano] WeTextProcessing (tn) 未安装，禁用文本规范化。"
                           "如果不安装 WeTextProcessing，合成依然能跑通，只是缺少中文文本规范化（比如阿拉伯数字不会自动转成中文读法）。"
                           "如需中文文本规范化，请先执行: conda install -c conda-forge pynini=2.1.6.post1 -y"
                           "然后执行: pip install WeTextProcessing")

        # 使用临时文件接收输出（OnnxTtsRuntime 必须指定 output_audio_path）
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            kwargs = dict(
                text=text,
                voice=voice,
                output_audio_path=tmp_path,
                sample_mode="fixed",
                do_sample=True,
                streaming=True,
                enable_wetext=has_tn,
                enable_normalize_tts_text=has_tn,
            )
            if prompt_audio_path:
                kwargs["prompt_audio_path"] = prompt_audio_path

            result = self.runtime.synthesize(**kwargs)
            waveform = result["waveform"]
            duration = len(waveform) / SAMPLE_RATE
            logger.info(f"[MossNano] 合成完成，音频时长: {duration:.2f}s")
            return waveform.astype(np.float32)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        logger.info(
            f"[MossNano] 生成语音文件: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        audio_numpy = self._synthesize(text, tts_params)
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
        result = convert_ndarray_to_format(audio_numpy, SAMPLE_RATE, output_format)
        if isinstance(result, str):
            return result
        raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        logger.info(
            f"[MossNano] 生成语音字节流: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        audio_numpy = self._synthesize(text, tts_params)
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
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
        logger.info(
            f"[MossNano] 生成语音流: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        audio_numpy = self._synthesize(text, tts_params)
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )
        yield audio_data
