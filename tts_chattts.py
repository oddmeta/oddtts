import logging
import os
import subprocess

# import ChatTTS

from oddtts.oddtts_params import new_uuid

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
    
    async def generate_tts_file(self, text: str, voice: str) -> str:
        return self.create_audio(text, voice)
    
    async def generate_tts_bytes(self, text: str, voice: str) -> bytes:
        return self.create_audio(text, voice)
    
    async def generate_tts_stream(self, text: str, voice: str) -> bytes:
        audio_path = self.create_audio(text, voice)
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        return audio_data

    @staticmethod
    def remove_html(text: str):
        # TODO 待改成正则
        new_text = text.replace('[', "")
        new_text = new_text.replace(']', "")
        return new_text
    
    @staticmethod
    def create_audio(text, voiceId):
        new_text = ChatTTSAPI.remove_html(text)
        pwdPath = os.getcwd()
        file_name = new_uuid() + ".wav"
        filePath = pwdPath + "/tmp/" + file_name
        dirPath = os.path.dirname(filePath)
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        if not os.path.exists(filePath):
            # 用open创建文件 兼容mac
            open(filePath, 'a').close()

        subprocess.run(["edge-tts", "--voice", voiceId, "--text", new_text, "--write-media", str(filePath)])

        print("tts audio file: ", file_name)
        
        return file_name
