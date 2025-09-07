import logging
import os
import subprocess
import tempfile
import edge_tts

from oddtts_params import new_uuid

logger = logging.getLogger(__name__)

TTS_edge_voices = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "xiaoxiao"},
    {"id": "zh-CN-XiaoyiNeural", "name": "xiaoyi"},
    {"id": "zh-CN-YunjianNeural", "name": "yunjian"},
    {"id": "zh-CN-YunxiNeural", "name": "yunxi"},
    {"id": "zh-CN-YunxiaNeural", "name": "yunxia"},
    {"id": "zh-CN-YunyangNeural", "name": "yunyang"},
    {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "xiaobei"},
    {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "xiaoni"},
    {"id": "zh-HK-HiuGaaiNeural", "name": "hiugaai"},
    {"id": "zh-HK-HiuMaanNeural", "name": "hiumaan"},
    {"id": "zh-HK-WanLungNeural", "name": "wanlung"},
    {"id": "zh-TW-HsiaoChenNeural", "name": "hsiaochen"},
    {"id": "zh-TW-HsiaoYuNeural", "name": "hsioayu"},
    {"id": "zh-TW-YunJheNeural", "name": "yunjhe"}
]

class EdgeTTSAPI():

    def __init__(self) -> None:
        pass
    
    async def get_voices(self) -> list[dict[str, str]]:
        # return TTS_edge_voices
        voice_list = []
        voices = await edge_tts.list_voices()
        for v in voices:
            # 只提取确保存在的字段，避免KeyError
            voice_info = {
                "name": v.get("Name"),
                "gender": v.get("Gender"),
                "locale": v.get("Locale"),
                "short_name": v.get("ShortName")
            }
            
            # 可选字段，存在才添加
            if "LocalName" in v:
                voice_info["local_name"] = v["LocalName"]
                
            voice_list.append(voice_info)

        return voice_list
    
    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        # 确保参数格式正确，包含正负符号
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            voice, 
            rate=rate_str, 
            volume=volume_str, 
            pitch=pitch_str
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            output_file = f.name
        
        # 生成音频
        await communicate.save(output_file)

        return output_file

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            voice, 
            rate=rate_str, 
            volume=volume_str, 
            pitch=pitch_str
        )
        
        # 将音频数据保存到字节流
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return audio_data
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        rate_str = f"{rate:+d}%"
        volume_str = f"{volume:+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            voice, 
            rate=rate_str, 
            volume=volume_str, 
            pitch=pitch_str
        )
        
        # 直接yield音频数据块，而不是收集后返回
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    @staticmethod
    def remove_html(text: str):
        # TODO 待改成正则
        new_text = text.replace('[', "")
        new_text = new_text.replace(']', "")
        return new_text

    @staticmethod
    def create_audio(text, voiceId, rate, volume, pitch):
        new_text = EdgeTTSAPI.remove_html(text)
        pwdPath = os.getcwd()
        file_name = new_uuid() + ".mp3"
        filePath = f"{pwdPath}tmp/{file_name}"
        dirPath = os.path.dirname(filePath)
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        if not os.path.exists(filePath):
            # 用open创建文件 兼容mac
            open(filePath, 'a').close()

        if voiceId == "":
            voiceId = "zh-HK-WanLungNeural";
            print(f"using default voice: {voiceId}")

        try:
            print(f"edge-tts --voice {voiceId} --text {new_text} --write-media {filePath}")
            subprocess.run(["edge-tts", "--voice", voiceId, "--text", new_text, "--write-media", str(filePath)])
        except Exception as e:
            print(f"edge-tts error: {e}")
            return ""
        return file_name
