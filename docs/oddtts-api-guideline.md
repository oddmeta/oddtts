# OddTTS API 接口文档

OddTTS 提供高质量的文本转语音（Text-to-Speech）服务，完全兼容 OpenAI Audio API 标准。支持多种 TTS 引擎，包括 OddGPT-SoVITS、EdgeTTS、ChatTTS、Bert-VITS2、Kokoro、Kokorov1.1(支持中英混合) 等。

## 1. 系统管理 API

### 1.1 健康检查

检查 API 服务是否正常运行。

- 端点: GET `/oddtts/health`
- Content-Type: application/json

#### 1.1.1 响应示例

```json
{
  "status": "healthy",
  "message": "API服务运行正常"
}
```

## 2. 语音列表 API

### 2.1 获取语音列表

获取当前 TTS 引擎支持的所有语音列表。

- 端点: GET `/v1/audio/voice/list`
- Content-Type: application/json

#### 2.1.1 响应示例

```json
[
  {
    "name": "xiaoyan",
    "short_name": "xiaoyan",
    "description": "小燕 - 女性声音",
    "locale": "zh-CN"
  },
  {
    "name": "xiaoxiao",
    "short_name": "xiaoxiao",
    "description": "晓晓 - 女性声音",
    "locale": "zh-CN"
  }
]
```

### 2.2 获取语音详情

获取指定语音的详细信息。

- 端点: GET `/v1/audio/voice/list/<voice_name>`
- Content-Type: application/json

#### 2.2.1 请求参数

|参数名|类型|必填|说明|
|--|--|--|--|
|voice_name | String	| 是 | 语音的 short_name |

#### 2.2.2 响应示例

```json
{
  "name": "xiaoyan",
  "short_name": "xiaoyan",
  "description": "小燕 - 女性声音",
  "locale": "zh-CN"
}
```

#### 2.2.3 错误响应

```json
{
  "error": "Voice 'unknown_voice' not found"
}
```

## 3. TTS 生成 API（原生）

### 3.1 TTS 生成 - 返回文件路径

将文本转换为音频文件，返回文件路径。

- 端点: POST `/api/oddtts/file`
- Content-Type: application/json

#### 3.1.1 请求参数

|参数名|类型|必填|默认值|说明|
|--|--|--|--|--|
|text | String	| 是 | -	| 要合成的文本内容|
|voice | String	| 是 | -	| 音色 ID，从语音列表获取|
|rate | Integer	| 否 | 0	| 语速调整，负数减速，正数加速|
|volume | Integer	| 否 | 0	| 音量调整，负数减小，正数增大|
|pitch | Integer	| 否 | 0	| 音调调整，负数降低，正数升高|
|locale | String	| 否 | zh-CN	| 语言区域|
|response_format | String	| 否 | wav	| 输出音频格式，支持 wav, mp3 等|

#### 3.1.2 请求示例 (cURL)

```bash
curl http://localhost:8000/api/oddtts/file \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是 OddTTS 生成的语音。",
    "voice": "xiaoyan",
    "rate": 0,
    "volume": 0,
    "pitch": 0,
    "locale": "zh-CN",
    "response_format": "wav"
  }'
```

#### 3.1.3 响应示例

```json
{
  "status": "success",
  "file_path": "/tmp/abc123def456.wav",
  "format": "wav"
}
```

### 3.2 TTS 生成 - 返回 Base64

将文本转换为音频，返回 Base64 编码的音频数据。

- 端点: POST `/api/oddtts/base64`
- Content-Type: application/json

#### 3.2.1 请求参数

参数同 3.1.1

#### 3.2.2 响应示例

```json
{
  "status": "success",
  "base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=",
  "format": "wav"
}
```

### 3.3 TTS 生成 - 流式响应

将文本转换为音频，以流式方式返回音频数据。

- 端点: POST `/api/oddtts/stream`
- Content-Type: application/json

#### 3.3.1 请求参数

参数同 3.1.1

#### 3.3.2 请求示例 (cURL)

```bash
curl http://localhost:8000/api/oddtts/stream \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是 OddTTS 生成的语音。",
    "voice": "xiaoyan",
    "response_format": "mp3"
  }' \
  --output speech.mp3
```

#### 3.3.3 响应

成功: 直接返回音频二进制流（Binary Stream）。
失败: 返回 JSON 格式的错误信息。

## 4. 音频文件操作 API

### 4.1 播放音频文件

在浏览器中播放指定的音频文件。

- 端点: GET `/play`

#### 4.1.1 请求参数

|参数名|类型|必填|说明|
|--|--|--|--|
|path | String	| 是 | 音频文件的绝对路径（需 URL 编码）|

#### 4.1.2 请求示例

```bash
curl "http://localhost:8000/play?path=%2Ftmp%2Fabc123def456.wav"
```

### 4.2 下载音频文件

下载指定的音频文件。

- 端点: GET `/download`

#### 4.2.1 请求参数

参数同 4.1.1

#### 4.2.2 请求示例

```bash
curl "http://localhost:8000/download?path=%2Ftmp%2Fabc123def456.wav" -o audio.mp3
```

## 5. OpenAI 兼容 API

### 5.1 获取模型列表

获取可用的 TTS 模型列表。

- 端点: GET `/v1/models`
- Content-Type: application/json

#### 5.1.1 响应示例

```json
{
  "object": "list",
  "data": [
    {
      "id": "oddtts-ODDTTS_EDGETTS",
      "object": "model",
      "created": 1700000000,
      "owned_by": "oddtts",
      "permission": [],
      "root": "ODDTTS_EDGETTS",
      "parent": null
    }
  ],
  "model": "ODDTTS_EDGETTS"
}
```

### 5.2 创建语音合成 (Create Speech)

OpenAI 兼容的语音合成接口。

- 端点: POST `/v1/audio/speech`
- Content-Type: application/json

#### 5.2.1 请求参数

|参数名|类型|必填|默认值|说明|
|--|--|--|--|--|
|input | String	| 是 | -	| 要合成的文本内容|
|voice | String	| 是 | -	| 音色 ID，从语音列表获取|
|speed | Float	| 否 | 1.0	| 语速，范围 0.25 - 4.0|
|response_format | String	| 否 | mp3	| 输出音频格式，支持 mp3, wav 等|
|locale | String	| 否 | zh-CN	| 语言区域|

#### 5.2.2 请求示例 (cURL)

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "你好，这是 OddTTS 生成的语音。",
    "voice": "xiaoyan",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

Python 调用示例

```python
from pathlib import Path
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # 本地部署无需真实 Key
)

speech_file_path = Path(__file__).parent / "speech.mp3"

response = client.audio.speech.create(
    model="oddtts-ODDTTS_EDGETTS",
    voice="xiaoyan",
    input="你好，欢迎使用小奥语音合成服务。"
)

response.stream_to_file(speech_file_path)
print(f"Audio saved to {speech_file_path}")
```

#### 5.2.3 响应

成功: 直接返回音频二进制流（Binary Stream）。
失败: 返回 JSON 格式的错误信息。

## 6. 配置管理 API

### 6.1 获取 TTS 类型列表

获取所有支持的 TTS 引擎类型及当前配置。

- 端点: GET `/api/config/tts-types`
- Content-Type: application/json

#### 6.1.1 响应示例

```json
{
  "types": [
    {
      "value": 1,
      "name": "ODDTTS_GPTSOVITS",
      "description": "OddGPT-SoVITS - 基于GPT-SoVITS的语音合成引擎（需8G以上GPU）",
      "enable": true
    },
    {
      "value": 2,
      "name": "ODDTTS_EDGETTS",
      "description": "EdgeTTS - 微软Edge浏览器的在线TTS服务(无需GPU)",
      "enable": true
    },
    {
      "value": 3,
      "name": "ODDTTS_CHATTTS",
      "description": "ChatTTS - 专为对话场景设计的TTS引擎（需4G以上GPU）",
      "enable": true
    },
    {
      "value": 4,
      "name": "ODDTTS_BERTVITS2",
      "description": "Bert-VITS2 - 基于BERT和VITS的语音合成（需4G以上GPU）",
      "enable": true
    },
    {
      "value": 5,
      "name": "ODDTTS_BERTVITS2_V2",
      "description": "Bert-VITS2 V2 - Bert-VITS2的升级版本（需4G以上GPU）",
      "enable": true
    },
    {
      "value": 6,
      "name": "ODDTTS_KOKORO",
      "description": "Kokoro - 轻量级多语言TTS引擎（纯CPU，中文）",
      "enable": true
    },
    {
      "value": 7,
      "name": "ODDTTS_KOKORO_V1_1",
      "description": "Kokoro V1.1 - Kokoro引擎的1.1版本（纯CPU，中英混合）",
      "enable": true
    }
  ],
  "current": {
    "value": 2,
    "name": "ODDTTS_EDGETTS",
    "description": "EdgeTTS - 微软Edge浏览器的在线TTS服务(无需GPU)",
    "enable": true
  }
}
```

### 6.2 保存配置

更新 TTS 引擎配置并自动生效。

- 端点: POST `/api/config/save`
- Content-Type: application/json

#### 6.2.1 请求参数

|参数名|类型|必填|说明|
|--|--|--|--|
|tts_type | Integer	| 是 | TTS 类型的值，参考 6.1 中的 value|

#### 6.2.2 请求示例

```bash
curl http://localhost:8000/api/config/save \
  -H "Content-Type: application/json" \
  -d '{
    "tts_type": 2
  }'
```

#### 6.2.3 响应示例

```json
{
  "success": true,
  "message": "配置已保存并已自动生效"
}
```

## 7. 注意事项

- API Key:

  - 本地部署时，api_key 字段可填写任意字符串（如 "dummy" 或 "sk-xxx"），服务端通常不进行严格鉴权，但建议在生产环境中配置密钥。

- 音频格式:

  - 支持 wav, mp3, ogg, flac 等多种输出格式。
  - 默认格式：OpenAI API 为 mp3，原生 API 为 wav。

- 文本长度限制:

  - 单次请求的 text 文本长度建议控制在合理范围内（如 4096 字符以内），过长文本建议分段合成。

- 并发与性能:

  - 响应速度取决于服务器 GPU/CPU 性能。
  - 高并发场景下建议启用队列机制或使用异步客户端。

- TTS 引擎选择:

  - EdgeTTS: 无需 GPU，适合快速测试和轻量级应用。
  - OddGPT-SoVITS: 需 8G 以上 GPU，音质最佳。
  - ChatTTS: 需 4G 以上 GPU，专为对话场景优化。
  - Bert-VITS2: 需 4G 以上 GPU，支持多语言。
  - Kokoro: 纯 CPU 运行，适合资源受限环境。
  - Kokoro V1.1: Kokoro 的 1.1 版本，支持中英混合。

- 与 OpenAI 的差异:

  - 模型 ID: 使用项目定义的模型 ID（如 oddtts-ODDTTS_EDGETTS）而非 OpenAI 的 tts-1。
  - 音色支持: 支持的 voice 列表取决于当前选择的 TTS 引擎。
  - 参数调整: 原生 API 支持 rate、volume、pitch 三维参数调整，OpenAI API 仅支持 speed 参数。

## 8. 错误码说明

遵循 HTTP 标准状态码及 OpenAI 错误格式：

```json
{
  "error": {
    "message": "Invalid value for 'voice': 'unknown_voice'. Supported voices: ['xiaoyan', 'xiaoxiao']",
    "type": "invalid_request_error",
    "param": "voice",
    "code": "invalid_value"
  }
}
```

| 错误状态码 | 含义 | 常见原因 |
| 400 | Bad Request | 参数缺失、格式错误、不支持的音色 |
| 401 | Unauthorized | API Key 无效（若启用了鉴权）|
| 404 | Not Found | 语音不存在、文件不存在 |
| 429 | Too Many Requests | 超过速率限制 |
| 500 | Internal Server Error | 服务端推理失败、显存溢出 |
| 503 | Service Unavailable | 服务端异常 |