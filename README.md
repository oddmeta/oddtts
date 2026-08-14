**Read this in other languages: [English](README.md), [中文](README.chs.md).**

[TOC]

# OddTTS - Multi-Engine TTS Speech Synthesis API Server (Compatible with OpenAI TTS API)

OddTTS is a powerful multi-engine text-to-speech synthesis service that provides a unified API interface and a user-friendly Web UI. With a single set of APIs, it supports multiple mainstream TTS engines, including EdgeTTS, Kokoro-82M-v1.1-zh, ChatTTS, Bert-VITS2, GptSovits v2, etc., and also supports OpenAI TTS API calls.

> Notes:
> - Model files will be downloaded automatically on the first run.
> - Model file sizes:
>   - Kokoro-82M-v1.1-zh model: ~376MB.
>   - EdgeTTS model: 0MB, no download required.
>   - ChatTTS model: 2.4GB (FP16 precision).
>   - Bert-VITS2 model: ~2GB (backbone + BERT feature network; each additional language requires ~1.3GB more).
>   - GptSovits v2 model: ~2.5GB.
> - VRAM requirements:
>   - EdgeTTS model: 0MB.
>   - Kokoro-82M-v1.1-zh model: 0MB (runs on ordinary CPU).
>   - ChatTTS model: at least 2.5GB.
>   - Bert-VITS2 model: at least 5GB. For few-shot fine-tuning, a GPU with 24GB+ VRAM is recommended.
>   - GptSovits v2 model: at least 8GB. For few-shot fine-tuning, a GPU with 24GB/48GB+ VRAM is recommended.
> - Users in China are recommended to use a mirror to accelerate model downloads.
>   - Windows: set HF_ENDPOINT=https://hf-mirror.com
>   - Linux/MacOS: export HF_ENDPOINT=https://hf-mirror.com
> - Model files are large; it is recommended to run in an environment with sufficient disk space, or customize the model path (change models/hf_home to your own path).
>   - Windows: set HF_HOME=x:/models/hf_home
>   - Linux/MacOS: export HF_HOME=/models/hf_home

## I. Introduction

### 1. About OddTTS

Because the **[Xiaoluo Tongxue](https://x.oddmeta.net "Xiaoluo Tongxue")** project I am working on requires TTS speech synthesis functionality, and due to the hardware limitations of Xiaoluo Tongxue (an Alibaba Cloud ECS server at 99 CNY/year), EdgeTTS was the only option at first. However, my own computer has slightly better specs, so I tried several different TTS engines. I needed to create a unified wrapper for these TTS models so that Xiaoluo Tongxue could switch between different TTS engines at any time, and thus OddTTS was born.

Considering the wide range of uses for TTS functionality, I separated it out and open-sourced it. I hope it will be helpful to those who need TTS.

<font color=red><b>Note: If you want to use TTS engines other than EdgeTTS, you need to install the corresponding TTS engine yourself before installing and using OddTTS.</b></font>

### 2. Why Choose OddTTS?

- **Multi-Engine Support**: Integrates EdgeTTS, Kokoro, ChatTTS, Bert-VITS2, GptSovits, and other TTS engines.
- **Multiple Calling Methods**: Supports file path return, Base64 encoding return, streaming response, and other output methods.
- **User-Friendly Web UI**: Provides a visual operation interface based on Gradio.
- **RESTful API**: Provides a complete REST API for easy integration into other systems.
- **Highly Configurable**: Supports GPU acceleration, concurrent thread adjustment, model preloading, and other configuration options.
- **Cross-Platform Compatibility**: Developed based on Python, supports Windows, Linux, macOS, and other operating systems.

### 3. Recommended Hardware

| Model Name | Minimum VRAM (Original) | Smooth VRAM (Original) | Full VRAM (Original) | INT8 Quantized Minimum VRAM | INT4 Quantized Minimum VRAM | Pure CPU Viable | CPU Speed |
|----------------|------------------|------------------|--------------|------------------|------------------|---------------|------------|
| EdgeTTS | 0GB | 0GB | 0GB | 0GB | 0GB | Yes | Depends on your network speed |
| Kokoro | 0GB | 0GB | 0GB | 0GB | 0GB | Yes | High |
| ChatTTS | 2.5GB | 4GB | 6GB+ | 1.5GB | 1GB | Yes | Relatively fast |
| Bert-VITS2 | 5GB | 6GB | 8GB+ | 3GB | 2GB | Yes | Medium |
| GPT-SoVITS v2 | 8GB | 10GB | 12GB+ | 4GB | 2.5GB | Not recommended | Slow |

> Xiaoluo Tongxue Usage
> - Demo version: Alibaba Cloud ECS at 99 CNY/year (2 cores, 2GB), cannot run any TTS model locally, so EdgeTTS is used.
> - Local version: My own computer is a ten-year-old laptop, using the Kokoro-82M-v1.1-zh model, running purely on CPU and offline, with fast execution speed.

## II. Quick Start

### 1. Install OddTTS

```bash
pip install -i https://pypi.org/simple/ oddtts
```

### 2. Start OddTTS

#### 1) Start with Default Configuration

Simply run the following command in your installed virtual environment to start:

```bash
oddtts
```

After startup, OddTTS will bind to 127.0.0.1 (local access only) by default, on port 9001. Access it in your browser at: http://localhost:9001

#### 2) Start with Custom Configuration

To allow access from other IPs, start the service with the following command, setting the host to 0.0.0.0; the port can also be customized.

```bash
oddtts --host 0.0.0.0 --port 8080
```

## III. OddTTS API Documentation

### 1. API Interface List

#### 1) OpenAI API Compatible Interface

```
GET /v1/audio/speech
```

- **Function**: OpenAI TTS API compatible interface, details see [OpenAI TTS API](https://platform.openai.com/docs/api-reference/audio/create).
- **Return**: mp3 audio data.

#### 2) Get Voice List

```
GET /v1/audio/voice/list
```

- **Function**: Get all voices supported by the current TTS engine.
- **Return**: Voice list, each voice contains name, language, gender, and other information.

#### 3) Get Specific Voice Details

```
GET /v1/audio/voice/list/{voice_name}
```

- **Function**: Get detailed information for a specified voice.
- **Parameter**: `voice_name` - voice name.
- **Return**: Detailed voice information.

#### 4) Generate TTS Audio (Return File Path)

```
POST /api/oddtts/file
```

- **Function**: Generate TTS audio and return the file path.
- **Request Body**:

```json
  {
    "text": "Text to be converted to speech",
    "voice": "Voice name",
    "rate": Speech rate adjustment (-50 to 50),
    "volume": Volume adjustment (-50 to 50),
    "pitch": Pitch adjustment (-50 to 50)
  }
```

- **Return**: `{"status": "success", "file_path": "Audio file path", "format": "mp3"}`

#### 5) Generate TTS Audio (Return Base64)

```
POST /api/oddtts/base64
```

- **Function**: Generate TTS audio and return Base64 encoding.
- **Request Body**: Same as file path API.
- **Return**: `{"status": "success", "base64": "Base64 encoded audio data", "format": "mp3"}`

#### 6) Generate TTS Audio (Streaming Response)

```
POST /api/oddtts/stream
```

- **Function**: Generate TTS audio and return it as a streaming response.
- **Request Body**: Same as file path API.
- **Return**: Streaming audio data (audio/mpeg format).

#### 7) Health Check

```
GET /oddtts/health
```

- **Function**: Check if the service is running normally.
- **Return**: `{"status": "healthy", "message": "API service is running normally"}`


### 2. API Call Examples

Here are some examples of calling the OddTTS API.

> The `voice` parameter needs to be obtained from the backend voice list first, then filled in with the voice name supported by the current model (interface: `/v1/audio/voice/list`). <font color=red>The voice options differ for different models.</font>

#### 1) Call API using curl

```bash
curl.exe -X POST http://localhost:9001/api/oddtts/file ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Welcome to follow my WeChat official account: Aodeyuan. Let's learn AI together and keep up with the times!\", \"voice\": \"zm_011\", \"rate\": 0, \"volume\": 0, \"pitch\": 0}"
```

#### 2) Call API using the OpenAI library

```python
from openai import OpenAI

base_url = "http://localhost:9001/v1"
model = "oddtts-1"
api_key = "dummy"
voice = "zm_011"

text = "Welcome to follow my WeChat official account: Aodeyuan. Let's learn AI together and keep up with the times! Good good study, day day up!"

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

#### 3) Call API using the requests library

```python
import requests

# Configure API base URL
API_BASE_URL = "http://localhost:9001"

# Test text
TEST_TEXT = "Welcome to follow my WeChat official account: Aodeyuan. Let's learn AI together and keep up with the times! Good good study, day day up!"

# Get voice list
def test_api_voices():
    response = requests.get(f"{API_BASE_URL}/v1/audio/voice/list")
    voices = response.json()
    print(f"Successfully retrieved {len(voices)} voice options")
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

#### 4) Call API using JavaScript

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

generateTTS('Welcome to follow my WeChat official account: Aodeyuan. Let\'s learn AI together and keep up with the times!', 'zm_011');
```

## IV. Web Interface Usage

After the service starts, you can open the Gradio Web UI by visiting `http://localhost:9001/` in your browser. It supports the following features:

- Text input area: Enter the text to be converted to speech.
- Voice selection: Choose different voices and languages.
- Parameter adjustment: Adjust speech rate, volume, pitch, and other parameters.
- Audio generation: Click the button to generate and play speech.
- Audio download: Download the generated audio file.

## V. Frequently Asked Questions

1. **Service startup failure**
   - Check if the port is occupied.
   - Confirm that all dependency packages are installed correctly.
   - Check the log file for detailed error information.

2. **Speech synthesis failure**
   - Check if the TTS engine configuration is correct.
   - Confirm that the selected voice exists in the current TTS engine.
   - For some engines that require internet access, confirm that the network connection is normal (e.g., EdgeTTS).

3. **How to switch TTS engines**
   - Modify the `tts_type` configuration item in the `oddtts_config.py` file.
   - Restart the service for the configuration to take effect.

4. **Output format**
   - The default output format is mp3.
   - Other formats such as wav, mp3, etc., can be specified via the `response_format` parameter.

## VI. License

MIT License - see LICENSE file for details. Commercial use, personal use, feel free to use it however you like.

Questions and improvement suggestions are also welcome!
