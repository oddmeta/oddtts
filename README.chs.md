<div align="center">

<h1>OddTTS</h1>
<p><strong>多引擎 TTS 语音合成 API 服务</strong> — 兼容 OpenAI TTS API</p>

<p>
  <a href="https://www.oddmeta.net" target="_blank">🏠 官方网站</a> ·
  <a href="https://minutes.oddmeta.net" target="_blank">🌐 在线演示</a> ·
  <a href="https://oddmeta.net/docs/oddminutes" target="_blank">📖 文档中心</a>
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

> **v2.0 亮点：音色克隆** — 上传一段 3-10 秒的参考音频即可克隆任意音色，通过 API 或 Web 界面像内置音色一样使用。

OddTTS 是一个功能强大的多引擎语音合成服务，提供统一的 API 接口和友好的 Web 界面。一套接口支持多种主流 TTS 引擎，包括 **EdgeTTS**、**Kokoro-82M-v1.1-zh**、**ZipVoice**、**ChatTTS**、**Bert-VITS2**、**GPT-SoVITS v2**、**MOSS-TTS-Nano**、**Audio8** 等，同时提供 **OpenAI 兼容的 TTS API**。

## 目录

- [特性](#特性)
- [支持的引擎](#支持的引擎)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [Web 界面](#web-界面)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 特性

- **多引擎支持** — 集成 EdgeTTS、Kokoro、ZipVoice、ChatTTS、Bert-VITS2、GPT-SoVITS、MOSS-TTS-Nano、Audio8 等多种 TTS 引擎
- **音色克隆** — 上传参考音频即可克隆任意音色，通过 API 和 Web 界面直接使用（v2.0+）
- **OpenAI 兼容 API** — 可直接替换 OpenAI `/v1/audio/speech` 接口
- **多种输出方式** — 文件路径返回、Base64 编码返回、流式响应
- **Web 界面** — 可视化操作界面，含音色克隆管理面板
- **高度可配置** — 支持 GPU 加速、并发线程调整、模型预加载
- **跨平台** — 支持 Windows、Linux、macOS
- **纯 CPU 运行** — 多个引擎无需 GPU 即可运行

## 支持的引擎

| 引擎 | 模型大小 | 原版显存需求 | 纯 CPU | 速度 | 支持语言 |
|------|---------|-------------|--------|------|---------|
| EdgeTTS | 0 MB | 0 GB | 支持 | 取决于网络 | 多语言 |
| Kokoro v1.1 | ~376 MB | 0 GB | 支持 | 高 | 中英混合 |
| ZipVoice INT8 | ~186 MB | 0 GB | 支持 | 中等 | 中英混合 |
| MOSS-TTS-Nano | ~200 MB | 0 GB | 支持 | 高 | 近 20 种语言 |
| Audio8 0.1B INT8 | ~150 MB | 0 GB | 支持 | 高 | 11 种语言 |
| Audio8 0.6B INT4 | ~400 MB | 0 GB | 支持 | 中等 | 11 种语言 |
| ChatTTS | ~2.4 GB | 2.5 GB+ | 支持 | 较快 | 中文、英文 |
| Bert-VITS2 | ~2 GB | 5 GB+ | 支持 | 中等 | 多语言 |
| GPT-SoVITS v2 | ~2.5 GB | 8 GB+ | 不建议 | 较慢 | 中日英 |

> **注意：** 首次运行时会自动下载模型文件。国内用户建议设置 `HF_ENDPOINT=https://hf-mirror.com` 加速下载。

## 快速开始

**环境要求：** Python >= 3.12

### 安装

```bash
pip install oddtts
```

### 启动服务

```bash
# 默认仅本地访问，端口 9001
oddtts

# 允许外部访问，自定义端口
oddtts --host 0.0.0.0 --port 8080
```

然后浏览器访问 `http://localhost:9001`。

## API 文档

### OpenAI 兼容接口

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/v1/audio/speech` | OpenAI 兼容 TTS（返回 MP3） |
| GET | `/v1/audio/voice/list` | 获取所有可用音色 |
| GET | `/v1/audio/voice/list/{voice_name}` | 获取指定音色详情 |

### OddTTS 原生接口

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/oddtts/file` | 生成语音并返回文件路径 |
| POST | `/api/oddtts/base64` | 生成语音并返回 Base64 |
| POST | `/api/oddtts/stream` | 生成语音并流式返回 |
| GET | `/oddtts/health` | 健康检查 |

### 音色克隆接口

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/voice/clone` | 上传参考音频并注册音色 |
| GET | `/api/voice/clone/list` | 列出自定义音色 |
| DELETE | `/api/voice/clone/<engine>/<voice_id>` | 删除克隆音色 |
| GET | `/api/voice/clone/audio/<engine>/<voice_id>` | 试听参考音频 |

### 示例：使用 OpenAI 库

```python
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://localhost:9001/v1")

response = client.audio.speech.create(
    model="oddtts-1",
    input="你好，这是测试。",
    voice="zm_011",
    response_format="mp3"
)
response.write_to_file("output.mp3")
```

### 示例：使用 cURL

```bash
curl -X POST http://localhost:9001/api/oddtts/file \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界", "voice": "zm_011", "rate": 0, "volume": 0, "pitch": 0}'
```

### 示例：音色克隆

```bash
# 上传参考音频并注册克隆音色
curl -X POST http://localhost:9001/api/voice/clone \
  -F "audio_file=@reference.wav" \
  -F "name=xiaoming" \
  -F "display_name=小明" \
  -F "engine=moss_nano"

# 通过 OpenAI 兼容接口使用克隆音色
curl -X POST http://localhost:9001/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "你好，这是克隆音色测试", "voice": "xiaoming"}' \
  --output cloned.mp3
```

## Web 界面

服务启动后，浏览器访问 `http://localhost:9001/` 即可使用 Web 界面：

- 文本输入区域
- 语音选择（克隆音色带  标记）
- 语速 / 音量 / 音调调节
- 语音生成、播放和下载
- **音色克隆面板** — 上传参考音频、管理克隆音色、试听和删除

## 项目结构

```
oddtts/
├── oddtts/
│   ├── app.py                 # 入口文件
│   ├── oddtts_config.py       # 服务配置
│   ├── oddtts_params.py       # TTS 枚举与音频工具
│   ├── models/
│   │   ├── base_tts_driver.py # 策略调度器
│   │   ├── tts_edge.py        # EdgeTTS 引擎
│   │   ├── tts_kokoro_v11.py  # Kokoro v1.1 引擎
│   │   ├── tts_zipvoice.py    # ZipVoice 引擎
│   │   ├── tts_moss_nano.py   # MOSS-TTS-Nano 引擎
│   │   ├── tts_audio8_*.py    # Audio8 引擎
│   │   └── ...                # 其他引擎
│   ├── router/
│   │   └── api.py             # REST API 端点
│   ├── static/                # Web UI 资源
│   └── templates/             # HTML 模板
├── models/                    # 下载的模型文件
├── voices/                    # 克隆音色存储
├── tests/                     # 测试脚本
└── docs/                      # 文档资料
```

## 配置说明

`oddtts_config.py` 中的主要配置项（首次运行后会生成 `~/.config/oddtts/config.json`）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `tts_type` | `ODDTTS_KOKORO_V1_1` | 默认 TTS 引擎 |
| `preload_model` | `True` | 启动时预加载模型 |
| `enable_gpu` | `False` | 启用 GPU 加速 |
| `concurrent_thread` | `8` | 并发合成线程数 |
| `model_base_dir` | `"models"` | 模型存放目录 |
| `voices_base_dir` | `"voices"` | 克隆音色存放目录 |

## 常见问题

**Q: 服务启动失败？**
- 检查端口是否被占用
- 确认所有依赖包已正确安装
- 查看 `logs/oddtts.log` 获取详细错误信息

**Q: 语音合成失败？**
- 检查 TTS 引擎配置是否正确
- 确认选择的语音存在于当前 TTS 引擎中
- 对于需要联网的引擎，确认网络连接正常（如 EdgeTTS）

**Q: 如何切换 TTS 引擎？**
- 修改 `~/.config/oddtts/config.json` 中的 `tts_type` 配置项，或通过 Web 界面切换
- 重启服务使配置生效

**Q: 没有 GPU 可以使用吗？**
- 可以！EdgeTTS、Kokoro、ZipVoice、MOSS-TTS-Nano、Audio8 均支持纯 CPU 运行。

## 📬 联系我们

| 渠道 | 账号 |
|------|------|
| 微信公众号 | 奥德元 |
| 微信 | oddmeta |
| 微博 | [oddmeta](https://weibo.com/oddmeta) |
| Twitter / X | [oddmet](https://x.com/oddmet) |

## 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE) 文件。商用、个人用，均可自由使用。

欢迎提交问题和改进建议！联系邮箱：<hi@oddmeta.com>
