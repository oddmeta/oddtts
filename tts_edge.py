import logging
import os
import subprocess
import tempfile
import edge_tts

from oddtts.oddtts_params import new_uuid, TTSParams

logger = logging.getLogger(__name__)

class EdgeTTSAPI():

    def __init__(self) -> None:
        pass
    
    async def get_voices(self) -> list[dict[str, str]]:
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
    
    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> list[str]:
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
                audio_data += chunk["data"]
        
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
                yield chunk["data"]