"""VoiceCloneManager — 克隆音色统一管理器

目录结构:
    voices/
      <engine>/
        <voice_id>/
          reference.wav   # 统一转换为 WAV 存储
          meta.json       # 音色元数据

每个引擎的克隆音色互相隔离，避免命名冲突。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from oddtts.oddtts_log import setup_logger

logger = setup_logger(__name__)

def _get_default_voices_root() -> Path:
    """返回默认的克隆音色根目录：data_root / voices_base_dir。"""
    from oddtts.utils.model_utils import get_data_root
    from oddtts.oddtts_config import oddtts_cfg
    base = oddtts_cfg.get("voices_base_dir", "voices")
    return Path(get_data_root()) / base

# 参考音频统一转码为 WAV, 48kHz, 单声道/立体声保持原样
_TARGET_SAMPLE_RATE = 48000

# 有效的 voice_id 正则（只允许字母、数字、下划线、连字符）
_VOICE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _sanitize_voice_id(name: str) -> str:
    """将用户输入的名称转换为安全的 voice_id。"""
    # 去掉前后空白，替换非法字符为下划线
    sid = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip())
    # 合并连续下划线
    sid = re.sub(r"_+", "_", sid)
    # 去掉首尾下划线
    sid = sid.strip("_")
    if not sid:
        sid = "voice_" + uuid.uuid4().hex[:8]
    return sid[:64]


def _ensure_wav(audio_path: str | Path, output_path: str | Path) -> Path:
    """确保音频为 WAV 格式，如需要则转码。"""
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if audio_path.suffix.lower() == ".wav":
        # 已经是 WAV，直接复制
        shutil.copy2(audio_path, output_path)
        return output_path

    # 需要转码，尝试使用 soundfile / pydub
    try:
        import soundfile as sf
        data, sr = sf.read(str(audio_path))
        sf.write(str(output_path), data, sr, format="WAV")
        return output_path
    except Exception:
        pass

    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(audio_path))
        audio.export(str(output_path), format="wav")
        return output_path
    except Exception as e:
        raise RuntimeError(f"无法将音频转码为 WAV: {e}")


class VoiceCloneManager:
    """克隆音色管理器。

    用法::

        manager = VoiceCloneManager()
        # 保存新音色
        manager.save_voice("moss_nano", "xiaoming", "小明", "/path/to/upload.mp3")
        # 列出色色
        voices = manager.list_voices("moss_nano")
        # 获取参考音频路径
        path = manager.get_audio_path("moss_nano", "xiaoming")
        # 删除音色
        manager.delete_voice("moss_nano", "xiaoming")
    """

    def __init__(self, voices_root: str | Path | None = None) -> None:
        self.voices_root = Path(voices_root) if voices_root else _get_default_voices_root()
        self.voices_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"[VoiceClone] 音色根目录: {self.voices_root}")

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    def _engine_dir(self, engine: str) -> Path:
        d = self.voices_root / _sanitize_voice_id(engine)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _voice_dir(self, engine: str, voice_id: str) -> Path:
        return self._engine_dir(engine) / voice_id

    def _meta_path(self, engine: str, voice_id: str) -> Path:
        return self._voice_dir(engine, voice_id) / "meta.json"

    def _audio_path(self, engine: str, voice_id: str) -> Path:
        return self._voice_dir(engine, voice_id) / "reference.wav"

    def _load_meta(self, engine: str, voice_id: str) -> dict[str, Any] | None:
        p = self._meta_path(engine, voice_id)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[VoiceClone] 读取 meta.json 失败 [{engine}/{voice_id}]: {e}")
            return None

    # ------------------------------------------------------------------ #
    # 公共 API
    # ------------------------------------------------------------------ #
    def list_voices(self, engine: str | None = None) -> list[dict[str, Any]]:
        """返回克隆音色列表。

        Args:
            engine: 引擎名，如 ``"moss_nano"``。为 None 时返回所有引擎的音色。

        Returns:
            与现有 ``get_voices()`` 格式兼容的列表，额外包含 ``is_cloned`` 字段。
        """
        results: list[dict[str, Any]] = []

        engines = [engine] if engine else [d.name for d in self.voices_root.iterdir() if d.is_dir()]

        for eng in engines:
            eng_dir = self._engine_dir(eng)
            for voice_dir in eng_dir.iterdir():
                if not voice_dir.is_dir():
                    continue
                voice_id = voice_dir.name
                meta = self._load_meta(eng, voice_id)
                if meta is None:
                    # 目录存在但缺少 meta，尝试自动修复
                    if self._audio_path(eng, voice_id).exists():
                        meta = {
                            "voice_id": voice_id,
                            "display_name": voice_id,
                            "engine": eng,
                            "created_at": "",
                            "is_cloned": True,
                        }
                    else:
                        continue

                results.append(
                    {
                        "name": meta.get("voice_id", voice_id),
                        "short_name": meta.get("voice_id", voice_id),
                        "display_name": meta.get("display_name", voice_id),
                        "gender": meta.get("gender", "Unknown"),
                        "locale": meta.get("locale", "zh-CN"),
                        "engine": meta.get("engine", eng),
                        "is_cloned": True,
                        "created_at": meta.get("created_at", ""),
                    }
                )

        return results

    def get_voice(self, engine: str, voice_id: str) -> dict[str, Any] | None:
        """获取单个克隆音色的详细信息。"""
        meta = self._load_meta(engine, voice_id)
        if meta is None:
            return None
        return {
            "name": meta.get("voice_id", voice_id),
            "short_name": meta.get("voice_id", voice_id),
            "display_name": meta.get("display_name", voice_id),
            "gender": meta.get("gender", "Unknown"),
            "locale": meta.get("locale", "zh-CN"),
            "engine": meta.get("engine", engine),
            "is_cloned": True,
            "created_at": meta.get("created_at", ""),
            "audio_path": str(self._audio_path(engine, voice_id)),
        }

    def get_audio_path(self, engine: str, voice_id: str) -> str | None:
        """返回克隆音色的参考音频路径，如不存在则返回 None。"""
        p = self._audio_path(engine, voice_id)
        return str(p) if p.exists() else None

    def save_voice(
        self,
        engine: str,
        voice_id: str,
        display_name: str,
        audio_file_path: str | Path,
        locale: str = "zh-CN",
        gender: str = "Unknown",
    ) -> dict[str, Any]:
        """保存新的克隆音色。

        Args:
            engine: 所属引擎，如 ``"moss_nano"``。
            voice_id: 音色唯一标识（会被 sanitize）。
            display_name: 展示名称。
            audio_file_path: 上传的原始音频文件路径。
            locale: 语种，默认 ``"zh-CN"``。
            gender: 性别，默认 ``"Unknown"``。

        Returns:
            保存后的音色信息字典。
        """
        sid = _sanitize_voice_id(voice_id)
        if not _VOICE_ID_RE.match(sid):
            raise ValueError(f"音色标识非法: {sid}")

        vdir = self._voice_dir(engine, sid)
        vdir.mkdir(parents=True, exist_ok=True)

        # 转码并保存为 reference.wav
        target_audio = vdir / "reference.wav"
        _ensure_wav(audio_file_path, target_audio)

        meta = {
            "voice_id": sid,
            "display_name": display_name.strip() or sid,
            "engine": engine,
            "locale": locale,
            "gender": gender,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "is_cloned": True,
            "source_audio_name": Path(audio_file_path).name,
        }

        with open(vdir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"[VoiceClone] 已保存音色 [{engine}/{sid}]: {meta['display_name']}")
        return meta

    def delete_voice(self, engine: str, voice_id: str) -> bool:
        """删除克隆音色，返回是否成功。"""
        vdir = self._voice_dir(engine, voice_id)
        if not vdir.exists():
            logger.warning(f"[VoiceClone] 音色不存在，跳过删除: [{engine}/{voice_id}]")
            return False

        try:
            shutil.rmtree(vdir)
            logger.info(f"[VoiceClone] 已删除音色 [{engine}/{voice_id}]")
            return True
        except Exception as e:
            logger.error(f"[VoiceClone] 删除音色失败 [{engine}/{voice_id}]: {e}")
            return False

    def voice_exists(self, engine: str, voice_id: str) -> bool:
        """检查音色是否存在。"""
        return self._voice_dir(engine, voice_id).exists() and self._audio_path(engine, voice_id).exists()


# ---------------------------------------------------------------------- #
# 全局单例
# ---------------------------------------------------------------------- #
_voice_clone_manager: VoiceCloneManager | None = None


def get_voice_clone_manager() -> VoiceCloneManager:
    """获取全局 VoiceCloneManager 单例。"""
    global _voice_clone_manager
    if _voice_clone_manager is None:
        _voice_clone_manager = VoiceCloneManager()
    return _voice_clone_manager

