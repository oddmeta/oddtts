import os
import subprocess
import tempfile
import uuid
import asyncio

from kokoro import KPipeline, KModel
import soundfile as sf
import numpy as np
import torch

from oddtts.oddtts_params import new_uuid, TTSParams
from oddtts.oddtts_log import setup_logger

logger = setup_logger(__name__)

oddtts_voices = {
    'OddTTS Voice (zh-CN, Jacky)':      {'name': 'Jacky', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'Jacky'}, 
    'OddTTS Voice (zh-CN, Lucy)':       {'name': 'Lucy', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'Lucy'},
    'OddTTS Voice (zh-CN, Catherine)':  {'name': 'Catherine', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'Catherine'},
    'OddTTS Voice (zh-CN, CiCi)':       {'name': 'Cici', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'Cici'}
}

class OddGptSovitsAPI():
    def __init__(self) -> None:
        pass

    def _params_adjustments(self, tts_params: TTSParams):
        """
        调整参数，确保它们的格式正确，包含正负符号
        """
        rate_ = 1 + tts_params.rate / 100
        volume_ = tts_params.volume / 100
        pitch_ = tts_params.pitch

        if tts_params.locale == 'zh-CN':
            lang_ = 'z'
        elif tts_params.locale == 'en-US':
            lang_ = 'e'
        else:
            lang_ = 'z'

        return rate_, volume_, pitch_, lang_

    async def _generate_audio(self, text: str, tts_params: TTSParams) -> str|np.ndarray:
        """
        生成语音
        """
        voice = tts_params.voice
        rate_, volume_, pitch_, lang_ = self._params_adjustments(tts_params)

        # 生成语音
        if text == "":
            text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。"

        # 生成音频数据
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code=lang_)
        
        generator = self.pipeline(text, voice=voice, speed=rate_, split_pattern=r'\n+')

        # 获取生成结果 (这是一个 KPipeline.Result 对象)
        result = next(generator)

        # 1. 访问 result.output.audio 获取 tensor
        # 根据日志: result.output 是 KModel.Output 对象，里面有个 audio 属性是 tensor
        if result.output is None:
            raise Exception("Kokoro pipeline生成语音失败")
        audio_tensor = result.output.audio

        # 2. 将 PyTorch Tensor 转换为 NumPy 数组
        # .detach() 移除梯度追踪，.cpu() 确保在CPU内存中，.numpy() 转为 numpy
        audio_numpy = audio_tensor.detach().cpu().numpy()

        return audio_numpy

    async def get_voices(self) -> list[dict[str, str]]:
        return list(oddtts_voices.values())
    
    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        audio_numpy = await self._generate_audio(text, tts_params)

        filename = tempfile.gettempdir() + '/' + new_uuid() + '.wav'
        sf.write(filename, audio_numpy, 22050)
        return filename
    
    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        audio_numpy = await self._generate_audio(text, tts_params)
        filename = tempfile.gettempdir() + '/' + new_uuid() + '.wav'
        sf.write(filename, audio_numpy, 22050)
        with open(filename, 'rb') as f:
            audio_data = f.read()
        return audio_data
    
    async def generate_tts_stream(self, text: str, tts_params: TTSParams) -> bytes:
        audio_numpy = await self._generate_audio(text, tts_params)
        filename = tempfile.gettempdir() + '/' + new_uuid() + '.wav'
        sf.write(filename, audio_numpy, 22050)
        with open(filename, 'rb') as f:
            audio_data = f.read()
        return audio_data