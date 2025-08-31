from abc import ABC, abstractmethod
import logging
from .tts_edge import TTS_Edge, TTS_edge_voices
from .tts_bert_vits2 import TTS_BertVits2
from .tts_omserver import TTS_OMServer
from .tts_chattts import TTS_ChatTTS

logger = logging.getLogger(__name__)

class BaseTTS(ABC):
    '''合成语音统一抽象类'''
    @abstractmethod
    def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        '''合成语音'''
        pass

    @abstractmethod
    def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        '''生成语音文件'''
        pass

    @abstractmethod
    def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        '''生成TTS音频并返回字节流'''
        pass

    @abstractmethod
    def get_voices(self) -> list[dict[str, str]]:
        '''获取声音列表'''
        pass

class TTSChatTTS(BaseTTS):
    '''Chattts语音合成类'''
    def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        return TTS_ChatTTS.create_audio(text=text, voiceId=voice_id)

    def get_voices(self) -> list[dict[str, str]]:
        return TTS_edge_voices

    def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return TTS_ChatTTS.create_audio(text=text, voiceId=voice)

    def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return TTS_ChatTTS.create_audio_bytes(text=text, voiceId=voice)

class TTSEdge(BaseTTS):
    '''Edge 微软语音合成类'''
    def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        print("1a")
        return TTS_Edge.create_audio(text=text, voiceId=voice_id)

    def get_voices(self) -> list[dict[str, str]]:
        return TTS_edge_voices

    def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return TTS_Edge.create_audio(text=text, voiceId=voice)

    def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return TTS_Edge.create_audio_bytes(text=text, voiceId=voice)

class TTSBertVITS2(BaseTTS):
    '''Bert-VITS2 语音合成类'''
    client: TTS_BertVits2

    def __init__(self):
        self.client = TTS_BertVits2()

    def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return self.client.do_synthesis(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

    def get_voices(self) -> list[dict[str, str]]:
        return self.client.get_voices()

class TTSOMServer(BaseTTS):
    client: TTS_OMServer

    def __init__(self):
        self.client = TTS_OMServer()

    def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return TTS_OMServer.create_audio(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

    def get_voices(self) -> list[dict[str, str]]:
        return TTS_OMServer.get_voices()

    def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return TTS_OMServer.create_audio(text=text, voiceId=voice)

    def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return TTS_OMServer.create_audio_bytes(text=text, voiceId=voice)

class TTSDriver:
    '''TTS驱动类'''
    def synthesis(self, type: str, text: str, voice_id: str, **kwargs) -> str:
        tts = self.get_strategy(type)
        file_name = tts.synthesis(text=text, voice_id=voice_id, kwargs=kwargs)
        logger.info(f"TTS synthesis # type:{type} text:{text} voice_id:{voice_id} => file_name: {file_name} #")
        return file_name

    def get_voices(self, type: str) -> list[dict[str, str]]:
        tts = self.get_strategy(type)
        return tts.get_voices()

    def get_strategy(self, type: str) -> BaseTTS:
        if type == "Edge":
            return TTSEdge()
        elif type == "ChatTTS":
            return TTSChatTTS()
        elif type == "Bert-VITS2":
            return TTSBertVITS2()
        elif type == "omtts":
            return TTSOMServer()
        else:
            #default use Edge TTS
            return TTSEdge()
            # raise ValueError("Unknown type")
