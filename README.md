<div align="center">

<h1>OddTTS</h1>
<p><strong>Multi-Engine TTS Speech Synthesis API Server</strong> — Compatible with OpenAI TTS API</p>

<p>
  <a href="https://github.com/oddmeta/oddtts" target="_blank">⭐ GitHub</a> ·
  <a href="https://www.oddmeta.net" target="_blank">🏠 Official Site</a> ·
  <a href="https://tts.oddmeta.net" target="_blank">🌐 Live Demo</a> ·
  <a href="https://oddmeta.net/docs/oddtts" target="_blank">📖 Documentation</a>
</p>

<p>
  <a href="https://pypi.org/project/oddtts/"><img src="https://img.shields.io/pypi/v/oddtts?style=flat-square&color=blue" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/oddtts/"><img src="https://img.shields.io/pypi/pyversions/oddtts?style=flat-square&color=green" alt="Python Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License: MIT"></a>
  <a href="https://github.com/oddmeta/oddtts"><img src="https://img.shields.io/github/stars/oddmeta/oddtts?style=flat-square&color=orange" alt="GitHub Stars"></a>
</p>

<p>
  <a href="README.md">English</a> | <a href="README.chs.md">中文</a>
</p>

</div>

---

> **v2.0 Highlight: Voice Cloning** — Upload a 3-10 second reference audio to clone any voice, then use it like a built-in voice via API or Web UI.

OddTTS is a powerful multi-engine text-to-speech synthesis service that provides a unified API interface and a user-friendly Web UI. With a single set of APIs, it supports multiple mainstream TTS engines, including **EdgeTTS**, **Kokoro-82M-v1.1-zh**, **ZipVoice**, **ChatTTS**, **Bert-VITS2**, **GPT-SoVITS v2**, **MOSS-TTS-Nano**, **Audio8**, and more. It also provides an **OpenAI-compatible TTS API**.

## Features

- **Multi-Engine Support** — Integrates EdgeTTS, Kokoro, ZipVoice, ChatTTS, Bert-VITS2, GPT-SoVITS, MOSS-TTS-Nano, Audio8, and more.
- **Voice Cloning** — Upload a reference audio to clone any voice, usable via API and Web UI (v2.0+).
- **OpenAI-Compatible API** — Drop-in replacement for OpenAI's `/v1/audio/speech` endpoint.
- **Multiple Output Modes** — File path, Base64 encoding, and streaming response.
- **Web UI** — Visual operation interface with a voice cloning management panel.
- **Highly Configurable** — GPU acceleration, concurrent thread adjustment, model preloading.
- **Cross-Platform** — Windows, Linux, macOS.
- **Pure CPU Ready** — Several engines run entirely on CPU with no GPU required.

## Supported Engines

| Engine | Model Size | VRAM (Original) | Pure CPU | Speed | Languages |
|--------|-----------|-----------------|----------|-------|-----------|
| EdgeTTS | 0 MB | 0 GB | Yes | Network | Multi |
| Kokoro v1.1 | ~376 MB | 0 GB | Yes | High | Chinese, English |
| ZipVoice INT8 | ~186 MB | 0 GB | Yes | Medium | Chinese + English |
| MOSS-TTS-Nano | ~200 MB | 0 GB | Yes | High | ~20 languages |
| Audio8 0.1B INT8 | ~150 MB | 0 GB | Yes | High | 11 languages |
| Audio8 0.6B INT4 | ~400 MB | 0 GB | Yes | Medium | 11 languages |
| ChatTTS | ~2.4 GB | 2.5 GB+ | Yes | Fast | Chinese, English |
| Bert-VITS2 | ~2 GB | 5 GB+ | Yes | Medium | Multi |
| GPT-SoVITS v2 | ~2.5 GB | 8 GB+ | No | Slow | Chinese, English, Japanese |

> **Note:** Model files are downloaded automatically on the first run. For users in China, set `HF_ENDPOINT=https://hf-mirror.com` to accelerate downloads.

## Quick Start

**Requirements:** Python >= 3.12

### Installation

```bash
pip install oddtts
```

### Start the Server

```bash
# Default: localhost only, port 9001
oddtts

# Allow external access with custom port
oddtts --host 0.0.0.0 --port 8080
```

Then open `http://localhost:9001` in your browser.

## API Documentation

### OpenAI-Compatible Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/audio/speech` | OpenAI-compatible TTS (returns MP3) |
| GET | `/v1/audio/voice/list` | List all available voices |
| GET | `/v1/audio/voice/list/{voice_name}` | Get voice details |

### OddTTS Native Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/oddtts/file` | Generate TTS and return file path |
| POST | `/api/oddtts/base64` | Generate TTS and return Base64 |
| POST | `/api/oddtts/stream` | Generate TTS with streaming response |
| GET | `/oddtts/health` | Health check |

### Voice Cloning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice/clone` | Upload reference audio and register voice |
| GET | `/api/voice/clone/list` | List cloned voices |
| DELETE | `/api/voice/clone/<engine>/<voice_id>` | Delete a cloned voice |
| GET | `/api/voice/clone/audio/<engine>/<voice_id>` | Preview reference audio |

### Example: OpenAI Library

```python
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://localhost:9001/v1")

response = client.audio.speech.create(
    model="oddtts-1",
    input="Hello, this is a test.",
    voice="zm_011",
    response_format="mp3"
)
response.write_to_file("output.mp3")
```

### Example: cURL

```bash
curl -X POST http://localhost:9001/api/oddtts/file \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "zm_011", "rate": 0, "volume": 0, "pitch": 0}'
```

### Example: Voice Cloning

```bash
# Upload reference audio
curl -X POST http://localhost:9001/api/voice/clone \
  -F "audio_file=@reference.wav" \
  -F "name=xiaoming" \
  -F "display_name=Xiaoming" \
  -F "engine=moss_nano"

# Use cloned voice via OpenAI-compatible API
curl -X POST http://localhost:9001/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello from cloned voice", "voice": "xiaoming"}' \
  --output cloned.mp3
```

## Web Interface

After starting the server, visit `http://localhost:9001/` to access the Web UI:

- Text input area
- Voice selection (including cloned voices marked with )
- Rate / Volume / Pitch adjustment
- Audio generation, playback, and download
- **Voice Cloning Panel** — Upload, manage, preview, and delete cloned voices

## Project Structure

```
oddtts/
├── oddtts/
│   ├── app.py                 # Entry point
│   ├── oddtts_config.py       # Server configuration
│   ├── oddtts_params.py       # TTS enums & audio utils
│   ├── models/
│   │   ├── base_tts_driver.py # Strategy dispatcher
│   │   ├── tts_edge.py        # EdgeTTS engine
│   │   ├── tts_kokoro_v11.py  # Kokoro v1.1 engine
│   │   ├── tts_zipvoice.py    # ZipVoice engine
│   │   ├── tts_moss_nano.py   # MOSS-TTS-Nano engine
│   │   ├── tts_audio8_*.py    # Audio8 engines
│   │   └── ...                # Other engines
│   ├── router/
│   │   └── api.py             # REST API endpoints
│   ├── static/                # Web UI assets
│   └── templates/             # HTML templates
├── models/                    # Downloaded model files
├── voices/                    # Cloned voice storage
├── tests/                     # Test scripts
└── docs/                      # Documentation
```

## Configuration

Key configuration options in `oddtts_config.py` (or `~/.config/oddtts/config.json` after first run):

| Option | Default | Description |
|--------|---------|-------------|
| `tts_type` | `ODDTTS_KOKORO_V1_1` | Default TTS engine |
| `preload_model` | `True` | Preload model on startup |
| `enable_gpu` | `False` | Enable GPU acceleration |
| `concurrent_thread` | `8` | Concurrent synthesis threads |
| `model_base_dir` | `"models"` | Model storage directory |
| `voices_base_dir` | `"voices"` | Cloned voice storage directory |

## FAQ

**Q: Service startup failure?**
- Check if the port is occupied.
- Confirm all dependencies are installed.
- Check `logs/oddtts.log` for detailed errors.

**Q: Speech synthesis failure?**
- Verify TTS engine configuration.
- Confirm the selected voice exists for the current engine.
- For online engines (e.g., EdgeTTS), check network connectivity.

**Q: How to switch TTS engines?**
- Modify `tts_type` in `~/.config/oddtts/config.json` or use the Web UI.
- Restart the service for changes to take effect.

**Q: Can I run without a GPU?**
- Yes! EdgeTTS, Kokoro, ZipVoice, MOSS-TTS-Nano, and Audio8 all run purely on CPU.

## Contact Us

| Channel | Handle |
|---------|--------|
| WeChat Official Account | 奥德元 |
| WeChat | oddmeta |
| Weibo | [oddmeta](https://weibo.com/oddmeta) |
| Twitter / X | [oddmet](https://x.com/oddmet) |

## License

MIT License — see [LICENSE](LICENSE) for details. Free for commercial and personal use.

Questions and suggestions welcome! Contact: <hi@oddmeta.com>
