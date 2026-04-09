from enum import Enum
from typing import Any, Union

import uuid
import os
import tempfile
import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment

# from oddtts.oddtts_log import setup_logger
# logger = setup_logger(__name__)

class TTSParams:
    '''合成语音参数类'''
    voice: str
    rate: int
    volume: int
    pitch: int
    locale: str
    response_format: str

    def __init__(self, voice: str, rate: int, volume: int, pitch: int, locale: str = "zh-CN", response_format: str = "wav") -> None:
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.locale = locale
        self.response_format = response_format


def new_uuid():
    """
    生成UUID
    """
    uuid_str = str(uuid.uuid4())
    uuid_str = uuid_str.replace("-", "")
    return uuid_str

def remove_html(text: str):
    # TODO 待改成正则
    new_text = text.replace('[', "")
    new_text = new_text.replace(']', "")
    return new_text

def convert_audio_format(
    input_data: Any,
    input_type: str = "numpy",
    output_format: str = "wav",
    output_type: str = "file",
    sample_rate: int = 24000,
    output_path: str = "",
    bitrate: str = "128k"
) -> Union[str, bytes]: 
    """
    通用的音频格式转换函数
    
    Args:
        input_data: 输入数据，可以是numpy数组、文件路径或字节流
        input_type: 输入类型（"numpy", "file", "bytes"）
        output_format: 输出格式（"wav", "mp3", "ogg", "flac"等）
        output_type: 输出类型（"file" 返回文件路径, "bytes" 返回字节流）
        sample_rate: 采样率（仅当input_type="numpy"时需要）
        output_path: 输出文件路径（仅当output_type="file"时使用，为空则自动生成）
        bitrate: 比特率（仅对有损格式有效，如"128k", "192k", "320k"）
    
    Returns:
        根据output_type返回文件路径或字节流
    
    Examples:
        # numpy数组转MP3文件
        convert_audio_format(audio_numpy, "numpy", "mp3", "file", 24000)
        
        # WAV文件转MP3文件
        convert_audio_format("input.wav", "file", "mp3", "file")
        
        # numpy数组转MP3字节流
        convert_audio_format(audio_numpy, "numpy", "mp3", "bytes", 24000)
        
        # WAV文件转MP3字节流
        convert_audio_format("input.wav", "file", "mp3", "bytes")
    """
    try:
        
        if output_type == "file" and output_path == "":
            temp_dir = tempfile.gettempdir()
            uuid_str = new_uuid()
            output_path = os.path.join(temp_dir, f"{uuid_str}.{output_format}")
        
        audio = None
        
        if input_type == "numpy":
            if sample_rate is None:
                raise ValueError("当input_type='numpy'时，必须提供sample_rate参数")
            
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, input_data, sample_rate, format='WAV')
            wav_buffer.seek(0)
            audio = AudioSegment.from_wav(wav_buffer)
            
        elif input_type == "file":
            if not os.path.exists(input_data):
                raise FileNotFoundError(f"输入文件不存在: {input_data}")
            audio = AudioSegment.from_file(input_data)
            
        elif input_type == "bytes":
            wav_buffer = io.BytesIO(input_data)
            audio = AudioSegment.from_wav(wav_buffer)
            
        else:
            raise ValueError(f"不支持的输入类型: {input_type}")
        
        if output_type == "file":
            audio.export(output_path, format=output_format, bitrate=bitrate)
            return output_path
        elif output_type == "bytes":
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format=output_format, bitrate=bitrate)
            return output_buffer.getvalue()
        else:
            raise ValueError(f"不支持的输出类型: {output_type}")
            
    except Exception as e:
        raise RuntimeError(f"音频格式转换失败: {str(e)}")


def convert_wav_to_mp3(wav_file_path: str, mp3_file_path: str = "", bitrate: str = "128k") -> str:
    """
    将WAV文件转换为MP3格式（便捷函数）
    
    Args:
        wav_file_path: WAV文件路径
        mp3_file_path: 输出MP3文件路径，如果为空则自动生成
        bitrate: 比特率（默认128k）
    
    Returns:
        MP3文件路径
    """
    try:
        output_path = mp3_file_path

        if mp3_file_path == "":
            temp_dir = tempfile.gettempdir()
            uuid_str = new_uuid()
            output_path = os.path.join(temp_dir, f"{uuid_str}.mp3")
        
        audio = None
        
        if not os.path.exists(wav_file_path):
            raise FileNotFoundError(f"输入文件不存在: {wav_file_path}")
        audio = AudioSegment.from_file(wav_file_path)
        audio.export(output_path, format="mp3", bitrate=bitrate)

        return output_path
            
    except Exception as e:
        raise RuntimeError(f"音频格式转换失败: {str(e)}")

def convert_ndarray_to_format(audio_numpy: np.ndarray, sample_rate: int, output_format: str, output_file_path: str = "", bitrate: str = "128k") -> str:
    """
    将音频numpy数组转换为指定格式（便捷函数，保持向后兼容）

    Args:
        audio_numpy: 音频数据（numpy数组）
        sample_rate: 采样率
        output_format: 输出格式（'wav' 或 'mp3'）
        output_file_path: 输出文件路径，如果为空则自动生成
        bitrate: 比特率（默认128k）

    Returns:
        输出文件路径
    """
    # return convert_audio_format(
    #     input_data=audio_numpy,
    #     input_type="numpy",
    #     output_format=output_format,
    #     output_type="file",
    #     sample_rate=sample_rate,
    #     output_path=output_file_path
    # )

    try:
        
        if output_file_path == "":
            temp_dir = tempfile.gettempdir()
            uuid_str = new_uuid()
            output_file_path = os.path.join(temp_dir, f"{uuid_str}.{output_format}")
        
        audio = None
        
        if sample_rate is None:
            raise ValueError("当input_type='numpy'时，必须提供sample_rate参数")
        
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_numpy, sample_rate, format='WAV')
        wav_buffer.seek(0)
        audio = AudioSegment.from_wav(wav_buffer)
        
        audio.export(output_file_path, format=output_format, bitrate=bitrate)
        return output_file_path

    except Exception as e:
        raise RuntimeError(f"音频格式转换失败: {str(e)}")



class ODDTTS_TYPE(Enum):
    # 未知
    UNKNOWN = 0
    # ODD_GptSovits
    ODDTTS_GPTSOVITS = 1
    # EdgeTTS
    ODDTTS_EDGETTS = 2
    # ChatTTS
    ODDTTS_CHATTTS = 3
    # Bert Vits2
    ODDTTS_BERTVITS2 = 4
    # Bert Vits2 v2
    ODDTTS_BERTVITS2_V2 = 5
    # Kokoro
    ODDTTS_KOKORO = 6
    # Kokoro v1.1
    ODDTTS_KOKORO_V1_1 = 7

    @property
    def description(self):
        descriptions = {
            self.UNKNOWN: '未知类型',
            self.ODDTTS_GPTSOVITS: 'OddGPT-SoVITS - 基于GPT-SoVITS的语音合成引擎（需8G以上GPU）',
            self.ODDTTS_EDGETTS: 'EdgeTTS - 微软Edge浏览器的在线TTS服务(无需GPU)',
            self.ODDTTS_CHATTTS: 'ChatTTS - 专为对话场景设计的TTS引擎（需4G以上GPU）',
            self.ODDTTS_BERTVITS2: 'Bert-VITS2 - 基于BERT和VITS的语音合成（需4G以上GPU）',
            self.ODDTTS_BERTVITS2_V2: 'Bert-VITS2 V2 - Bert-VITS2的升级版本（需4G以上GPU）',
            self.ODDTTS_KOKORO: 'Kokoro - 轻量级多语言TTS引擎（纯CPU，中文）',
            self.ODDTTS_KOKORO_V1_1: 'Kokoro V1.1 - Kokoro引擎的1.1版本（纯CPU，中英混合）'
        }
        return descriptions[self]

    @property
    def enable(self):
        enabled = {
            self.UNKNOWN: False,
            self.ODDTTS_GPTSOVITS: True,
            self.ODDTTS_EDGETTS: True,
            self.ODDTTS_CHATTTS: True,
            self.ODDTTS_BERTVITS2: True,
            self.ODDTTS_BERTVITS2_V2: True,
            self.ODDTTS_KOKORO: True,
            self.ODDTTS_KOKORO_V1_1: True
        }
        return enabled[self]

    def __str__(self):
        return self.name.title()


class OddTtsModels():
    def __init__(self, tts_type: ODDTTS_TYPE):
        self.tts_type = tts_type
    
    def get_model_name(self):
        return self.tts_type.name.title()

    def get_model_description(self):
        return self.tts_type.description
    
    def get_model_enabled(self):
        return self.tts_type.enable

# ============================================
# 音频格式转换使用示例
# ============================================

if __name__ == "__main__":
    import numpy as np
    
    print("音频格式转换函数使用示例")
    print("="*50)
    
    # 示例1: numpy数组转MP3文件
    print("\n1. numpy数组转MP3文件:")
    audio_data = np.random.uniform(-1, 1, 24000).astype(np.float32)
    mp3_file = convert_audio_format(
        input_data=audio_data,
        input_type="numpy",
        output_format="mp3",
        output_type="file",
        sample_rate=24000
    )
    print(f"   生成文件: {mp3_file}")
    
    # 示例2: numpy数组转WAV文件
    print("\n2. numpy数组转WAV文件:")
    wav_file = convert_audio_format(
        input_data=audio_data,
        input_type="numpy",
        output_format="wav",
        output_type="file",
        sample_rate=24000
    )
    print(f"   生成文件: {wav_file}")
    
    # 示例3: WAV文件转MP3文件
    print("\n3. WAV文件转MP3文件:")
    mp3_file2 = convert_audio_format(
        input_data=wav_file,
        input_type="file",
        output_format="mp3",
        output_type="file"
    )
    print(f"   生成文件: {mp3_file2}")
    
    # 示例4: numpy数组转MP3字节流
    print("\n4. numpy数组转MP3字节流:")
    mp3_bytes = convert_audio_format(
        input_data=audio_data,
        input_type="numpy",
        output_format="mp3",
        output_type="bytes",
        sample_rate=24000
    )
    print(f"   生成字节流大小: {len(mp3_bytes)} bytes")
    
    # 示例5: WAV文件转MP3字节流
    print("\n5. WAV文件转MP3字节流:")
    mp3_bytes2 = convert_audio_format(
        input_data=wav_file,
        input_type="file",
        output_format="mp3",
        output_type="bytes"
    )
    print(f"   生成字节流大小: {len(mp3_bytes2)} bytes")
    
    # 示例6: 使用便捷函数
    print("\n6. 使用便捷函数 (向后兼容):")
    mp3_file3 = convert_ndarray_to_format(audio_data, 24000, "mp3")
    print(f"   生成文件: {mp3_file3}")
    
    mp3_file4 = convert_wav_to_mp3(wav_file) # type: ignore
    print(f"   生成文件: {mp3_file4}")
    
    print("\n" + "="*50)
    print("所有示例执行完成!")
    print("\n支持的格式: wav, mp3, ogg, flac 等")
    print("支持的比特率: 128k, 192k, 320k 等")
    print("\n注意: 需要安装 FFmpeg 才能使用 pydub 进行格式转换")