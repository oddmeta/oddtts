import logging
import os
import subprocess
import tempfile
import uuid
import asyncio
import io

from kokoro import KPipeline
import soundfile as sf
import numpy as np
import torch

from oddtts.oddtts_params import convert_audio_to_format
from oddtts.oddtts_params import convert_audio_format
from oddtts.oddtts_params import TTSParams

logger = logging.getLogger(__name__)

Kokoro_voices = {
    'Kokoro Voice (zh-CN, Xiaobei)': {'name': 'zf_xiaobei', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaobei'}, 
    'Kokoro Voice (zh-CN, Xiaoni)': {'name': 'zf_xiaoni', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoni'},
    'Kokoro Voice (zh-CN, Xiaoxiao)': {'name': 'zf_xiaoxiao', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoxiao'},
    'Kokoro Voice (zh-CN, Xiaoyi)': {'name': 'zf_xiaoyi', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoyi'},
    'Kokoro Voice (zh-CN, Yunjian)': {'name': 'zm_yunjian', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_yunjian'},
    'Kokoro Voice (zh-CN, Yunxi)': {'name': 'zm_yunxi', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_yunxi'}, 
    'Kokoro Voice (zh-CN, Yunyang)': {'name': 'zm_yunyang', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_yunyang'},
    'Kokoro Voice (zh-CN, Yunxia)': {'name': 'zm_yunxia', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_yunxia'},
}

class KokoroAPI():

    def __init__(self) -> None:
        self.pipeline = None
        pass
    
    async def get_voices(self) -> list[dict[str, str]]:
        return list(Kokoro_voices.values())

    async def _check_voice(self, voice: str) -> bool:
        return voice in [voice['name'] for voice in Kokoro_voices.values()]

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

    async def _generate_audio(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """
        生成语音
        """
        logger.info(f"生成语音，参数：{tts_params}")
        rate_, volume_, pitch_, lang_ = self._params_adjustments(tts_params)

        # 生成语音
        if text == "":
            text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。"

        # 生成音频数据
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code=lang_)
        
        generator = self.pipeline(text, voice=tts_params.voice, speed=rate_, split_pattern=r'\n+')

        # 获取生成结果 (这是一个 KPipeline.Result 对象)
        result = next(generator)

        # 1. 访问 result.output.audio 获取 tensor
        # 根据日志: result.output 是 KModel.Output 对象，里面有个 audio 属性是 tensor
        audio_tensor = result.output.audio

        # 2. 将 PyTorch Tensor 转换为 NumPy 数组
        # .detach() 移除梯度追踪，.cpu() 确保在CPU内存中，.numpy() 转为 numpy
        audio_numpy = audio_tensor.detach().cpu().numpy()

        return audio_numpy

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> list[str]:
        logger.info(f"生成语音文件，参数：{tts_params}")
        audio_numpy = await self._generate_audio(text, tts_params)

        # 3. 处理维度
        # soundfile 需要 (样本数, 通道数) 的二维数组。
        # Kokoro 输出的通常是 (样本数,) 的一维数组，我们需要变成 (样本数, 1)
        if audio_numpy.ndim == 1:
            audio_numpy = audio_numpy.reshape(-1, 1)

        # 4. 获取采样率
        # Kokoro 的标准采样率通常是 24000，也可以检查是否有属性直接提供
        sample_rate = 24000 

        # 5. 根据输出格式生成文件
        output_format = tts_params.response_format if hasattr(tts_params, 'response_format') else 'wav'
        output_file = convert_audio_to_format(audio_numpy, sample_rate, output_format)

        return output_file

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        logger.info(f"生成语音字节流，参数：{tts_params}")

        audio_numpy = await self._generate_audio(text, tts_params)
        
        output_format = tts_params.response_format if hasattr(tts_params, 'response_format') else 'wav'
                
        return convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=24000
        )
    
    async def generate_tts_stream(self, text: str, tts_params: TTSParams):

        logger.info(f"生成语音流，参数：{tts_params}")

        audio_numpy = await self._generate_audio(text, tts_params)
        
        output_format = tts_params.response_format if hasattr(tts_params, 'response_format') else 'wav'
        
        logger.info(f"生成语音流，参数：{tts_params}，输出格式：{output_format}")
        
        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=24000
        )
        
        yield audio_data


def test_kokoro():
    api = KokoroAPI()

    text = "关注我的公众号：奥德元，一起学习 A I，一起追赶时代!"

    tts_params = TTSParams(
        voice="zf_xiaobei",
        rate=0,
        volume=0,
        pitch=0,
        locale="zh-CN",
        output_format="wav"
    )

    file_name = asyncio.run(api.generate_tts_file(text, tts_params))

    print(file_name)

if __name__ == "__main__":
    test_kokoro()