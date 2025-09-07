# OddTTS - 多引擎语音合成服务

OddTTS 是一个功能强大的多引擎语音合成服务，提供统一的API接口和友好的Web界面，支持多种主流TTS引擎，包括EdgeTTS、ChatTTS、Bert-VITS2等。

## 功能特点

- **多引擎支持**：集成了EdgeTTS、ChatTTS、Bert-VITS2、Bert-VITS2 V2、OddGptSovits等多种TTS引擎
- **多种调用方式**：支持文件路径返回、Base64编码返回、流式响应等多种输出方式
- **友好的Web界面**：基于Gradio提供可视化操作界面
- **RESTful API**：提供完整的REST API，便于集成到其他系统
- **可配置性强**：支持GPU加速、并发线程数调整、模型预加载等配置选项
- **跨平台兼容**：基于Python开发，支持Windows、Linux、macOS等多种操作系统

## 技术栈

- **Web框架**：FastAPI
- **Web界面**：Gradio
- **ASGI服务器**：Uvicorn
- **数据库**：SQLite（默认）
- **缓存**：Redis（可选）
- **异步支持**：Python asyncio

## 安装指南

### 环境要求
- Python 3.8+ 
- 依赖库：fastapi, gradio, uvicorn, requests等

### 安装步骤

1. 克隆项目代码
```bash
git clone https://github.com/yourusername/oddtts.git
cd oddtts
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

3. 配置项目参数（修改 oddtts_config.py）
```python
# 服务器配置
HOST = \"127.0.0.1\"
PORT = 9001
Debug = False

# TTS配置
oddtts_cfg = {
    \"preload_model\": True,
    \"enable_gpu\": False,
    \"disable_stream\": False,
    \"concurrent_thread\": 0,
    \"tts_type\": ODDTTS_TYPE.ODDTTS_EDGETTS,
    \"enable_https\": False,
    # ...
}
```

4. 启动服务
```bash
python oddtts.py
```

## 项目结构

```
oddtts/
├── base_tts_driver.py    # 基础TTS驱动抽象类及实现
├── oddtts.py             # 主程序入口，包含API和Web界面
├── oddtts_config.py      # 配置文件
├── oddtts_params.py      # 参数定义和枚举类型
├── tts_bert_vits2.py     # Bert-VITS2引擎实现
├── tts_bert_vits2_v2.py  # Bert-VITS2 V2引擎实现
├── tts_chattts.py        # ChatTTS引擎实现
├── tts_edge.py           # EdgeTTS引擎实现
├── tts_odd_gptsovits.py  # OddGptSovits引擎实现
└── test.py               # API测试脚本
```

## API接口文档

### 1. 健康检查
```
GET /oddtts/health
```
- **功能**：检查服务是否正常运行
- **返回**：`{\"status\": \"healthy\", \"message\": \"API服务运行正常\"}`

### 2. 获取语音列表
```
GET /api/oddtts/voices
```
- **功能**：获取当前TTS引擎支持的所有语音
- **返回**：语音列表，每个语音包含名称、语言、性别等信息

### 3. 获取特定语音详情
```
GET /api/oddtts/voices/{voice_name}
```
- **功能**：获取指定语音的详细信息
- **参数**：`voice_name` - 语音名称
- **返回**：语音详细信息

### 4. 生成TTS音频（返回文件路径）
```
POST /api/oddtts/file
```
- **功能**：生成TTS音频并返回文件路径
- **请求体**：
  ```json
  {
    \"text\": \"要转换为语音的文本\",
    \"voice\": \"语音名称\",
    \"rate\": 语速调整(-50到50),
    \"volume\": 音量调整(-50到50),
    \"pitch\": 音调调整(-50到50)
  }
  ```
- **返回**：`{\"status\": \"success\", \"file_path\": \"音频文件路径\", \"format\": \"mp3\"}`

### 5. 生成TTS音频（返回Base64）
```
POST /api/oddtts/base64
```
- **功能**：生成TTS音频并返回Base64编码
- **请求体**：同文件路径API
- **返回**：`{\"status\": \"success\", \"base64\": \"Base64编码的音频数据\", \"format\": \"mp3\"}`

### 6. 生成TTS音频（流式响应）
```
POST /api/oddtts/stream
```
- **功能**：生成TTS音频并以流式响应返回
- **请求体**：同文件路径API
- **返回**：流式音频数据（audio/mpeg格式）

## Web界面使用

服务启动后，可以通过浏览器访问 `http://localhost:9001/` 打开Gradio Web界面，支持以下功能：

- 文本输入区域：输入要转换为语音的文本
- 语音选择：选择不同的语音和语言
- 参数调整：调整语速、音量、音调等参数
- 音频生成：点击按钮生成并播放语音
- 音频下载：下载生成的语音文件

## 配置说明

主要配置项位于 `oddtts_config.py` 文件中：

- **服务器设置**：HOST、PORT、Debug模式
- **TTS引擎设置**：
  - `preload_model`: 是否在启动时预加载模型
  - `enable_gpu`: 是否启用GPU加速
  - `disable_stream`: 是否禁用流式TTS
  - `concurrent_thread`: 并发线程数，0表示自动检测CPU核心数
  - `tts_type`: TTS引擎类型，可选择EdgeTTS、ChatTTS等
- **HTTPS配置**：enable_https、ssl_cert_path、ssl_key_path
- **数据库配置**：db_engine、db_name等
- **Redis配置**：redis_enabled、redis_host等
- **日志配置**：log_file、log_path、log_level

## 支持的TTS引擎

OddTTS支持以下TTS引擎，可以通过 `tts_type` 配置项选择：

| 引擎类型 | 枚举值 | 说明 |
|---------|--------|------|
| EdgeTTS | ODDTTS_TYPE.ODDTTS_EDGETTS | 微软Edge浏览器的TTS引擎，支持多种语言和语音 |
| ChatTTS | ODDTTS_TYPE.ODDTTS_CHATTTS | 基于最新研究的对话式TTS引擎 |
| Bert-VITS2 | ODDTTS_TYPE.ODDTTS_BERTVITS2 | 基于BERT和VITS2的开源TTS引擎 |
| Bert-VITS2 V2 | ODDTTS_TYPE.ODDTTS_BERTVITS2_V2 | Bert-VITS2的改进版本 |
| OddGptSovits | ODDTTS_TYPE.ODDTTS_GPTSOVITS | 基于GPT和Sovits的TTS引擎 |

## 使用示例

项目提供了 `test.py` 文件作为API调用的示例：

```python
import requests
import oddtts_config as config

# 配置API基础URL
API_BASE_URL = \"http://\" + config.HOST + \":\" + str(config.PORT)

# 测试文本
TEST_TEXT = \"Hello! 这是一个API测试。This is an API test.\"

# 获取语音列表
def test_api_voices():
    response = requests.get(f\"{API_BASE_URL}/api/oddtts/voices\")
    voices = response.json()
    print(f\"成功获取 {len(voices)} 个语音选项\")
    return voices

# 测试生成TTS音频
def test_api_tts_file(voice_name):
    payload = {
        \"text\": TEST_TEXT,
        \"voice\": voice_name,
        \"rate\": 0,
        \"volume\": 0,
        \"pitch\": 0
    }
    response = requests.post(f\"{API_BASE_URL}/api/oddtts/file\", json=payload)
    result = response.json()
    print(f\"音频文件路径: {result.get('file_path')}\")
```

## 常见问题

1. **服务启动失败**
   - 检查端口是否被占用
   - 确认所有依赖包已正确安装
   - 查看日志文件获取详细错误信息

2. **语音合成失败**
   - 检查TTS引擎配置是否正确
   - 确认选择的语音存在于当前TTS引擎中
   - 对于某些需要联网的引擎，确认网络连接正常

3. **如何切换TTS引擎**
   - 修改 `oddtts_config.py` 文件中的 `tts_type` 配置项
   - 重启服务使配置生效

## 贡献指南

欢迎提交问题和改进建议！如果您想为项目贡献代码，请遵循以下步骤：

1. Fork 项目仓库
2. 创建功能分支
3. 提交代码更改
4. 推送到远程分支
5. 创建 Pull Request

## License

[MIT License](LICENSE)"},"render":null,"is_truncated":null}}}}]
