from abc import ABC, abstractmethod
import logging

from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams

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

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> list[str]:
        '''生成语音文件'''
        return await self.client.generate_tts_file(text=text, tts_params=tts_params)
        
    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        '''生成TTS音频并返回字节流'''
        return await self.client.generate_tts_bytes(text=text, tts_params=tts_params)

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        '''生成TTS音频并返回字节流'''
        async for chunk in self.client.generate_tts_stream(text=text, tts_params=tts_params):
            yield chunk

class OddTTSDriver:
    '''TTS驱动类'''
    def __init__(self, type: ODDTTS_TYPE):
        self.strategies: dict[ODDTTS_TYPE, BaseTTS] = {}
        self.tts = self.get_strategy(type)

    async def get_voices(self, type: ODDTTS_TYPE) -> list[dict[str, str]]:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        
        return await self.tts.get_voices()

    async def generate_tts_file(self, type: ODDTTS_TYPE, text: str, tts_params: TTSParams) -> list[str]:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        return await self.tts.generate_tts_file(text=text, tts_params=tts_params)

    async def generate_tts_bytes(self, type: ODDTTS_TYPE, text: str, tts_params: TTSParams) -> bytes:
        if self.tts is None:
            self.tts = self.get_strategy(type)
        return await self.tts.generate_tts_bytes(text=text, tts_params=tts_params)
    
    async def generate_tts_stream(self, type: ODDTTS_TYPE, text: str, tts_params: TTSParams):
        if self.tts is None:
            self.tts = self.get_strategy(type)

        async for chunk in self.tts.generate_tts_stream(text=text, tts_params=tts_params):
            yield chunk

    def get_strategy(self, type: ODDTTS_TYPE) -> BaseTTS:
        tts = BaseTTS()
        if type == ODDTTS_TYPE.ODDTTS_EDGETTS:
            tts.client = EdgeTTSAPI()
            return tts
        elif type == ODDTTS_TYPE.ODDTTS_CHATTTS:
            tts.client = ChatTTSAPI()
            return tts
        elif type == ODDTTS_TYPE.ODDTTS_BERTVITS2:
            tts.client = BertVits2API()
            return tts
        elif type == ODDTTS_TYPE.ODDTTS_BERTVITS2_V2:
            tts.client = BertVits2V2API()
            return tts
        elif type == ODDTTS_TYPE.ODDTTS_GPTSOVITS:
            tts.client = OddGptSovitsAPI()
            return tts
        elif type == ODDTTS_TYPE.ODDTTS_KOKORO:
            tts.client = KokoroAPI()
            return tts
        else:
            #fallback: default use Edge TTS
            tts.client = EdgeTTSAPI()
            return tts
            # raise ValueError("Unknown type")

