import os
import subprocess
import tempfile
import edge_tts

from oddtts.oddtts_params import new_uuid, TTSParams
from oddtts.oddtts_log import setup_logger

logger = setup_logger(__name__)

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

class MeloTTSAPI():

    def __init__(self) -> None:
        pass

    async def preload(self) -> None:
        '''MeloTTS 当前基于在线服务，无需预加载模型'''
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
    
    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        # 确保参数格式正确，包含正负符号
        rate_str = f"{tts_params.rate:+d}%"
        volume_str = f"{tts_params.volume:+d}%"
        pitch_str = f"{tts_params.pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            tts_params.voice, 
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

    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        rate_str = f"{tts_params.rate:+d}%"
        volume_str = f"{tts_params.volume:+d}%"
        pitch_str = f"{tts_params.pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            tts_params.voice, 
            rate=rate_str, 
            volume=volume_str, 
            pitch=pitch_str
        )
        
        # 将音频数据保存到字节流
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk.get("data", b"")
        
        return audio_data
    
    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        rate_str = f"{tts_params.rate:+d}%"
        volume_str = f"{tts_params.volume:+d}%"
        pitch_str = f"{tts_params.pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(
            text, 
            tts_params.voice, 
            rate=rate_str, 
            volume=volume_str, 
            pitch=pitch_str
        )
        
        # 直接yield音频数据块，而不是收集后返回
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk.get("data", b"")

