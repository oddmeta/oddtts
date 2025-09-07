import json
import os
import uuid

import requests
import logging

from oddtts_params import new_uuid

logger = logging.getLogger(__name__)

# url = "https://v2.genshinvoice.top/run/predict"
# url_new = "https://v2.genshinvoice.top/v1/tts"
url = "https://bv2.firefly.matce.cn/run/predict"

# https://v2.genshinvoice.top/api?speaker=%E5%AE%89%E8%A5%BF_ZH&text=%E5%9F%BA%E5%9F%BA%E5%85%B6%E5%AE%9E%E6%98%AF%E5%9F%BA%E5%9F%BA%E5%B7%A6%E5%8F%B3&format=wav&language=%E8%AF%AD%E8%A8%80&length=1&noise=0.1&noisew=0.4&sdp_ratio=0

headers = {
    "authority": "v2.genshinvoice.top",
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "content-type": "application/json",
    "cookie": "_ga_R1FN4KJKJH=GS1.1.1715348492.9.0.1715348492.0.0.0; _ga=GA1.2.245707418.1703683960; _gid=GA1.2.1196486009.1715348493; _gat_gtag_UA_156449732_1=1",
    "origin": "https://v2.genshinvoice.top",
    "referer": "https://v2.genshinvoice.top/",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Encoding": "deflate, gzip"
}

headers_new = {
    ":authority": "v2.genshinvoice.top", 
    ":method": "POST",
    ":path": "/v1/tts",
    ":scheme": "https",
    "accept": "*/*",
"accept-encoding":"gzip, deflate, br, zstd",
"accept-language":"en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
"cache-control": "no-cache",
# content-length:194
"content-type": "application/msgpack",
"origin": "https://v2.genshinvoice.top",
"pragma": "no-cache",
"priority":"u=1, i",
"referer": "https://v2.genshinvoice.top/",
"sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
"sec-ch-ua-mobile": "?0",
"sec-ch-ua-platform":'"Windows"',
"sec-fetch-dest":"empty",
"sec-fetch-mode":"cors",
"sec-fetch-site":"same-origin",
"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}

file_url = "https://v2.genshinvoice.top/file="

bert_vits2_voices = [{ "id": "派蒙_ZH", "name": "派蒙_ZH" }, 
                     { "id": "纳西妲_ZH", "name": "纳西妲_ZH"}, 
                     { "id": "凯亚_ZH", "name": "凯亚_ZH"}, 
                     { "id": "阿贝多_ZH", "name": "阿贝多_ZH" }, 
                     { "id": "温迪_ZH", "name": "温迪_ZH" }, 
                     { "id": "枫原万叶_ZH", "name": "枫原万叶_ZH" }, 
                     { "id": "钟离_ZH", "name": "钟离_ZH" }, 
                     { "id": "荒泷一斗_ZH", "name": "荒泷一斗_ZH"}, 
                     { "id": "八重神子_ZH", "name": "八重神子_ZH"}, 
                     { "id": "艾尔海森_ZH", "name": "艾尔海森_ZH"}, 
                     { "id": "提纳里_ZH", "name": "提纳里_ZH"}, 
                     { "id": "迪希雅_ZH", "name": "迪希雅_ZH"}, 
                     { "id": "卡维_ZH", "name": "卡维_ZH"}, 
                     { "id": "宵宫_ZH", "name": "宵宫_ZH"}, 
                     { "id": "那维莱特_ZH", "name": "那维莱特_ZH"}, 
                     { "id": "莱依拉_ZH", "name": "莱依拉_ZH"}, 
                     { "id": "赛诺_ZH", "name": "赛诺_ZH"}, 
                     { "id": "莫娜_ZH",    "name": "莫娜_ZH"}, 
                     { "id": "诺艾尔_ZH",    "name": "诺艾尔_ZH"}, 
                     { "id": "托马_ZH",    "name": "托马_ZH"},
                     {    "id": "凝光_ZH",    "name": "凝光_ZH"}, 
                     {    "id": "林尼_ZH", "name": "林尼_ZH"}, 
                     {    "id": "北斗_ZH", "name": "北斗_ZH"}, 
                     {    "id": "柯莱_ZH", "name": "柯莱_ZH"}, 
                     {    "id": "神里绫华_ZH", "name": "神里绫华_ZH"}, 
                     {    "id": "可莉_ZH", "name": "可莉_ZH"}, 
                     {    "id": "克列门特_ZH", "name": "克列门特_ZH"}, 
                     {    "id": "大慈树王_ZH", "name": "大慈树王_ZH"}, 
                     {    "id": "西拉杰_ZH", "name": "西拉杰_ZH"}, 
                     {    "id": "上杉_ZH", "name": "上杉_ZH"}, 
                     {    "id": "阿尔卡米_ZH", "name": "阿尔卡米_ZH"}, 
                     {    "id": "纯水精灵_ZH", "name": "纯水精灵_ZH"}, 
                     {    "id": "常九爷_ZH", "name": "常九爷_ZH"}, 
                     {    "id": "沙扎曼_ZH", "name": "沙扎曼_ZH"}, 
                     {    "id": "田铁嘴_ZH", "name": "田铁嘴_ZH"}, 
                     {    "id": "克罗索_ZH", "name": "克罗索_ZH"}, 
                     {    "id": "阿巴图伊_ZH", "name": "阿巴图伊_ZH"}, 
                     {    "id": "阿佩普_ZH", "name": "阿佩普_ZH"}, 
                     {    "id": "埃尔欣根_ZH", "name": "埃尔欣根_ZH"}, 
                     {    "id": "萨赫哈蒂_ZH", "name": "萨赫哈蒂_ZH"}, 
                     {    "id": "塔杰·拉德卡尼_ZH", "name": "塔杰·拉德卡尼_ZH"}, 
                     {    "id": "安西_ZH", "name": "安西_ZH"}, 
                     {    "id": "陆行岩本真蕈·元素生命_ZH", "name": "陆行岩本真蕈·元素生命_ZH"}
                    ]
        

class BertVits2API():
    def __init__(self):
        pass

    def request(self, req_params:dict[str,any]) -> str:
        logger.debug(f"params2={req_params}")
        # 合成语音
        body = json.dumps(req_params, ensure_ascii=False).encode('utf-8')
        logger.debug(f"body={body}")
        response = requests.post(url, headers=headers, data=body, verify=False)

        logger.debug("=======================================")
        logger.debug(f"response={response.text}")
        logger.debug("=======================================")

        # voice_result = json.loads(response.text)["data"]
        # file_path = voice_result[1]["name"]

        # logger.debug(f"body={body}, response={response}, file_path={file_path}, url={file_url + file_path}")

        # # 下载文件
        # response = requests.get(file_url + file_path, headers=headers, verify=False)

        # 初始化文件夹
        file_name = new_uuid() + ".wav"
        # file_path = os.getcwd() + "/tmp/" + file_name
        # dirPath = os.path.dirname(file_path)
        # if not os.path.exists(dirPath):
        #     os.makedirs(dirPath)
        # if not os.path.exists(file_path):
        #     # 用open创建文件 兼容mac
        #     open(file_path, 'a').close()

        # # 写入语音文件
        # with open(file_path, 'wb') as file:
        #     file.write(response.content)

        return file_name

    def do_synthesis(self, text: str, speaker: str, noise: str, noisew: str, sdp_ratio: str) -> str:
        params = {
            "data": [text, speaker, sdp_ratio, noise, noisew, 1, "ZH", False, 1, 0.2, None, "Happy", "", 0.7],
            "event_data": None,
            "fn_index": 0,
            "session_hash": str(uuid.uuid4())
        }
        logger.debug(f"params={params}")
        # 将所有非字符串数据转换为字符串，以匹配API的要求（如果API确实有这个要求）  
        # 注意：这里假设API可以接受所有值为字符串的字典，实际情况可能需要根据API的具体要求调整  
        params_str_values = {k: str(v) if isinstance(v, (int, float, bool)) else v for k, v in params.items()}  
        if isinstance(params_str_values["data"], list):  
            params_str_values["data"] = [str(item) if isinstance(item, (int, float, bool)) else item for item in params_str_values["data"]]  
        logger.debug(f"params={params_str_values}")  
        return self.request(req_params=params_str_values)  

    def do_synthesis_test(self, text: str, speaker: str, noise: str, noisew: str, sdp_ratio: str) -> str:
        params = {
            "data": [text, speaker, sdp_ratio, noise, noisew, 1, "ZH", False, 1, 0.2, None, "Happy", "", 0.7],
            "event_data": None,
            "fn_index": 0,
            "session_hash": str(uuid.uuid4())
        }
        logger.debug(f"params={params}")
        return self.request(req_params=params)

    async def get_voices(self) -> list:
        return bert_vits2_voices

    async def generate_tts_file(self, text: str, speaker: str, noise: str, noisew: str, sdp_ratio: str) -> str:
        return self.do_synthesis(text, speaker, noise, noisew, sdp_ratio)

    async def generate_tts_bytes(self, text: str, speaker: str, noise: str, noisew: str, sdp_ratio: str) -> bytes:
        return self.do_synthesis(text, speaker, noise, noisew, sdp_ratio)

    async def generate_tts_stream(self, text: str, speaker: str, noise: str, noisew: str, sdp_ratio: str) -> bytes:
        audio_path = self.do_synthesis(text, speaker, noise, noisew, sdp_ratio)
        logger.debug(f"audio_path={audio_path}")
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        return audio_data

if __name__ == '__main__':
    client = BertVits2API()
    client.do_synthesis(text="晚上好", speaker="流萤_ZH", noise=0.6, noisew=0.9, sdp_ratio=0.5)
