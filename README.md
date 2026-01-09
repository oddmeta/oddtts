**Read this in other languages: [English](README.md), [中文](README.chs.md).**

[TOC]

# OddTTS - Multi-Engine TTS Voice Synthesis API Wrapper

OddTTS is a powerful multi-engine text-to-speech service that provides a unified API interface and user-friendly web interface, allowing you to access multiple mainstream TTS engines (including EdgeTTS, ChatTTS, Bert-VITS2, GptSovits, etc.) with a single set of interfaces.

## I. Preface

### 1. About OddTTS

I needed TTS functionality for my project **[XiaoLuo Tongxue](https://x.oddmeta.net "XiaoLuo Tongxue")** (Little Luo Classmate). Due to hardware constraints (an Alibaba Cloud ECS server costing 99 yuan/year), I initially could only use EdgeTTS. However, my personal computer has better specifications, so I tried multiple different TTS engines. I needed to create a unified wrapper for these TTS models so that XiaoLuo Tongxue could switch between different TTS engines at any time - thus OddTTS was born.

Considering the wide range of applications for TTS functionality, I separated it into an independent project and open-sourced it. I hope it helps students with TTS needs.

<font color=red>**Note: If you want to use TTS engines other than EdgeTTS, you need to install the corresponding TTS engines yourself before installing and using OddTTS.**</font>

### 2. Why Choose OddTTS?

- **Multi-engine support**: Integrates EdgeTTS, ChatTTS, Bert-VITS2, OddGptSovits, and other TTS engines
- **Multiple calling methods**: Supports file path return, Base64 encoding return, streaming response, and other output methods
- **User-friendly web interface**: Provides a visual operation interface based on Gradio
- **RESTful API**: Offers a complete REST API for easy integration into other systems
- **Strong configurability**: Supports GPU acceleration, concurrent thread adjustment, model preloading, and other configuration options
- **Cross-platform compatibility**: Developed based on Python, supporting Windows, Linux, macOS, and other operating systems

### 3. Recommended Hardware

| Model Name | Original Minimum VRAM | Original Smooth VRAM | Original Full VRAM | INT8 Quantized Minimum VRAM | INT4 Quantized Minimum VRAM | Can Run on Pure CPU | CPU Running Speed |
|------------|----------|---------|-------|--------|-------|--------------------|------------------|
| EdgeTTS    | 0GB      | 0GB     | 0GB   | 0GB    | 0GB   | ✅ Yes             | Depends on your network speed |
| ChatTTS    | 2.5GB    | 4GB     | 6GB+  | 1.5GB  | 1GB   | ✅ Yes             | Fast             |
| Bert-VITS2 | 5GB      | 6GB     | 8GB+  | 3GB    | 2GB   | ✅ Yes             | Moderate         |
| GPT-SoVITS v2 | 8GB   | 10GB    | 12GB+ | 4GB    | 2.5GB | ❌ Not recommended | Slow             |

> XiaoLuo Tongxue uses an Alibaba Cloud ECS server costing 99 yuan/year with only 2 cores and 2GB of memory, which can't run any TTS models, so it uses EdgeTTS.

## II. Quick Start

### 1. Install OddTTS

```bash
pip install -i https://pypi.org/simple/ oddtts
```

### 2. Start OddTTS

#### 1. Default Configuration

Simply execute the following command in the installed virtual environment to start:

```bash
oddtts
```

After starting, OddTTS will bind to 127.0.0.1 (local access only) on port 9001 by default. Access it through your browser at: http://localhost:9001

#### 2. Custom Configuration

To allow access from other IPs, use the following command to start the service, setting host to 0.0.0.0, and you can also change the port to a custom port.

```bash
oddtts --host 0.0.0.0 --port 8080
```

## III. OddTTS API Documentation

### 1. API Interface List
#### 1) Health Check
```
GET /oddtts/health
```
- **Function**: Check if the service is running normally
- **Return**: `{\"status\": \"healthy\", \"message\": \"API service is running normally\"}`

#### 2) Get Voice List
```
GET /api/oddtts/voices
```
- **Function**: Get all voices supported by the current TTS engine
- **Return**: Voice list, each voice contains name, language, gender, etc.

#### 3) Get Specific Voice Details
```
GET /api/oddtts/voices/{voice_name}
```
- **Function**: Get detailed information about a specific voice
- **Parameter**: `voice_name` - Voice name
- **Return**: Detailed voice information

#### 4) Generate TTS Audio (Return File Path)
```
POST /api/oddtts/file
```
- **Function**: Generate TTS audio and return the file path
- **Request Body**:
  ```json
  {
    \"text\": \"Text to be converted to speech\",
    \"voice\": \"Voice name\",
    \"rate\": Speed adjustment (-50 to 50),
    \"volume\": Volume adjustment (-50 to 50),
    \"pitch\": Pitch adjustment (-50 to 50)
  }
  ```
- **Return**: `{\"status\": \"success\", \"file_path\": \"Audio file path\", \"format\": \"mp3\"}`

#### 5) Generate TTS Audio (Return Base64)
```
POST /api/oddtts/base64
```
- **Function**: Generate TTS audio and return Base64 encoding
- **Request Body**: Same as the file path API
- **Return**: `{\"status\": \"success\", \"base64\": \"Base64 encoded audio data\", \"format\": \"mp3\"}`

#### 6) Generate TTS Audio (Streaming Response)
```
POST /api/oddtts/stream
```
- **Function**: Generate TTS audio and return it as a streaming response
- **Request Body**: Same as the file path API
- **Return**: Streaming audio data (audio/mpeg format)

### 2. API Call Example

Here's an example of calling the OddTTS API:

```python
import requests

# Configure API base URL
API_BASE_URL = "http://localhost:9001"

# Test text
TEST_TEXT = \"Hello! This is an API test. 这是一个API测试。\"

# Get voice list
def test_api_voices():
    response = requests.get(f\"{API_BASE_URL}/api/oddtts/voices\")
    voices = response.json()
    print(f\"Successfully obtained {len(voices)} voice options\")
    return voices

# Test generating TTS audio
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
    print(f\"Audio file path: {result.get('file_path')}\")
```

## IV. Web Interface Usage

After starting the service, you can access `http://localhost:9001/` through your browser to open the Gradio Web interface, which supports the following functions:

- Text input area: Enter text to be converted to speech
- Voice selection: Choose different voices and languages
- Parameter adjustment: Adjust speed, volume, pitch, and other parameters
- Audio generation: Click the button to generate and play speech
- Audio download: Download the generated speech file

## V. Common Issues

1. **Service startup failure**
   - Check if the port is occupied
   - Confirm all dependency packages are correctly installed
   - View the log file for detailed error information

2. **Speech synthesis failure**
   - Check if the TTS engine configuration is correct
   - Confirm that the selected voice exists in the current TTS engine
   - For engines that require internet access, confirm that the network connection is normal

3. **How to switch TTS engines**
   - Modify the `tts_type` configuration item in the `oddtts_config.py` file
   - Restart the service for the configuration to take effect

## VI. License

The OddTTS project has no license.
Feel free to copy without any conditions! Just code happily! Contributions and improvement suggestions are also welcome!
