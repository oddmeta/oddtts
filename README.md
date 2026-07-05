**Read this in other languages: [English](README.md), [中文](README.chs.md).**

[TOC]

# OddTTS - Multi-Engine TTS Voice Synthesis API Wrapper (with OpenAI TTS API compatibility)

OddTTS is a powerful multi-engine text-to-speech service that provides a unified API interface and user-friendly web interface, allowing you to access multiple mainstream TTS engines (including EdgeTTS, Kokoro-82M-v1.1-zh, ChatTTS, Bert-VITS2, GptSovits v2, etc.) with a single set of interfaces, and also with OpenAI TTS API compatibility.

> Notes:
> - Model files will be downloaded automatically on first run.
> - Model file sizes:
>   - Kokoro-82M-v1.1-zh model: ~376MB.
>   - EdgeTTS model: 0MB, no model download required.
>   - ChatTTS model: 2.4GB (FP16 precision).
>   - Bert-VITS2 model: ~2GB (backbone + BERT feature network, each additional language adds ~1.3GB).
>   - GptSovits v2 model: ~2.5GB.
> - VRAM requirements:
>   - EdgeTTS model: 0MB.
>   - Kokoro-82M-v1.1-zh model: 0MB (runs on regular CPU).
>   - ChatTTS model: at least 2.5GB.
>   - Bert-VITS2 model: at least 5GB. For few-shot fine-tuning, GPU with 24GB+ VRAM is recommended.
>   - GptSovits v2 model: at least 8GB. For few-shot fine-tuning, GPU with 24GB/48GB+ VRAM is recommended.
> - Users in China are recommended to use mirror for faster downloads.
>   - Windows: set HF_ENDPOINT=https://hf-mirror.com
>   - Linux/MacOS: export HF_ENDPOINT=https://hf-mirror.com
> - Model files are large, recommend running in an environment with sufficient disk space, or customize model path.
>   - Windows: set HF_HOME=x:/models/hf_home
>   - Linux/MacOS: export HF_HOME=/models/hf_home

## I. Preface

### 1. About OddTTS

I needed TTS functionality for my project **[XiaoLuo Tongxue](https://x.oddmeta.net "XiaoLuo Tongxue")** (Little Luo Classmate). Due to hardware constraints (an Alibaba Cloud ECS server costing 99 yuan/year), I initially could only use EdgeTTS. However, my personal computer has better specifications, so I tried multiple different TTS engines. I needed to create a unified wrapper for these TTS models so that XiaoLuo Tongxue could switch between different TTS engines at any time - thus OddTTS was born.

Considering the wide range of applications for TTS functionality, I separated it into an independent project and open-sourced it. I hope it helps students with TTS needs.

<font color=red>**Note: If you want to use TTS engines other than EdgeTTS, you need to install the corresponding TTS engines yourself before installing and using OddTTS.**</font>

### 2. Why Choose OddTTS?

- **Multi-engine support**: Integrates EdgeTTS, Kokoro, ChatTTS, Bert-VITS2, OddGptSovits, and other TTS engines
- **Multiple calling methods**: Supports file path return, Base64 encoding return, streaming response, and other output methods
- **User-friendly web interface**: Provides a visual operation interface based on Gradio
- **RESTful API**: Offers a complete REST API for easy integration into other systems
- **Strong configurability**: Supports GPU acceleration, concurrent thread adjustment, model preloading, and other configuration options
- **Cross-platform compatibility**: Developed based on Python, supporting Windows, Linux, macOS, and other operating systems

### 3. Recommended Hardware

| Model Name | Original Minimum VRAM | Original Smooth VRAM | Original Full VRAM | INT8 Quantized Minimum VRAM | INT4 Quantized Minimum VRAM | Can Run on Pure CPU | CPU Running Speed |
|------------|----------|---------|-------|--------|-------|--------------------|------------------|
| EdgeTTS    | 0GB      | 0GB     | 0GB   | 0GB    | 0GB   | ✅ Yes             | Depends on your network speed |
| Kokoro     | 0GB      | 0GB     | 0GB   | 0GB    | 0GB   | ✅ Yes             | High             |
| ChatTTS    | 2.5GB    | 4GB     | 6GB+  | 1.5GB  | 1GB   | ✅ Yes             | Fast             |
| Bert-VITS2 | 5GB      | 6GB     | 8GB+  | 3GB    | 2GB   | ✅ Yes             | Moderate         |
| GPT-SoVITS v2 | 8GB   | 10GB    | 12GB+ | 4GB    | 2.5GB | ❌ Not recommended | Slow             |

> XiaoLuo Tongxue uses an Alibaba Cloud ECS server costing 99 yuan/year with only 2 cores and 2GB of memory, which can't run any TTS models, so it uses EdgeTTS.
> On my own computer (a 10-year-old laptop), I use the Kokoro-82M-v1.1-zh model, running purely on CPU and offline, with fast performance.

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

#### 1) OpenAI TTS API Compatibility

```
GET /v1/audio/speech
```

- **Function**: OpenAI TTS API compatibility, details see [OpenAI TTS API](https://platform.openai.com/docs/api-reference/audio/create).
- **Return**: mp3 audio data.

#### 2) Get Voice List

```
GET /v1/audio/voice/list
```
- **Function**: Get all voices supported by the current TTS engine
- **Return**: Voice list, each voice contains name, language, gender, etc.

#### 3) Get Specific Voice Details

```
GET /v1/audio/voice/list/{voice_name}
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
    "text": "Text to be converted to speech",
    "voice": "Voice name",
    "rate": Speed adjustment (-50 to 50),
    "volume": Volume adjustment (-50 to 50),
    "pitch": Pitch adjustment (-50 to 50)
  }
  ```
- **Return**: `{"status": "success", "file_path": "Audio file path", "format": "mp3"}`

#### 5) Generate TTS Audio (Return Base64)

```
POST /api/oddtts/base64
```

- **Function**: Generate TTS audio and return Base64 encoding
- **Request Body**: Same as the file path API
- **Return**: `{"status": "success", "base64": "Base64 encoded audio data", "format": "mp3"}`

#### 6) Generate TTS Audio (Streaming Response)

```
POST /api/oddtts/stream
```

- **Function**: Generate TTS audio and return it as a streaming response
- **Request Body**: Same as the file path API
- **Return**: Streaming audio data (audio/mpeg format)

#### 7) Health Check

```
GET /oddtts/health
```

- **Function**: Check if the service is running normally
- **Return**: `{"status": "healthy", "message": "API service is running normally"}`

### 2. API Call Example

Here are some examples of calling the OddTTS API:

> The `voice` parameter needs to be obtained from the backend voice list first, then fill in a voice name supported by the current model (API: `/v1/audio/voice/list`). <font color=red>**Different models have different voice options.**</font>

#### 1) Using curl to Call API

```bash
curl.exe -X POST http://localhost:9001/api/oddtts/file ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Welcome to follow my WeChat official account: OddMeta. Let's learn AI together!\", \"voice\": \"zm_011\", \"rate\": 0, \"volume\": 0, \"pitch\": 0}"
```

#### 2) Using OpenAI Library to Call API

```python
from openai import OpenAI

base_url = "http://localhost:9001/v1"
model = "oddtts-1"
api_key = "dummy"
voice = "zm_011"

text = "Welcome to follow my WeChat official account: OddMeta. Let's learn AI together, and catch up with the times! Good good study, day day up!"

def test_openai_tts_api(voice_id):
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    response = client.audio.speech.create(
        model=model,
        input=text,
        voice=voice_id,
        response_format="mp3"
    )
    response.write_to_file("output.mp3")

if __name__ == "__main__":
    test_openai_tts_api(voice)
```

#### 3) Using requests Library to Call API

```python
import requests

# Configure API base URL
API_BASE_URL = "http://localhost:9001"

# Test text
TEST_TEXT = "Welcome to follow my WeChat official account: OddMeta. Let's learn AI together, and catch up with the times! Good good study, day day up!"

# Get voice list
def test_api_voices():
    response = requests.get(f"{API_BASE_URL}/v1/audio/voice/list")
    voices = response.json()
    print(f"Successfully obtained {len(voices)} voice options")
    return voices

# Test generating TTS audio
def test_api_tts_file(voice_name):
    payload = {
        "text": TEST_TEXT,
        "voice": voice_name,
        "rate": 0,
        "volume": 0,
        "pitch": 0
    }
    response = requests.post(f"{API_BASE_URL}/api/oddtts/file", json=payload)
    result = response.json()
    print(f"Audio file path: {result.get('file_path')}")
```

#### 4) Using JavaScript to Call API

```javascript
async function generateTTS(text, voice) {
    const response = await fetch('http://localhost:9001/api/oddtts/file', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            text: text,
            voice: voice,
            rate: 0,
            volume: 0,
            pitch: 0
        })
    });
    const result = await response.json();
    console.log('Audio file path:', result.file_path);
    return result;
}

generateTTS('Welcome to follow my WeChat official account: OddMeta. Let\'s learn AI together!', 'zm_011');
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

4. **Output format**        
   - Default output format: mp3
   - You can specify other format such as wav, mp3 by setting `response_format` parameter

## VI. License

MIT License - See LICENSE file for details. Commercial, personal, feel free to use.

Contributions and improvement suggestions are also welcome!