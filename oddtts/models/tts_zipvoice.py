"""
ZipVoice 官方版本 TTS 引擎

使用 ZipVoice 官方代码进行推理，不依赖 sherpa-onnx
通过 subprocess 调用 zipvoice.bin.infer_zipvoice 模块
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from oddtts.utils.model_utils import ensure_model, resolve_model_dir
from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts.oddtts_log import setup_logger
from oddtts.voice_clone import get_voice_clone_manager

logger = setup_logger(__name__)

# 引擎标识（用于 VoiceCloneManager）
ENGINE_NAME = "zipvoice"

ZIPVOICE_REPO_ID = os.environ.get("ZIPVOICE_REPO_ID", "k2-fsa/ZipVoice")
ZIPVOICE_MODEL_DIR = resolve_model_dir(ODDTTS_TYPE.ODDTTS_ZIPVOICE.model_key)

# 模型配置
DEFAULT_REF_AUDIO = "models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia/test_wavs/news-female.wav"
DEFAULT_REF_TEXT = "This is a reference audio sample for voice cloning."

# 采样率（ZipVoice 输出 24kHz）
SAMPLE_RATE = 24000

# 默认推理步数（越少越快，质量略降）
DEFAULT_NUM_STEPS = 8


class ZipVoiceAPI:
    """ZipVoice 官方版本 TTS 引擎 API"""

    def __init__(self) -> None:
        self._zipvoice_dir: str | None = None
        self._model_dir_resolved: str | None = None
        self._voice_cache: dict[str, dict[str, str]] = {}

    def _get_zipvoice_dir(self) -> str:
        """获取 ZipVoice 仓库目录"""
        if self._zipvoice_dir is None:
            # 检查项目根目录下的 ZipVoice 目录
            project_root = Path(__file__).parent.parent.parent
            zipvoice_dir = project_root / "ZipVoice"
            
            if not zipvoice_dir.exists():
                raise RuntimeError(
                    "[ZipVoice] ZipVoice 仓库不存在。\n"
                    "请执行: git clone https://github.com/k2-fsa/ZipVoice.git"
                )
            
            self._zipvoice_dir = str(zipvoice_dir)
        
        return self._zipvoice_dir

    def _ensure_model(self):
        model_dir = ZIPVOICE_MODEL_DIR
        ensure_model(
            model_dir=model_dir,
            repo_ids=ZIPVOICE_REPO_ID,
            marker_file="zipvoice_distill/model.pt",
            source_priority=["modelscope", "huggingface"],
            tag="[ZipVoice]",
            manual_hint=f"请手动下载 {ZIPVOICE_REPO_ID} 到 {model_dir}",
        )

    def _get_model_dir(self) -> str | None:
        """获取本地 PyTorch 模型目录（如果存在）"""
        if self._model_dir_resolved is not None:
            return self._model_dir_resolved

        model_dir = ZIPVOICE_MODEL_DIR

        # 标准路径下的 zipvoice_distill 子目录
        distill_dir = os.path.join(model_dir, "zipvoice_distill")
        if self._validate_model_dir(distill_dir):
            self._model_dir_resolved = distill_dir
            return self._model_dir_resolved

        zipvoice_sub = os.path.join(model_dir, "zipvoice")
        if self._validate_model_dir(zipvoice_sub):
            self._model_dir_resolved = zipvoice_sub
            return self._model_dir_resolved

        # 尝试下载
        try:
            self._ensure_model()
        except Exception as e:
            logger.warning(f"[ZipVoice] 模型下载失败: {e}")

        # 下载后重新检查
        if self._validate_model_dir(distill_dir):
            self._model_dir_resolved = distill_dir
            return self._model_dir_resolved
        if self._validate_model_dir(zipvoice_sub):
            self._model_dir_resolved = zipvoice_sub
            return self._model_dir_resolved

        logger.info("[ZipVoice] 未找到本地 PyTorch 模型，将尝试从 HuggingFace 下载")
        return None

    @staticmethod
    def _validate_model_dir(path: str) -> bool:
        if not os.path.isdir(path):
            return False
        has_model = os.path.isfile(os.path.join(path, "model.pt")) or os.path.isfile(os.path.join(path, "model.safetensors"))
        has_config = os.path.isfile(os.path.join(path, "model.json"))
        has_tokens = os.path.isfile(os.path.join(path, "tokens.txt"))
        return has_model and has_config and has_tokens

    def _check_dependencies(self) -> None:
        """检查必要依赖"""
        missing = []
        
        try:
            import torch
        except ImportError:
            missing.append("torch")
        
        try:
            import torchaudio
        except ImportError:
            missing.append("torchaudio")
        
        try:
            import vocos
        except ImportError:
            missing.append("vocos")
        
        try:
            import pypinyin
        except ImportError:
            missing.append("pypinyin")
        
        try:
            import jieba
        except ImportError:
            missing.append("jieba")
        
        if missing:
            raise RuntimeError(
                f"[ZipVoice] 缺少依赖: {', '.join(missing)}\n"
                "请执行: cd ZipVoice && pip install -r requirements.txt"
            )

    def _get_ref_audio(self, voice: str | None = None) -> tuple[str, str]:
        """获取参考音频路径和文本。
        
        返回 (ref_audio_path, ref_text)
        """
        # 如果指定了 voice 且已缓存
        if voice and voice in self._voice_cache:
            cached = self._voice_cache[voice]
            return cached["audio"], cached["text"]
        
        # 使用默认参考音频
        project_root = Path(__file__).parent.parent.parent
        ref_audio = project_root / DEFAULT_REF_AUDIO
        
        if not ref_audio.exists():
            raise FileNotFoundError(
                f"[ZipVoice] 默认参考音频不存在: {ref_audio}\n"
                "请确认模型已正确下载。"
            )
        
        return str(ref_audio), DEFAULT_REF_TEXT

    async def preload(self) -> None:
        """预加载：检查依赖和参考音频"""
        logger.info("[预加载] 开始预加载 ZipVoice 引擎...")
        
        # 检查依赖
        self._check_dependencies()
        
        # 检查 ZipVoice 仓库
        zipvoice_dir = self._get_zipvoice_dir()
        logger.info(f"[预加载] ZipVoice 仓库: {zipvoice_dir}")
        
        # 检查参考音频
        ref_audio, ref_text = self._get_ref_audio()
        logger.info(f"[预加载] 参考音频: {ref_audio}")
        logger.info(f"[预加载] 参考文本: {ref_text}")
        
        logger.info("[预加载] ZipVoice 引擎预加载完成")

    async def get_voices(self) -> list[dict[str, str]]:
        """返回可用音色列表。
        
        ZipVoice 是零样本音色克隆模型，任何参考音频都可以作为音色。
        这里返回一个默认音色 + 克隆音色列表。
        """
        # 默认音色
        default_voice = {
            "name": "default",
            "gender": "Female",
            "locale": "en-US",
            "short_name": "default",
        }
        
        # 克隆音色
        cloned = get_voice_clone_manager().list_voices(ENGINE_NAME)
        
        return [default_voice] + cloned

    def _synthesize(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """内部合成方法，返回 numpy 音频数组"""
        # 检查依赖
        self._check_dependencies()
        
        # 获取 ZipVoice 目录
        zipvoice_dir = self._get_zipvoice_dir()
        
        # 解析音色和参考音频
        voice = tts_params.voice or "default"
        ref_audio, ref_text = self._get_ref_audio(voice)
        
        # 检查是否是克隆音色
        if voice != "default":
            manager = get_voice_clone_manager()
            prompt_path = manager.get_audio_path(ENGINE_NAME, voice)
            if prompt_path:
                ref_audio = prompt_path
                # 优先使用 TTSParams 中传入的 prompt_text
                if tts_params.prompt_text:
                    ref_text = tts_params.prompt_text
                else:
                    # 尝试从克隆库中获取存储的 prompt_text
                    stored_text = manager.get_prompt_text(ENGINE_NAME, voice)
                    if stored_text:
                        ref_text = stored_text
                    else:
                        # 克隆音色需要提供参考文本，这里使用通用文本
                        ref_text = "This is a reference audio sample for voice cloning."
                logger.info(f"[ZipVoice] 使用克隆音色: {voice}, 参考音频: {ref_audio}")
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            # 构建命令
            cmd = [
                sys.executable, "-m", "zipvoice.bin.infer_zipvoice",
                "--model-name", "zipvoice_distill",
                "--prompt-wav", ref_audio,
                "--prompt-text", ref_text,
                "--text", text,
                "--res-wav-path", output_path,
                "--num-step", str(DEFAULT_NUM_STEPS),
            ]
            
            # 如果找到本地模型，使用 --model-dir 参数
            model_dir = self._get_model_dir()
            if model_dir:
                cmd.extend(["--model-dir", model_dir])
                logger.info(f"[ZipVoice] 使用本地模型: {model_dir}")
            else:
                logger.info("[ZipVoice] 将尝试从 HuggingFace 下载模型")
            
            logger.info(f"[ZipVoice] 开始合成: {text[:50]}...")
            logger.info(f"[ZipVoice] 参考音频: {ref_audio}")
            
            # 设置环境变量
            env = os.environ.copy()
            env['HF_ENDPOINT'] = 'https://hf-mirror.com'
            
            # 将 ZipVoice 目录添加到 PYTHONPATH
            if 'PYTHONPATH' not in env:
                env['PYTHONPATH'] = zipvoice_dir
            else:
                env['PYTHONPATH'] = zipvoice_dir + os.pathsep + env['PYTHONPATH']
            
            logger.info(f"[ZipVoice] PYTHONPATH: {env['PYTHONPATH']}")
            
            # 执行推理
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=str(Path.cwd()),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            elapsed = time.time() - start_time
            
            # 检查执行结果
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "未知错误"
                error = f"[ZipVoice] 推理失败 (返回码: {result.returncode}): {error_msg}"
                logger.error(error)
                raise RuntimeError(error)
            
            # 检查输出文件
            if not Path(output_path).exists():
                raise RuntimeError(f"[ZipVoice] 输出文件未生成: {output_path}")
            
            # 读取音频
            import soundfile as sf
            waveform, sr = sf.read(output_path)
            
            # 重采样到 24kHz（如果需要）
            if sr != SAMPLE_RATE:
                import librosa
                waveform = librosa.resample(waveform, orig_sr=sr, target_sr=SAMPLE_RATE)
            
            logger.info(f"[ZipVoice] 合成完成，耗时: {elapsed:.2f}s, 采样率: {SAMPLE_RATE}Hz")
            
            return waveform.astype(np.float32)
        
        finally:
            # 清理临时文件
            if Path(output_path).exists():
                Path(output_path).unlink()

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        """生成语音文件"""
        logger.info(
            f"[ZipVoice] 生成语音文件: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        
        audio_numpy = self._synthesize(text, tts_params)
        
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
        
        time_start = time.time()
        logger.info(f"[ZipVoice] 转换音频格式: {output_format}")
        
        result = convert_ndarray_to_format(audio_numpy, SAMPLE_RATE, output_format)
        
        time_end = time.time()
        logger.info(f"[ZipVoice] 转换完成，耗时: {time_end - time_start:.2f}s")
        
        if isinstance(result, str):
            return result
        raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        """生成语音字节流"""
        logger.info(
            f"[ZipVoice] 生成语音字节流: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        
        audio_numpy = self._synthesize(text, tts_params)
        
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
        
        time_start = time.time()
        logger.info(f"[ZipVoice] 转换音频格式: {output_format}")
        
        result = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )
        
        time_end = time.time()
        logger.info(f"[ZipVoice] 转换完成，耗时: {time_end - time_start:.2f}s")
        
        if isinstance(result, bytes):
            return result
        raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        """生成语音流"""
        logger.info(
            f"[ZipVoice] 生成语音流: voice={tts_params.voice}, format={tts_params.response_format}"
        )
        
        audio_numpy = self._synthesize(text, tts_params)
        
        output_format = (
            tts_params.response_format
            if hasattr(tts_params, "response_format")
            else "wav"
        )
        
        time_start = time.time()
        logger.info(f"[ZipVoice] 转换音频格式: {output_format}")
        
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )
        
        time_end = time.time()
        logger.info(f"[ZipVoice] 转换完成，耗时: {time_end - time_start:.2f}s")
        
        yield audio_data
