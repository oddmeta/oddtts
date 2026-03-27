import logging
import os
import subprocess
import tempfile
import uuid
import asyncio

from kokoro import KPipeline
import soundfile as sf
import numpy as np
import torch

logger = logging.getLogger(__name__)

Kokoro_voices = {
    'Kokoro Voice (zh-CN, Xiaobei)': {'name': 'zf_xiaobei', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaobei'}, 
    'Kokoro Voice (zh-CN, Xiaoni)': {'name': 'zf_xiaoni', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoni'},
    'Kokoro Voice (zh-CN, Xiaoxiao)': {'name': 'zf_xiaoxiao', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoxiao'},
    'Kokoro Voice (zh-CN, Xiaoyi)': {'name': 'zf_xiaoyi', 'gender': 'Female', 'locale': 'zh-CN', 'short_name': 'zf_xiaoyi'},
    'Kokoro Voice (zh-CN, Yunjian)': {'name': 'zm_yunjian', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zh-CN-YunjianNeural'},
    'Kokoro Voice (zh-CN, Yunxi)': {'name': 'zm_yunxi', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zh-CN-YunxiNeural'}, 
    'Kokoro Voice (zh-CN, Yunyang)': {'name': 'zm_yunyang', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zh-CN-YunyangNeural'},
    'Kokoro Voice (zh-CN, Yunxia)': {'name': 'zm_yunxia', 'gender': 'Male', 'locale': 'zh-CN', 'short_name': 'zh-CN-YunxiaNeural'},
}

class KokoroAPI():

    def __init__(self) -> None:
        self.pipeline = None
        pass
    
    async def get_voices(self) -> list[dict[str, str]]:
        return list(Kokoro_voices.values())

    async def _check_voice(self, voice: str) -> bool:
        return voice in [voice['name'] for voice in Kokoro_voices.values()]

    @staticmethod
    def _new_uuid():
        """
        生成UUID
        """
        uuid_str = str(uuid.uuid4())
        uuid_str = uuid_str.replace("-", "")
        return uuid_str

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        # 确保参数格式正确，包含正负符号
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        # 初始化中文管线
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code='z')

        # 生成语音
        if text == "":
            text = "关注我的公众号：奥德元，一起学习 A I，一起追赶时代。"

        generator = self.pipeline(text, voice=voice)

        # 获取生成结果 (这是一个 KPipeline.Result 对象)
        result = next(generator)

        # 1. 访问 result.output.audio 获取 tensor
        # 根据日志: result.output 是 KModel.Output 对象，里面有个 audio 属性是 tensor
        audio_tensor = result.output.audio

        # 2. 将 PyTorch Tensor 转换为 NumPy 数组
        # .detach() 移除梯度追踪，.cpu() 确保在CPU内存中，.numpy() 转为 numpy
        audio_numpy = audio_tensor.detach().cpu().numpy()

        # 3. 处理维度
        # soundfile 需要 (样本数, 通道数) 的二维数组。
        # Kokoro 输出的通常是 (样本数,) 的一维数组，我们需要变成 (样本数, 1)
        if audio_numpy.ndim == 1:
            audio_numpy = audio_numpy.reshape(-1, 1)

        # 4. 获取采样率
        # Kokoro 的标准采样率通常是 24000，也可以检查是否有属性直接提供
        sample_rate = 24000 

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            output_file = f.name

        # 5. 写入文件
        sf.write(output_file, audio_numpy, sample_rate)

        return output_file

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        # 生成音频数据
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code='z')
        
        generator = self.pipeline(text, voice=voice)
        result = next(generator)
        audio_tensor = result.output.audio
        audio_numpy = audio_tensor.detach().cpu().numpy()
        
        # 转换为字节流
        import io
        buffer = io.BytesIO()
        sf.write(buffer, audio_numpy, 24000, format='WAV')
        audio_data = buffer.getvalue()
        
        return audio_data
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        # 生成音频数据并流式返回
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code='z')
        
        generator = self.pipeline(text, voice=voice)
        result = next(generator)
        audio_tensor = result.output.audio
        audio_numpy = audio_tensor.detach().cpu().numpy()
        
        # 转换为字节流
        import io
        buffer = io.BytesIO()
        sf.write(buffer, audio_numpy, 24000, format='WAV')
        audio_data = buffer.getvalue()

        yield audio_data

    @staticmethod
    def remove_html(text: str):
        # TODO 待改成正则
        new_text = text.replace('[', "")
        new_text = new_text.replace(']', "")
        return new_text

    @staticmethod
    def create_audio(text, voiceId, rate, volume, pitch):
        new_text = KokoroAPI.remove_html(text)
        pwdPath = os.getcwd()
        file_name = KokoroAPI._new_uuid() + ".wav"
        # filePath = f"{pwdPath}tmp/{file_name}"
        # dirPath = os.path.dirname(filePath)
        # if not os.path.exists(dirPath):
        #     os.makedirs(dirPath)
        # if not os.path.exists(filePath):
        #     # 用open创建文件 兼容mac
        #     open(filePath, 'a').close()

        # if voiceId == "":
        #     voiceId = "zf_xiaobei"
        #     print(f"using default voice: {voiceId}")

        # try:
        #     print(f"edge-tts --voice {voiceId} --text {new_text} --write-media {filePath}")
        #     subprocess.run(["edge-tts", "--voice", voiceId, "--text", new_text, "--write-media", str(filePath)])
        # except Exception as e:
        #     print(f"edge-tts error: {e}")
        #     return ""
        return file_name

def test_kokoro():
    api = KokoroAPI()
    text = "关注我的公众号：奥德元，一起学习 A I，一起追赶时代!"
    voice = "zf_xiaobei"
    voice = "zf_xiaoni"
    rate = 0
    volume = 0
    pitch = 0

    # file_name = asyncio.run(api.generate_tts_file(text, voice, rate, volume, pitch))
    file_name = asyncio.run(api.generate_tts_file(text, voice, rate, volume, pitch))

    print(file_name)

if __name__ == "__main__":
    test_kokoro()