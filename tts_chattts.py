import logging
import os
import subprocess

# import ChatTTS

from oddtts.oddtts_params import new_uuid, TTSParams

logger = logging.getLogger(__name__)

chat_tts_voices = [
    {
        "name": "chat_tts",
        "display_name": "ChatTTS",
        "description": "ChatTTS",
    }
]

class ChatTTSAPI():

    # def inference(text: str):
    #     # 初始化ChatTTS
    #     chat = ChatTTS.Chat()
    #     chat.load_models()

    #     # 1. 随机选择一个说话者
    #     rand_spk = chat.sample_random_speaker() 
    #     # 2. 定义推理参数
    #     params_infer_code = {
    #         'spk_emb': rand_spk,  # 使用随机选择的说话者
    #         'temperature': 0.5,    # 调整语音变化 
    #     }

    #     # 3. 带有嵌入控制标记的文本
    #     text_with_tokens = "你最喜欢的颜色是什么？[uv_break][laugh]"

    #     # 4. 生成并保存音频
    #     wav = chat.infer(text_with_tokens, params_infer_code=params_infer_code)
    #     torchaudio.save("advanced_output.wav", torch.from_numpy(wav[0]), 24000)

    async def get_voices(self) -> list:
        return chat_tts_voices
    
    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        return self.create_audio(text, tts_params.voice)
    
    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        return self.create_audio(text, tts_params.voice)
    
    async def generate_tts_stream(self, text: str, tts_params: TTSParams) -> bytes:
        audio_path = self.create_audio(text, tts_params.voice)
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        return audio_data
