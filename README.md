[TOC]

Here’s a draft for the `README.md` file based on your project:

---

# OddTTS: A Simple TTS API Server

![GitHub](https://img.shields.io/github/license/oddmeta/oddtts)

A simplest TTS web interface, and API access, supporting serveral different TTS engine and models, including EdgeTTS, ChatTTS, BertVits2, BertVits2 v2, and omserver(GPT Sovits wrapper).



# Overview
OddTTS is a powerful TTS service that integrates multiple speech synthesis engines into a unified platform. It provides both a user-friendly web interface and a REST API for programmatic access, supporting various voice customization options.

# Features
Multiple TTS engine support:
- Edge TTS (default)
- ChatTTS
- Bert-VITS2
- OMServer(GPT sovits)
- Web interface with Gradio
- REST API with FastAPI
- Voice customization (speed, volume, pitch)
- Character voice selection
- Configurable through YAML settings
- Chinese language support

# Installation

bash
pip install edge-tts gradio fastapi uvicorn pyyaml
Usage
Starting the Service

bash
python oddtts.py
Web Interface
Access the Gradio web interface at http://localhost:7860 after starting the service.

Features include:

Text input area
Voice selection by locale
Speech parameter adjustment (speed, volume, pitch)
Audio playback and download
API Endpoints
The FastAPI backend provides RESTful endpoints for programmatic access. Documentation available at /docs.

# Configuration
Modify config.yml to set:

Default character voice
Audio parameters
Voice switch default state
Emotional parameters
Supported TTS Engines
TTSEdge: Microsoft Edge TTS
TTSChatTTS: ChatTTS engine
TTSBertVITS2: Bert-VITS2 engine
TTSOMServer: OMServer engine

# Project Structure
oddtts.py: Main application entry point
base_tts_driver.py: TTS engine interface and drivers
config: Configuration files

## License
This project is NOT licensed under any License.
Copy free, without any string attached! Just happy coding!
