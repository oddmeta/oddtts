import logging
import os
import subprocess
import tempfile
import uuid
import asyncio
import io
import time
import json
import sys

from kokoro import KPipeline, KModel
import soundfile as sf
import numpy as np
import torch
from huggingface_hub import snapshot_download, try_to_load_from_cache

from oddtts.oddtts_params import convert_audio_to_format
from oddtts.oddtts_params import convert_audio_format
from oddtts.oddtts_params import TTSParams

logger = logging.getLogger(__name__)

KokoroV11_voices = {
    'Kokoro Voice (zh-CN, Xiaobei)': {'name': 'zf_001', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_001'}, 
    'Kokoro Voice (zh-CN, Xiaoni)': {'name': 'zf_002', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_002'},
    'Kokoro Voice (zh-CN, Xiaoxiao)': {'name': 'zf_003', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_003'},
    'Kokoro Voice (zh-CN, Xiaoyi)': {'name': 'zf_004', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_004'},
    'Kokoro Voice (zh-CN, Yunjian)': {'name': 'zm_009', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_009'},
    'Kokoro Voice (zh-CN, Yunxi)': {'name': 'zm_010', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_010'}, 
    'Kokoro Voice (zh-CN, Yunyang)': {'name': 'zm_011', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_011'},
    'Kokoro Voice (zh-CN, Yunxia)': {'name': 'zm_012', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_012'},
}

class KokoroAPIV11():

    def __init__(self) -> None:
        self.model = None
        self.local_repo_id = "hexgrad/Kokoro-82M-v1.1-zh"
        self.local_model_dir = "ckpts"
        self.local_model_name = "kokoro-v1_1-zh.pth"
        self.default_text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。Good good study, day day up."
        # 中文音色张量
        self.pipeline = None
        self.voice_tensor_cn = None
        # 中英混合-英文管道
        self.pipeline_en = None
        self.voice_en = "af_maple"
        self.voice_tensor_en = None
    
    async def get_voices(self) -> list[dict[str, str]]:
        return list(KokoroV11_voices.values())

    async def _check_voice(self, voice: str) -> bool:
        return voice in [voice['name'] for voice in KokoroV11_voices.values()]

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

    async def _load_model(self, repo_id: str, local_dir: str, device: str = 'cpu') -> None:
        '''
        加载模型，如果模型不存在则自动从 HuggingFace 下载
        '''
        if self.model is None:
            start_time = time.time()
            
            try:
                model_cache_path = try_to_load_from_cache(repo_id, filename="config.json")
                if model_cache_path is None:
                    logger.info(f"[响应] 模型 {repo_id} 不在本地缓存中，正在从 HuggingFace 下载...")
                    model_path = snapshot_download(repo_id=repo_id)
                    logger.info(f"[响应] 模型已下载到: {model_path}")
                else:
                    logger.info(f"[响应] 模型 {repo_id} 已在本地缓存中")
            except Exception as e:
                logger.error(f"[响应] 下载模型时出错: {e}")
                raise

            with open(f"{local_dir}/config.json", 'r', encoding='utf-8') as r:
                config = json.load(r)

            logger.info(f"[响应] 开始加载模型...")
            self.model = KModel(repo_id=repo_id, config=config, model=f"{local_dir}/{self.local_model_name}").to(device).eval()
            # self.model = KModel(model=f"{local_dir}/{self.local_model_name}").to(device).eval()
            logger.info(f"[响应] 模型加载完成 - 耗时: {time.time() - start_time:.3f}秒")
        else:
            logger.info(f"[响应] 模型已加载，无需重新加载")
            self.model.to(device).eval()

    async def _load_pipeline_en(self) -> None:
        if self.voice_tensor_en is None:
            logger.info(f"[响应] 加载管道: 开始加载英文音色...")
            start_time = time.time()
            self.voice_tensor_en = torch.load(f'{self.local_model_dir}/voices/{self.voice_en}.pt', weights_only=True)
            logger.info(f"[响应] 加载英文音色完成 - 耗时: {time.time() - start_time:.3f}秒")

        if self.pipeline_en is None:
            # 2. 定义英文处理回调函数
            # 这个函数会处理管道中识别出的英文片段
            logger.info(f"[响应] 加载管道: 开始创建英文管道...")
            start_time = time.time()
            self.pipeline_en = KPipeline(lang_code='a', repo_id=self.local_repo_id, model=False)
            logger.info(f"[响应] 创建英文管道完成 - 耗时: {time.time() - start_time:.3f}秒")


    def en_callable(self, text):
        # 可以为特定单词定制发音
        if text == 'Kokoro':
            return 'kˈOkəɹO'

        # 默认使用英文管道和英文音色来处理
        return next(self.pipeline_en(text, voice=self.voice_tensor_en)).phonemes


    async def _load_pipeline(self, tts_params: TTSParams) -> None:
        '''
        加载管道
        '''
        if self.pipeline is None:
            start_time = time.time()

            # 加载一个中文音色和一个英文音色
            logger.info(f"[响应] 加载管道: 开始加载权重...")
            self.voice_tensor_cn = torch.load(f'{self.local_model_dir}/voices/{tts_params.voice}.pt', weights_only=True)
            logger.info(f"[响应] 加载中文音色完成 - 耗时: {time.time() - start_time:.3f}秒")

            # 创建中文管道，并传入 en_callable
            logger.info(f"[响应] 加载管道: 开始创建中文管道...")
            start_time_pipeline = time.time()
            self.pipeline = KPipeline(lang_code='z', repo_id=self.local_repo_id, model=self.model, en_callable=self.en_callable)
            logger.info(f"[响应] 管道加载完成 - 耗时: {time.time() - start_time_pipeline:.3f}秒")


    async def _generate_audio(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """
        生成语音
        """
        logger.info(f"生成语音，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")
        rate_, volume_, pitch_, lang_ = self._params_adjustments(tts_params)

        start_time = time.time()

        # load model
        await self._load_model(repo_id=self.local_repo_id, local_dir=self.local_model_dir)

        # load pipeline_en
        await self._load_pipeline_en()

        # load pipeline
        await self._load_pipeline(tts_params)
        
        # 生成语音
        logger.info(f"开始生成语音...")
        start_time_pipeline = time.time()
        # 调用管道生成语音
        # 注意：这里假设管道的参数是 text, voice, speed, split_pattern
        # generator = self.pipeline(text, voice=tts_params.voice, speed=rate_, split_pattern=r'\n+')
        generator = self.pipeline(text, voice=self.voice_tensor_cn, speed=rate_, split_pattern=r'\n+')

        # 获取生成结果 (这是一个 KPipeline.Result 对象)
        result = next(generator)

        logger.info(f"文本长度：{len(text)}，生成语音耗时：{time.time() - start_time_pipeline:.3f}秒, 总耗时：{time.time() - start_time:.3f}秒")

        # 1. 访问 result.output.audio 获取 tensor
        # 根据日志: result.output 是 KModel.Output 对象，里面有个 audio 属性是 tensor
        audio_tensor = result.output.audio

        # 2. 将 PyTorch Tensor 转换为 NumPy 数组
        # .detach() 移除梯度追踪，.cpu() 确保在CPU内存中，.numpy() 转为 numpy
        audio_numpy = audio_tensor.detach().cpu().numpy()

        return audio_numpy

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> list[str]:
        logger.info(f"生成语音文件，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")
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
        logger.info(f"生成语音字节流，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")

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

        logger.info(f"生成语音流，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")

        audio_numpy = await self._generate_audio(text, tts_params)
        
        output_format = tts_params.response_format if hasattr(tts_params, 'response_format') else 'wav'

        audio_data = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=24000
        )
        
        yield audio_data


def test_kokoro():
    api = KokoroAPIV11()

    text = sys.argv[1] if len(sys.argv) > 1 else api.default_text

    tts_params = TTSParams(
        voice="zf_001",
        rate=0,
        volume=0,
        pitch=0,
        locale="zh-CN",
        response_format="wav"
    )

    file_name = asyncio.run(api.generate_tts_file(text, tts_params))

    print(file_name)

if __name__ == "__main__":
    test_kokoro()