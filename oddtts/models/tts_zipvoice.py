"""ZipVoice TTS engine — uses sherpa-onnx for inference.

Model: roarson/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia (ModelScope)
- No voice cloning support
- Built-in voices from test_wavs/prompt.txt
- Requires: sherpa-onnx, soundfile
"""

import os
import time
import urllib.request
from pathlib import Path

import numpy as np

from oddtts.utils.model_utils import ensure_model, resolve_model_dir
from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts.oddtts_log import setup_logger

logger = setup_logger(__name__)

ENGINE_NAME = "zipvoice"

# Model source: ModelScope
ZIPVOICE_REPO_ID = os.environ.get(
    "ZIPVOICE_REPO_ID",
    "roarson/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia",
)
ZIPVOICE_MODEL_DIR = resolve_model_dir(ODDTTS_TYPE.ODDTTS_ZIPVOICE.model_key)

# Model files (encoder/decoder/tokens/lexicon are in the ModelScope repo)
ENCODER_NAME = "encoder.int8.onnx"
DECODER_NAME = "decoder.int8.onnx"
TOKEN_FILE_NAME = "tokens.txt"
LEXICON_NAME = "lexicon.txt"
ESPEAK_DIR = "espeak-ng-data"

# Vocoder: separate download (not in the main model repo)
VOCODER_NAME = "vocos_24khz.onnx"
VOCODER_REPO_ID = "roarson/vocos_24khz.onnx"
VOCODER_GITHUB_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos_24khz.onnx"

SAMPLE_RATE = 24000


def _load_builtin_voices(model_dir: str) -> list[dict[str, str]]:
    """Parse test_wavs/prompt.txt to discover built-in voices."""
    voices = []
    prompt_file = os.path.join(model_dir, "test_wavs", "prompt.txt")
    if not os.path.isfile(prompt_file):
        return voices

    with open(prompt_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) < 2:
                continue
            wav_name, prompt_text = parts
            wav_path = os.path.join(model_dir, "test_wavs", wav_name)
            if os.path.isfile(wav_path):
                voice_id = wav_name.rsplit(".", 1)[0]
                voices.append({
                    "name": voice_id,
                    "gender": "Unknown",
                    "locale": "zh-CN",
                    "short_name": voice_id,
                    "_ref_audio": wav_path,
                    "_ref_text": prompt_text,
                })
    return voices


def _find_vocoder(base_dir: str) -> str | None:
    """Search for vocos_24khz.onnx in standard locations."""
    parent = os.path.dirname(base_dir)
    candidates = [
        os.path.join(base_dir, VOCODER_NAME),
        os.path.join(base_dir, "vocos-mel-24khz-onnx", VOCODER_NAME),
        os.path.join(parent, "vocos-mel-24khz-onnx", VOCODER_NAME),
        os.path.join(parent, "vocoder-models", VOCODER_NAME),
        os.path.join(parent, "sherpa-onnx-zipvoice-distill-int8-zh-en-emilia", VOCODER_NAME),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _download_vocoder(target_dir: str) -> str | None:
    """Download vocos_24khz.onnx from ModelScope if not present."""
    target = os.path.join(target_dir, VOCODER_NAME)
    if os.path.isfile(target):
        return target

    logger.info("[ZipVoice] Downloading vocoder from ModelScope: %s", VOCODER_REPO_ID)
    try:
        from modelscope import snapshot_download
        snapshot_download(
            VOCODER_REPO_ID,
            local_dir=target_dir,
        )
        if os.path.isfile(target):
            logger.info("[ZipVoice] Vocoder downloaded to: %s", target)
            return target
    except Exception as e:
        logger.warning("[ZipVoice] Vocoder download from ModelScope failed: %s", e)

    # Fallback: try GitHub
    logger.info("[ZipVoice] Trying GitHub: %s", VOCODER_GITHUB_URL)
    try:
        urllib.request.urlretrieve(VOCODER_GITHUB_URL, target)
        if os.path.isfile(target):
            logger.info("[ZipVoice] Vocoder downloaded to: %s", target)
            return target
    except Exception as e:
        logger.warning("[ZipVoice] Vocoder download from GitHub failed: %s", e)
    return None


class ZipVoiceAPI:
    """ZipVoice TTS engine — uses sherpa-onnx for inference."""

    def __init__(self) -> None:
        self.tts = None
        self._model_dir_resolved: str | None = None
        self._vocoder_path_resolved: str | None = None
        self._builtin_voices: list[dict] | None = None

    # ── Model resolution ────────────────────────────────────────────────

    def _ensure_model(self):
        """Download model from ModelScope if missing."""
        ensure_model(
            model_dir=ZIPVOICE_MODEL_DIR,
            repo_ids=ZIPVOICE_REPO_ID,
            marker_file=ENCODER_NAME,
            source_priority=["modelscope"],
            tag="[ZipVoice]",
            manual_hint=f"请手动下载 {ZIPVOICE_REPO_ID} 到 {ZIPVOICE_MODEL_DIR}",
        )

    def _get_model_dir(self) -> str | None:
        """Resolve the model directory."""
        if self._model_dir_resolved is not None:
            return self._model_dir_resolved

        # Flat layout (ModelScope downloads directly here)
        if self._validate_model_dir(ZIPVOICE_MODEL_DIR):
            self._model_dir_resolved = ZIPVOICE_MODEL_DIR
            return self._model_dir_resolved

        # Subdirectory layout
        subdir = os.path.join(ZIPVOICE_MODEL_DIR, "sherpa-onnx-zipvoice-distill-int8-zh-en-emilia")
        if self._validate_model_dir(subdir):
            self._model_dir_resolved = subdir
            return self._model_dir_resolved

        # Try downloading
        try:
            self._ensure_model()
        except Exception as e:
            logger.warning("[ZipVoice] Model download failed: %s", e)

        # Re-check after download
        if self._validate_model_dir(ZIPVOICE_MODEL_DIR):
            self._model_dir_resolved = ZIPVOICE_MODEL_DIR
            return self._model_dir_resolved
        if self._validate_model_dir(subdir):
            self._model_dir_resolved = subdir
            return self._model_dir_resolved

        return None

    def _get_vocoder_path(self) -> str | None:
        """Resolve vocoder ONNX path."""
        if self._vocoder_path_resolved is not None:
            return self._vocoder_path_resolved

        model_dir = self._get_model_dir()
        if model_dir is None:
            return None

        # Search existing locations
        path = _find_vocoder(model_dir)
        if path:
            self._vocoder_path_resolved = path
            return path

        # Try downloading to the model directory
        path = _download_vocoder(model_dir)
        if path:
            self._vocoder_path_resolved = path
            return path

        # Search in sibling directories (e.g., models/vocos-mel-24khz-onnx/)
        parent = os.path.dirname(model_dir)
        path = _find_vocoder(parent)
        if path:
            self._vocoder_path_resolved = path
            return path

        return None

    @staticmethod
    def _validate_model_dir(path: str) -> bool:
        """Check if directory has the core model files (vocoder excluded — separate download)."""
        if not os.path.isdir(path):
            return False
        for f in [ENCODER_NAME, DECODER_NAME, TOKEN_FILE_NAME]:
            if not os.path.isfile(os.path.join(path, f)):
                return False
        return os.path.isdir(os.path.join(path, ESPEAK_DIR))

    # ── Runtime initialization ──────────────────────────────────────────

    def _init_runtime(self):
        """Initialize sherpa-onnx TTS (once)."""
        if self.tts is not None:
            return

        model_dir = self._get_model_dir()
        if model_dir is None:
            raise RuntimeError(
                f"[ZipVoice] 模型目录不存在: {ZIPVOICE_MODEL_DIR}/\n"
                f"请执行: modelscope download --model {ZIPVOICE_REPO_ID} --local_dir {ZIPVOICE_MODEL_DIR}"
            )

        vocoder_path = self._get_vocoder_path()
        if vocoder_path is None:
            raise RuntimeError(
                f"[ZipVoice] Vocoder 不存在 ({VOCODER_NAME})。\n"
                f"自动下载失败。请手动下载并放置到:\n"
                f"  {model_dir}/{VOCODER_NAME}\n"
                f"下载地址: {VOCODER_GITHUB_URL}"
            )

        # Lazy import sherpa-onnx
        import sherpa_onnx

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                zipvoice=sherpa_onnx.OfflineTtsZipvoiceModelConfig(
                    tokens=os.path.join(model_dir, TOKEN_FILE_NAME),
                    encoder=os.path.join(model_dir, ENCODER_NAME),
                    decoder=os.path.join(model_dir, DECODER_NAME),
                    data_dir=os.path.join(model_dir, ESPEAK_DIR),
                    lexicon=os.path.join(model_dir, LEXICON_NAME),
                    vocoder=vocoder_path,
                ),
                num_threads=int(os.environ.get("ZIPVOICE_NUM_THREADS", "2")),
            ),
        )

        self.tts = sherpa_onnx.OfflineTts(config)

        # Cache built-in voices
        self._builtin_voices = _load_builtin_voices(model_dir)

        logger.info("[ZipVoice] sherpa-onnx initialized (model: %s, vocoder: %s, sr: %d, %d voices)",
                     model_dir, vocoder_path, self.tts.sample_rate, len(self._builtin_voices or []))

    # ── Public API ──────────────────────────────────────────────────────

    async def preload(self) -> None:
        """Preload: initialize sherpa-onnx and verify models."""
        logger.info("[ZipVoice] Preloading...")
        self._init_runtime()
        logger.info("[ZipVoice] Preload complete")

    async def get_voices(self) -> list[dict[str, str]]:
        """Return available built-in voices."""
        if self._builtin_voices is None:
            try:
                self._init_runtime()
            except Exception as e:
                logger.warning("[ZipVoice] Failed to load voices: %s", e)
                return []
        return self._builtin_voices or []

    def _resolve_voice(self, tts_params: TTSParams) -> tuple[str, str]:
        """Resolve reference audio path and text."""
        voice = tts_params.voice or ""

        if self._builtin_voices:
            for v in self._builtin_voices:
                if v["name"] == voice or v["short_name"] == voice:
                    return v["_ref_audio"], v["_ref_text"]

            # Default to first voice
            first = self._builtin_voices[0]
            if voice and voice != "default":
                logger.warning("[ZipVoice] Voice '%s' not found, using default: %s",
                               voice, first["name"])
            return first["_ref_audio"], first["_ref_text"]

        raise RuntimeError("[ZipVoice] No built-in voices available")

    def _synthesize(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """Core synthesis: returns numpy float32 audio array."""
        self._init_runtime()

        import soundfile as sf

        ref_audio, ref_text = self._resolve_voice(tts_params)

        # Allow prompt_text override
        if tts_params.prompt_text:
            ref_text = tts_params.prompt_text

        # Load reference audio
        samples, sr = sf.read(ref_audio, dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        speed = 1.0
        if hasattr(tts_params, "rate") and tts_params.rate is not None:
            speed = 1.0 + tts_params.rate / 100.0

        logger.info("[ZipVoice] Synthesizing: %s (voice=%s)", text[:50], ref_text[:30])
        start_time = time.time()

        audio = self.tts.generate(
            text=text,
            prompt_text=ref_text,
            prompt_samples=samples.tolist(),
            sample_rate=sr,
            speed=speed,
            num_steps=8,
        )

        elapsed = time.time() - start_time
        result = np.array(audio.samples, dtype=np.float32)
        duration = len(result) / SAMPLE_RATE
        logger.info("[ZipVoice] Done: %.2fs audio in %.2fs (RTF=%.3f)",
                     duration, elapsed, elapsed / max(duration, 0.01))

        return result

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        audio_numpy = self._synthesize(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav") or "wav"
        result = convert_ndarray_to_format(audio_numpy, SAMPLE_RATE, output_format)
        if isinstance(result, str):
            return result
        raise TypeError(f"Expected str, got {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        audio_numpy = self._synthesize(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav") or "wav"
        result = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )
        if isinstance(result, bytes):
            return result
        raise TypeError(f"Expected bytes, got {type(result).__name__}")

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        audio_numpy = self._synthesize(text, tts_params)
        output_format = getattr(tts_params, "response_format", "wav") or "wav"
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=SAMPLE_RATE,
        )
        yield audio_data
