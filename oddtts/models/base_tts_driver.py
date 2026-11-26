from abc import ABC, abstractmethod
from typing import Any

from oddtts.oddtts_params import ODDTTS_TYPE, TTSParams
from oddtts.oddtts_log import setup_logger

from .tts_edge import EdgeTTSAPI
from .tts_bert_vits2 import BertVits2API
from .tts_bert_vits2_v2 import BertVits2V2API
from .tts_odd_gptsovits import OddGptSovitsAPI
from .tts_chattts import ChatTTSAPI
from .tts_kokoro import KokoroAPI
from .tts_kokoro_v11 import KokoroAPIV11
from .tts_audio8_0_1b_onnx_int8 import Audio8_0_1b_OnnxInt8_API
from .tts_audio8_0_6b_onnx_int4 import Audio8_0_6b_OnnxInt4_API
from .tts_moss_nano import MossNanoAPI
from .tts_zipvoice import ZipVoiceAPI

logger = setup_logger(__name__)

MODEL_NAME_MAP: dict[str, ODDTTS_TYPE] = {
    "oddtts-edgetts": ODDTTS_TYPE.ODDTTS_EDGETTS,
    "oddtts-chattts": ODDTTS_TYPE.ODDTTS_CHATTTS,
    "oddtts-bertvits2": ODDTTS_TYPE.ODDTTS_BERTVITS2,
    "oddtts-bertvits2-v2": ODDTTS_TYPE.ODDTTS_BERTVITS2_V2,
    "oddtts-gptsovits": ODDTTS_TYPE.ODDTTS_GPTSOVITS,
    "oddtts-kokoro": ODDTTS_TYPE.ODDTTS_KOKORO,
    "oddtts-kokoro-v1-1": ODDTTS_TYPE.ODDTTS_KOKORO_V1_1,
    "oddtts-audio8-0-1b-onnx-int8": ODDTTS_TYPE.ODDTTS_AUDIO8_0_1B_ONNX_INT8,
    "oddtts-audio8-0-6b-onnx-int4": ODDTTS_TYPE.ODDTTS_AUDIO8_0_6B_ONNX_INT4,
    "oddtts-moss-nano": ODDTTS_TYPE.ODDTTS_MOSS_NANO,
    "oddtts-zipvoice": ODDTTS_TYPE.ODDTTS_ZIPVOICE,
}


def resolve_model_name(model_name: str) -> ODDTTS_TYPE:
    """将 model name 解析为 ODDTTS_TYPE。

    支持 oddtts-<kebab-name> 格式，以及 ODDTTS_TYPE 枚举名本身（大小写不敏感）。
    """
    if not model_name or not isinstance(model_name, str):
        raise ValueError("model name 不能为空")

    key = model_name.strip().lower()
    tts_type = MODEL_NAME_MAP.get(key)
    if tts_type is not None:
        return tts_type

    # 尝试匹配枚举名（如 "ODDTTS_KOKORO_V1_1" 或 "kokoro_v1_1"）
    upper_key = key.upper()
    for t in ODDTTS_TYPE:
        if t.name.upper() == upper_key:
            return t
        # 也支持不带 ODDTTS_ 前缀的枚举名，如 "KOKORO_V1_1"
        if t.name.upper().replace("ODDTTS_", "") == upper_key.replace("ODDTTS_", ""):
            return t

    valid_names = ", ".join(MODEL_NAME_MAP.keys())
    raise ValueError(f"未知的 model: {model_name}。有效的 model 名称: {valid_names}")

class BaseTTS(ABC):
    '''合成语音统一抽象类'''

    def __init__(self) -> None:
        self.client: Any = None

    async def get_voices(self) -> list[dict[str, str]]:
        if self.client is None:
            raise RuntimeError("TTS client is not initialized")
        
        return await self.client.get_voices()

    async def generate_tts_file(self, text: str, tts_params: TTSParams) -> str:
        '''生成语音文件'''
        if self.client is None:
            raise RuntimeError("TTS client is not initialized")
        
        return await self.client.generate_tts_file(text=text, tts_params=tts_params)
        
    async def generate_tts_bytes(self, text: str, tts_params: TTSParams) -> bytes:
        '''生成TTS音频并返回字节流'''
        if self.client is None:
            raise RuntimeError("TTS client is not initialized")

        result = await self.client.generate_tts_bytes(text=text, tts_params=tts_params)

        if isinstance(result, bytes):
            return result
        else:
            raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")

    async def generate_tts_stream(self, text: str, tts_params: TTSParams):
        '''生成TTS音频并返回字节流'''
        if self.client is None:
            raise RuntimeError("TTS client is not initialized")

        async for chunk in self.client.generate_tts_stream(text=text, tts_params=tts_params):
            yield chunk

    async def preload(self) -> None:
        '''预加载模型（可选，由具体 client 决定是否实现）'''
        if self.client is not None and hasattr(self.client, 'preload'):
            await self.client.preload()

    def unload(self) -> None:
        '''卸载模型并释放资源'''
        if self.client is not None:
            # 尝试调用客户端自定义的 unload
            if hasattr(self.client, 'unload') and callable(getattr(self.client, 'unload')):
                try:
                    self.client.unload()
                except Exception as e:
                    logger.warning(f"客户端 unload 失败: {e}")

            # 通用清理：释放常见的大型属性
            for attr in ('model', 'pipeline', 'pipeline_en', 'tts', 'runtime', 'session', 'sess'):
                if hasattr(self.client, attr):
                    try:
                        setattr(self.client, attr, None)
                    except Exception:
                        pass

            self.client = None

class OddTTSDriver:
    '''TTS驱动类'''
    def __init__(self, type: ODDTTS_TYPE):
        self.type = type
        self.strategies: dict[ODDTTS_TYPE, BaseTTS] = {}
        self.tts = self._get_or_create_strategy(type)

    def _get_or_create_strategy(self, tts_type: ODDTTS_TYPE) -> BaseTTS:
        if tts_type not in self.strategies:
            self.strategies[tts_type] = self.get_strategy(tts_type)
        return self.strategies[tts_type]

    async def get_voices(self, type: ODDTTS_TYPE) -> list[dict[str, str]]:
        strategy = self._get_or_create_strategy(type)
        return await strategy.get_voices()

    async def generate_tts_file(self, tts_type: ODDTTS_TYPE, text: str, tts_params: TTSParams) -> str:
        strategy = self._get_or_create_strategy(tts_type)
        result = await strategy.generate_tts_file(text=text, tts_params=tts_params)
        if isinstance(result, str):
            return result
        else:
            raise TypeError(f"期望返回 str 类型，但得到 {type(result).__name__}")

    async def generate_tts_bytes(self, tts_type: ODDTTS_TYPE, text: str, tts_params: TTSParams) -> bytes:
        strategy = self._get_or_create_strategy(tts_type)
        result = await strategy.generate_tts_bytes(text=text, tts_params=tts_params)
        if isinstance(result, bytes):
            return result
        else:
            raise TypeError(f"期望返回 bytes 类型，但得到 {type(result).__name__}")

    async def generate_tts_stream(self, tts_type: ODDTTS_TYPE, text: str, tts_params: TTSParams):
        strategy = self._get_or_create_strategy(tts_type)
        async for chunk in strategy.generate_tts_stream(text=text, tts_params=tts_params):
            yield chunk

    async def preload(self) -> None:
        '''预加载当前 TTS 引擎的模型'''
        strategy = self._get_or_create_strategy(self.type)
        await strategy.preload()

    def resolve_model_name(self, model_name: str) -> ODDTTS_TYPE:
        '''通过 model name 解析对应的 ODDTTS_TYPE'''
        return resolve_model_name(model_name)

    def list_loaded_models(self) -> list[dict]:
        '''返回当前已缓存的模型列表'''
        result = []
        for tts_type, strategy in self.strategies.items():
            info = {
                'model_name': f'oddtts-{tts_type.name.lower().replace("oddtts_", "").replace("_", "-")}',
                'tts_type': tts_type.name,
                'tts_value': tts_type.value,
                'description': tts_type.description,
            }
            # 判断模型权重是否已加载到内存
            if strategy.client is not None:
                client = strategy.client
                if hasattr(client, 'model') and client.model is not None:
                    info['model_status'] = 'loaded'
                elif hasattr(client, 'tts') and client.tts is not None:
                    info['model_status'] = 'loaded'
                elif hasattr(client, 'runtime') and client.runtime is not None:
                    info['model_status'] = 'loaded'
                elif hasattr(client, 'pipeline') and client.pipeline is not None:
                    info['model_status'] = 'loaded'
                else:
                    info['model_status'] = 'initialized'
            else:
                info['model_status'] = 'unknown'
            result.append(info)
        return result

    def unload_model(self, model_name: str) -> bool:
        '''卸载指定模型并释放内存'''
        tts_type = resolve_model_name(model_name)
        if tts_type not in self.strategies:
            raise ValueError(f"模型 {model_name} 未加载")

        strategy = self.strategies[tts_type]
        strategy.unload()
        del self.strategies[tts_type]

        # 如果卸载的是当前默认 tts，也清理 self.tts
        if self.tts is strategy:
            self.tts = None

        import gc
        gc.collect()

        return True

    def get_strategy(self, tts_type: ODDTTS_TYPE) -> BaseTTS:
        tts = BaseTTS()
        if tts_type == ODDTTS_TYPE.ODDTTS_EDGETTS:
            tts.client = EdgeTTSAPI()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_CHATTTS:
            tts.client = ChatTTSAPI()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_BERTVITS2:
            tts.client = BertVits2API()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_BERTVITS2_V2:
            tts.client = BertVits2V2API()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_GPTSOVITS:
            tts.client = OddGptSovitsAPI()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_KOKORO:
            tts.client = KokoroAPI()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_KOKORO_V1_1:
            tts.client = KokoroAPIV11()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_AUDIO8_0_1B_ONNX_INT8:
            tts.client = Audio8_0_1b_OnnxInt8_API()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_AUDIO8_0_6B_ONNX_INT4:
            tts.client = Audio8_0_6b_OnnxInt4_API()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_MOSS_NANO:
            tts.client = MossNanoAPI()
            return tts
        elif tts_type == ODDTTS_TYPE.ODDTTS_ZIPVOICE:
            tts.client = ZipVoiceAPI()
            return tts
        else:
            logger.error(f"Unknown type: {tts_type}, fallback to Edge TTS")
            #fallback: default use Edge TTS
            # raise ValueError("Unknown type")
            tts.client = EdgeTTSAPI()
            return tts
