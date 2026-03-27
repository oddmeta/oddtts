from abc import ABC, abstractmethod
import logging

from oddtts.oddtts_params import ODDTTS_TYPE

from oddtts.tts_edge import EdgeTTSAPI
from oddtts.tts_bert_vits2 import BertVits2API
from oddtts.tts_bert_vits2_v2 import BertVits2V2API
from oddtts.tts_odd_gptsovits import OddGptSovitsAPI
from oddtts.tts_chattts import ChatTTSAPI
from oddtts.tts_kokoro import KokoroAPI

logger = logging.getLogger(__name__)

class BaseTTS(ABC):
    '''合成语音统一抽象类'''

    def __init__(self) -> None:
        self.client = None

    async def get_voices(self) -> list[dict[str, str]]:
        return await self.client.get_voices()

    @abstractmethod
    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        '''合成语音'''
        pass

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        '''生成语音文件'''
        return await self.client.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        '''生成TTS音频并返回字节流'''
        return await self.client.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        '''生成TTS音频并返回字节流'''
        async for chunk in self.client.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

class OddTTSEdge(BaseTTS):
    '''Edge 微软语音合成类'''
    
    def __init__(self) -> None:
        self.client = EdgeTTSAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        return await EdgeTTSAPI.create_audio(text=text, voiceId=voice_id)

class OddTTSChatTTS(BaseTTS):
    '''Chattts语音合成类'''
    def __init__(self) -> None:
        self.client = ChatTTSAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        return await self.client.create_audio(text=text, voiceId=voice_id)

class OddTTSBertVits2(BaseTTS):
    '''Bert-VITS2 语音合成类'''
    client: BertVits2API

    def __init__(self):
        self.client = BertVits2API()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return await self.client.do_synthesis(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

class OddTTSBertVITS2V2(BaseTTS):
    '''Bert-VITS2 语音合成类'''
    client: BertVits2V2API
    def __init__(self):
        self.client = BertVits2V2API()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return await self.client.generate_audio(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

class OddTTSGPTSovits(BaseTTS):
    client: OddGptSovitsAPI

    def __init__(self):
        self.client = OddGptSovitsAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return await self.client.create_audio(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

class OddTTSKokoro(BaseTTS):
    '''Kokoro 语音合成类'''
    client: KokoroAPI
    def __init__(self):
        self.client = KokoroAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return await self.client.generate_audio(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

class OddTTSDriver:
    '''TTS驱动类'''
    def __init__(self, type: ODDTTS_TYPE):
        self.strategies: dict[ODDTTS_TYPE, BaseTTS] = {}
        self.tts = self.get_strategy(type)

    async def get_voices(self, type: ODDTTS_TYPE) -> list[dict[str, str]]:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        
        return await self.tts.get_voices()

    async def synthesis(self, type: ODDTTS_TYPE, text: str, voice_id: str, **kwargs) -> str:
        if self.tts is None:
            self.tts = self.get_strategy(type)

        file_name = await self.tts.synthesis(text=text, voice_id=voice_id, **kwargs)
        logger.info(f"TTS synthesis # type:{type} text:{text} voice_id:{voice_id} => file_name: {file_name} #")
        return file_name

    async def generate_tts_file(self, type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        return await self.tts.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        return await self.tts.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int):
        if self.tts is None:
            self.tts = self.get_strategy(type)

        async for chunk in self.tts.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

    def get_strategy(self, type: ODDTTS_TYPE) -> BaseTTS:
        if type == ODDTTS_TYPE.ODDTTS_EDGETTS:
            return OddTTSEdge()
        elif type == ODDTTS_TYPE.ODDTTS_CHATTTS:
            return OddTTSChatTTS()
        elif type == ODDTTS_TYPE.ODDTTS_BERTVITS2:
            return OddTTSBertVits2()
        elif type == ODDTTS_TYPE.ODDTTS_BERTVITS2_V2:
            return OddTTSBertVITS2V2()
        elif type == ODDTTS_TYPE.ODDTTS_GPTSOVITS:
            return OddTTSGPTSovits()
        elif type == ODDTTS_TYPE.ODDTTS_KOKORO:
            return OddTTSKokoro()
        else:
            #fallback: default use Edge TTS
            return OddTTSEdge()
            # raise ValueError("Unknown type")

