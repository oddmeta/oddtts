import logging
import os
import subprocess

from oddtts.oddtts_params import new_uuid

logger = logging.getLogger(__name__)

edge_voices = [
    {"id": "zh-CN-Jacky", "name": "jacky"},
    {"id": "zh-CN-Catherine", "name": "catherine"},
    {"id": "zh-CN-Lucy", "name": "lucy"},
    {"id": "zh-CN-Cici", "name": "Cici"}
]


class OddGptSovitsAPI():
    def __init__(self) -> None:
        pass

    async def get_voices(self) -> list[dict[str, str]]:
        return edge_voices
    
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
        new_text = OddGptSovitsAPI.remove_html(text)
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
