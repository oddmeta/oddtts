import asyncio
import time
import json
import sys

from kokoro import KPipeline, KModel
import numpy as np
import torch

from utils.model_utils import download_model
from oddtts_params import new_uuid, TTSParams, convert_audio_format, convert_ndarray_to_format
from oddtts_log import setup_logger

logger = setup_logger(__name__)

KokoroV11_voices = {
    'Kokoro Voice (zh-CN, zf_001)': {'name': 'zf_001', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_001'}, 
    'Kokoro Voice (zh-CN, zf_002)': {'name': 'zf_002', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_002'},
    'Kokoro Voice (zh-CN, zf_003)': {'name': 'zf_003', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_003'},
    'Kokoro Voice (zh-CN, zf_004)': {'name': 'zf_004', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_004'},
    'Kokoro Voice (zh-CN, zm_009)': {'name': 'zm_009', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_009'},
    'Kokoro Voice (zh-CN, zm_010)': {'name': 'zm_010', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_010'}, 
    'Kokoro Voice (zh-CN, zm_011)': {'name': 'zm_011', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_011'},
    'Kokoro Voice (zh-CN, zm_012)': {'name': 'zm_012', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zm_012'},
}

class KokoroAPIV11():

    def __init__(self) -> None:
        self.model = None
        self.local_repo_id = "hexgrad/Kokoro-82M-v1.1-zh"
        self.local_model_name = "kokoro-v1_1-zh.pth"
        self._init_local_model_dir()
        self.default_text = "关注我的公众号：奥德元，一起学习 AI，一起追赶时代。Good good study, day day up."
        # 中文音色张量
        self.pipeline = None
        self.voice = "zm_009"
        self.voice_tensor_cn = None
        # 中英混合-英文管道
        self.pipeline_en = None
        self.voice_en = "af_maple"
        self.voice_tensor_en = None

    def _init_local_model_dir(self):
        import os
        possible_dirs = [
            os.path.join(os.getcwd(), "ckpts"),
            os.path.join(os.path.dirname(__file__), "ckpts"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "ckpts"),
        ]
        for dir_path in possible_dirs:
            config_path = os.path.join(dir_path, "config.json")
            model_path = os.path.join(dir_path, self.local_model_name)
            if os.path.exists(config_path) and os.path.exists(model_path):
                self.local_model_dir = dir_path
                logger.info(f"[响应] 找到模型目录: {self.local_model_dir}")
                return
        self.local_model_dir = "ckpts"
        logger.info(f"[响应] 未找到本地模型目录，使用默认路径: {self.local_model_dir}")
    
    async def preload(self, device: str = 'cpu') -> None:
        '''预加载模型：触发模型检测/下载并加载到内存'''
        logger.info("[预加载] 开始预加载 Kokoro v1.1 模型...")
        await self._load_model(repo_id=self.local_repo_id, local_dir=self.local_model_dir, device=device)
        logger.info("[预加载] Kokoro v1.1 模型预加载完成")

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
        加载模型，优先使用本地 ckpts 目录，若本地不存在则尝试从 HuggingFace 下载
        '''
        if self.model is None:
            start_time = time.time()
            
            import os
            local_config_path = os.path.join(local_dir, "config.json")
            local_model_path = os.path.join(local_dir, self.local_model_name)
            
            if os.path.exists(local_config_path) and os.path.exists(local_model_path):
                logger.info(f"[响应] 本地 ckpts 目录已存在模型文件，跳过 HuggingFace 下载")
            else:
                logger.info(f"[响应] 本地目录不存在模型文件，使用通用接口获取模型...")
                try:
                    model_path = download_model(repo_id=repo_id)
                    logger.info(f"[响应] 模型路径: {model_path}")
                    local_config_path = os.path.join(model_path, "config.json")
                    local_model_path = os.path.join(model_path, self.local_model_name)
                    logger.info(f"[响应] config路径: {local_config_path}")
                    logger.info(f"[响应] model路径: {local_model_path}")
                except Exception as e:
                    logger.error(f"[响应] 获取模型时出错: {e}")
                    raise

            with open(local_config_path, 'r', encoding='utf-8') as r:
                config = json.load(r)

            logger.info(f"[响应] 开始加载模型...")
            self.model = KModel(repo_id=repo_id, config=config, model=local_model_path).to(device).eval()
            self.local_model_dir = os.path.dirname(local_model_path)
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
            logger.info(f"[响应] 加载管道: 开始创建英文管道...")
            start_time = time.time()
            self.pipeline_en = KPipeline(lang_code='a', repo_id=self.local_repo_id, model=self.model)
            logger.info(f"[响应] 创建英文管道完成 - 耗时: {time.time() - start_time:.3f}秒")


    def en_callable(self, text):
        # 可以为特定单词定制发音
        if text == 'Kokoro':
            return 'kˈOkəɹO'

        # 默认使用英文管道和英文音色来处理英文文本
        if self.pipeline_en is None or self.voice_tensor_en is None:
            logger.warning(f"英文管道或英文音色未加载，无法处理英文文本: {text}")
            return text  # 返回原始文本，可能会被中文管道处理成不理想的发音
        
        return next(self.pipeline_en(text, voice=self.voice_tensor_en)).phonemes


    async def _load_pipeline(self, tts_params: TTSParams) -> None:
        '''
        加载管道
        '''
        if self.pipeline is None:
            start_time = time.time()
            logger.info(f"[响应] 加载管道: 开始创建中文管道...")
            self.pipeline = KPipeline(lang_code='z', repo_id=self.local_repo_id, model=self.model, en_callable=self.en_callable)
            logger.info(f"[响应] 管道加载完成 - 耗时: {time.time() - start_time:.3f}秒")


    async def _generate_audio(self, text: str, tts_params: TTSParams) -> np.ndarray:
        """
        生成语音
        """
        logger.info(f"生成语音，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")
        rate_, volume_, pitch_, lang_ = self._params_adjustments(tts_params)

        start_time = time.time()

        # load model
        await self._load_model(repo_id=self.local_repo_id, local_dir=self.local_model_dir)

        # 加载一个中文音色和一个英文音色
        if self.voice != tts_params.voice:
            logger.info(f"[响应] 开始加载中文音色：{tts_params.voice}...")
            self.voice_tensor_cn = torch.load(f'{self.local_model_dir}/voices/{tts_params.voice}.pt', weights_only=True)
            logger.info(f"[响应] 加载中文音色：{tts_params.voice}完成 - 耗时: {time.time() - start_time:.3f}秒")


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
        if self.pipeline is None:
            logger.error("管道未加载，无法生成语音")
            raise RuntimeError("Pipeline not loaded")
        generator = self.pipeline(text, voice=self.voice_tensor_cn, speed=rate_, split_pattern=r'\n+')

        # 获取生成结果 (这是一个 KPipeline.Result 对象)
        result = next(generator)

        logger.info(f"文本长度：{len(text)}，生成语音耗时：{time.time() - start_time_pipeline:.3f}秒, 总耗时：{time.time() - start_time:.3f}秒")

        # 1. 访问 result.output.audio 获取 tensor
        # 根据日志: result.output 是 KModel.Output 对象，里面有个 audio 属性是 tensor
        if result.output is None or result.output.audio is None:
            logger.error("生成结果中没有 audio 属性，无法转换为 numpy 数组")
            raise ValueError("生成结果中没有 audio 属性")

        audio_tensor = result.output.audio

        # 2. 将 PyTorch Tensor 转换为 NumPy 数组
        # .detach() 移除梯度追踪，.cpu() 确保在CPU内存中，.numpy() 转为 numpy
        audio_numpy = audio_tensor.detach().cpu().numpy()

        return audio_numpy

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
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
        result = convert_ndarray_to_format(audio_numpy, sample_rate, output_format)
        
        if isinstance(result, str):
            return result
        else:
            raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        logger.info(f"生成语音字节流，参数：locale={tts_params.locale}, voice={tts_params.voice}, rate={tts_params.rate}, volume={tts_params.volume}, pitch={tts_params.pitch}")

        audio_numpy = await self._generate_audio(text, tts_params)
        
        output_format = tts_params.response_format if hasattr(tts_params, 'response_format') else 'wav'
                
        result = convert_audio_format(
            input_data=audio_numpy,
            input_type="numpy",
            output_format=output_format,
            output_type="bytes",
            sample_rate=24000
        )
        
        if isinstance(result, bytes):
            return result
        else:
            raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")
    
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