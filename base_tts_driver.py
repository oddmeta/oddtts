from abc import ABC, abstractmethod
import logging

from oddtts.oddtts_params import ODDTTS_TYPE

from oddtts.tts_edge import EdgeTTSAPI
from oddtts.tts_bert_vits2 import BertVits2API
from oddtts.tts_bert_vits2_v2 import BertVits2V2API
from oddtts.tts_odd_gptsovits import OddGptSovitsAPI
from oddtts.tts_chattts import ChatTTSAPI

logger = logging.getLogger(__name__)

class BaseTTS(ABC):
    '''合成语音统一抽象类'''
    @abstractmethod
    async def get_voices(self) -> list[dict[str, str]]:
        '''获取声音列表'''
        pass

    @abstractmethod
    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        '''合成语音'''
        pass

    @abstractmethod
    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        '''生成语音文件'''
        pass

    @abstractmethod
    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        '''生成TTS音频并返回字节流'''
        pass

    @abstractmethod
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        '''生成TTS音频并返回字节流'''
        pass

class OddTTSEdge(BaseTTS):
    '''Edge 微软语音合成类'''
    async def get_voices(self) -> list[dict[str, str]]:
        return await self.client.get_voices()
    
    def __init__(self) -> None:
        self.client = EdgeTTSAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        return await EdgeTTSAPI.create_audio(text=text, voiceId=voice_id)

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return await self.client.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return await self.client.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        async for chunk in self.client.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

class OddTTSChatTTS(BaseTTS):
    '''Chattts语音合成类'''
    def __init__(self) -> None:
        self.client = ChatTTSAPI()

    async def get_voices(self) -> list[dict[str, str]]:
        return await self.client.get_voices()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        return await ChatTTSAPI.create_audio(text=text, voiceId=voice_id)

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return ChatTTSAPI.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return ChatTTSAPI.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        async for chunk in self.client.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

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

    async def get_voices(self) -> list[dict[str, str]]:
        return self.client.get_voices()

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return self.client.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return self.client.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        async for chunk in self.client.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

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

    async def get_voices(self) -> list[dict[str, str]]:
        return self.client.get_voices()

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return self.client.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return self.client.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        async for chunk in self.client.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

class OddTTSGPTSovits(BaseTTS):
    client: OddGptSovitsAPI

    def __init__(self):
        self.client = OddGptSovitsAPI()

    async def synthesis(self, text: str, voice_id: str, **kwargs) -> str:
        noise = kwargs.get("noise", "0.5")
        noisew = kwargs.get("noisew", "0.9")
        sdp_ratio = kwargs.get("sdp_ratio", "0.2")
        return self.client.create_audio(text=text, speaker=voice_id, noise=noise, noisew=noisew, sdp_ratio=sdp_ratio)

    async def get_voices(self) -> list[dict[str, str]]:
        return self.client.get_voices()

    async def generate_tts_file(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        return self.client.generate_tts_file(text=text, voiceId=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        return self.client.generate_tts_bytes(text=text, voiceId=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, text: str, voice: str, rate: int, volume: int, pitch: int):
        async for chunk in self.client.generate_tts_stream(text=text, voiceId=voice, rate=rate, volume=volume, pitch=pitch):
            yield chunk

class OddTTSDriver:
    '''TTS驱动类'''
    def __init__(self):
        self.strategies: dict[ODDTTS_TYPE, BaseTTS] = {}

    async def get_voices(self, type: str) -> list[dict[str, str]]:
        tts = self.get_strategy(type)
        return await tts.get_voices()

    async def synthesis(self, type: str, text: str, voice_id: str, **kwargs) -> str:
        tts = self.get_strategy(type)
        file_name = await tts.synthesis(text=text, voice_id=voice_id, **kwargs)
        logger.info(f"TTS synthesis # type:{type} text:{text} voice_id:{voice_id} => file_name: {file_name} #")
        return file_name

    async def generate_tts_file(self, type: str, text: str, voice: str, rate: int, volume: int, pitch: int) -> list[str]:
        tts = self.get_strategy(type)
        return await tts.generate_tts_file(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)

    async def generate_tts_bytes(self, type: str, text: str, voice: str, rate: int, volume: int, pitch: int) -> bytes:
        tts = self.get_strategy(type)
        return await tts.generate_tts_bytes(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    
    async def generate_tts_stream(self, type: str, text: str, voice: str, rate: int, volume: int, pitch: int):
        tts = self.get_strategy(type)
        async for chunk in tts.generate_tts_stream(text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
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
        else:
            #default use Edge TTS
            return OddTTSEdge()
            # raise ValueError("Unknown type")
