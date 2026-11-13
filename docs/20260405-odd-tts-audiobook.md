# 用 oh-my-openagent + OddTTS 从0实现有声书功能

---

## 一、先看效果

你有一本 10 万字的技术电子书，想把它变成有声书。不是那种机器感很强的合成音，而是自然流畅的人声。

把文本拖进去，点一下开始，然后去喝杯咖啡。回来的时候，一本完整的有声书已经躺在你的文件夹里了。

这不是科幻，这是我真做出来的功能。

实测效果：
- 5 万字文本 → 约 2.5 小时音频
- 纯 CPU 推理，不需要显卡
- 8 种音色切换（Kokoro 引擎）
- 中英混合朗读自然
- 中途停止后可以从断点继续

---

## 二、什么是 OddTTS？

OddTTS 是我之前开源的语音合成 API 封装项目。

![odd-tts-audiobook-01](/images/oddtts/odd-tts-audiobook-01.png)

两个特点：**多引擎、低成本**。

![odd-tts-audiobook-02](/images/oddtts/odd-tts-audiobook-02.png)

多引擎：支持 Kokoro、MeloTTS、Edge TTS、OpenAI TTS 统一调用。

- Kokoro：82M 参数，CPU 就能跑，8 种音色，中英混合效果还行
- MeloTTS：轻量级，CPU 可跑
- Edge TTS：微软云端，效果好但要联网
- OpenAI TTS：效果最好，但收费

低成本：Kokoro 可以在十年前的老笔记本上跑，纯 CPU 推理，一次部署无限使用。

以前做有声书，要么买云端 API（一本书几十块），要么自己部署大模型（需要显卡）。

现在一台几百块的 CPU 机器就能跑，还免费。

---

## 三、用 oh-my-openagent 实现的全流程

这一节讲讲我怎么做这个项目。

![odd-tts-audiobook-03](/images/oddtts/odd-tts-audiobook-03.png)

### 3.1 第一步：需求分析

用的 Agent：Metis（预规划分析）

直接跟 oh-my-openagent 说"我想做一个有声书功能"，它会调用 Metis 帮你分析：

- 需求模糊的地方在哪
- 有什么没考虑到的 corner case
- 优先级是什么

Metis 分析的结果：

```markdown
## 需求分析

### 明确的需求
1. 长文本转语音
2. 多引擎切换
3. 进度保存和恢复

### 模糊的地方
1. 单次最大处理多少字？
2. 需要实时流式输出吗？
3. 支持多语言混合吗？

### 潜在风险
1. 超长文本可能内存爆掉
2. 网络中断要处理断点续传
3. 音频格式兼容性
```

### 3.2 第二步：制定计划

用的 Agent：Prometheus（任务规划）

Prometheus 会制定详细的实现计划：

- 分哪些模块
- 模块依赖关系
- 工作量估算

Prometheus 输出的计划：

```markdown
## 实现计划

### 模块划分

模块 1：文本预处理
- 输入验证
- 文本清洗
- 智能分段

模块 2：TTS 服务集成
- OddTTS API 封装
- 多引擎切换
- 音色和语速配置

模块 3：音频处理
- 音频片段保存
- 拼接算法
- 输出格式转换

模块 4：进度管理
- 进度保存
- 断点恢复

模块 5：Web 服务
- FastAPI 接口
- RESTful API

### 依赖关系
1. 先实现文本预处理
2. TTS 服务依赖文本预处理
3. 音频处理依赖 TTS 服务
4. 进度管理独立
5. Web 服务依赖所有模块

### 工作量估算
- 模块 1：2 小时
- 模块 2：3 小时
- 模块 3：2 小时
- 模块 4：1 小时
- 模块 5：3 小时
- 总计：约 11 小时
```

### 3.3 第三步：代码探索

用的 Agent：Explore（内部探索）

写代码前，先让 Explore 分析 OddTTS 源码，理解 API 接口。

Explore 会做这些：
1. 找到 API 端点
2. 理解请求/响应格式
3. 找到配置文件结构
4. 了解错误处理机制

探索结果：

```markdown
## OddTTS API 分析

### 端点
- POST /tts - 语音合成
- GET /voices - 音色列表
- GET /engines - 引擎列表

### 请求格式
{"text": "...", "voice": "af_sarah", "engine": "kokoro", "speed": 1.0, "output_format": "mp3"}

### 响应格式
{"audio": "base64...", "duration": 3.5, "chars": 15}

### 关键配置
- 端口：8000
- 超时：60秒
- 最大文本：4000字符
```

### 3.4 第四步：模块实现

用的 Agent：Sisyphus（主编排）

Sisyphus 是总调度，会把计划拆成具体任务，调用合适的子 agent 执行，协调各模块集成。

#### 4.1 text_splitter.py

```python
import re
from typing import List

class TextSplitter:
    def __init__(self, max_length: int = 2000):
        self.max_length = max_length
    
    def split(self, text: str) -> List[str]:
        sentences = re.split(r'([。！？])', text)
        chunks = []
        current = ""
        
        for s in sentences:
            if len(current) + len(s) <= self.max_length:
                current += s
            else:
                if current:
                    chunks.append(current)
                current = s
        
        if current:
            chunks.append(current)
        return chunks
    
    def clean(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、：；""''（）【】《》]', '', text)
        return text.strip()
```

#### 4.2 tts_client.py

```python
import requests
from typing import Optional, Dict, List
import base64

class TTSClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def synthesize(self, text: str, voice: str = "af_sarah", 
                   engine: str = "kokoro", speed: float = 1.0) -> Optional[bytes]:
        try:
            response = requests.post(
                f"{self.base_url}/tts",
                json={"text": text, "voice": voice, "engine": engine, 
                      "speed": speed, "output_format": "mp3"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return base64.b64decode(data["audio"])
            else:
                print(f"TTS API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"TTS request failed: {e}")
            return None
    
    def get_voices(self) -> List[Dict]:
        response = requests.get(f"{self.base_url}/voices")
        return response.json()["voices"]
```

#### 4.3 progress.py

```python
import json
import os
from typing import Optional, Dict
from datetime import datetime

class ProgressManager:
    def __init__(self, progress_file: str = "progress.json"):
        self.progress_file = progress_file
    
    def save(self, task_id: str, current_index: int, total: int, 
             output_file: str, chunk_files: list):
        progress = {
            "task_id": task_id,
            "current_index": current_index,
            "total": total,
            "output_file": output_file,
            "chunk_files": chunk_files,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def load(self) -> Optional[Dict]:
        if not os.path.exists(self.progress_file):
            return None
        
        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    
    def clear(self):
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
```

#### 4.4 audio_merger.py

```python
from pydub import AudioSegment
from typing import List
import os

class AudioMerger:
    def merge(self, chunk_files: List[str], output_file: str, 
              format: str = "mp3") -> bool:
        try:
            combined = AudioSegment.empty()
            
            for f in chunk_files:
                if os.path.exists(f):
                    audio = AudioSegment.from_mp3(f)
                    combined += audio
            
            combined.export(output_file, format=format)
            return True
        except Exception as e:
            print(f"Audio merge failed: {e}")
            return False
    
    def merge_with_silence(self, chunk_files: List[str], output_file: str,
                           silence_ms: int = 500) -> bool:
        try:
            combined = AudioSegment.empty()
            silence = AudioSegment.silent(duration=silence_ms)
            
            for i, f in enumerate(chunk_files):
                if os.path.exists(f):
                    audio = AudioSegment.from_mp3(f)
                    combined += audio
                    if i < len(chunk_files) - 1:
                        combined += silence
            
            combined.export(output_file, format="mp3")
            return True
        except Exception as e:
            print(f"Audio merge failed: {e}")
            return False
```

#### 4.5 app.py（FastAPI 主服务）

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os

from text_splitter import TextSplitter
from tts_client import TTSClient
from progress import ProgressManager
from audio_merger import AudioMerger

app = FastAPI(title="有声书转换服务")

splitter = TextSplitter(max_length=2000)
tts_client = TTSClient()
progress_mgr = ProgressManager()
merger = AudioMerger()

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class ConvertRequest(BaseModel):
    text: str
    voice: str = "af_sarah"
    engine: str = "kokoro"
    speed: float = 1.0
    with_silence: bool = True
    silence_ms: int = 500

class ConvertResponse(BaseModel):
    task_id: str
    total_chunks: int
    message: str

@app.post("/convert", response_model=ConvertResponse)
async def convert(req: ConvertRequest):
    cleaned_text = splitter.clean(req.text)
    chunks = splitter.split(cleaned_text)
    
    task_id = str(uuid.uuid4())
    total = len(chunks)
    
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    chunk_files = []
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{total}...")
        
        audio_data = tts_client.synthesize(chunk, req.voice, req.engine, req.speed)
        
        if audio_data:
            chunk_file = os.path.join(task_dir, f"chunk_{i:04d}.mp3")
            with open(chunk_file, "wb") as f:
                f.write(audio_data)
            chunk_files.append(chunk_file)
        
        progress_mgr.save(task_id, i, total, "", chunk_files)
    
    output_file = os.path.join(task_dir, "audiobook.mp3")
    if req.with_silence:
        merger.merge_with_silence(chunk_files, output_file, req.silence_ms)
    else:
        merger.merge(chunk_files, output_file)
    
    progress_mgr.clear()
    
    return ConvertResponse(
        task_id=task_id,
        total_chunks=total,
        message=f"转换完成！音频保存在 {output_file}"
    )

@app.get("/progress")
async def get_progress():
    progress = progress_mgr.load()
    if progress:
        return progress
    return {"message": "没有进行中的任务"}

@app.get("/audio/{task_id}")
async def get_audio(task_id: str):
    audio_file = os.path.join(OUTPUT_DIR, task_id, "audiobook.mp3")
    if os.path.exists(audio_file):
        return FileResponse(audio_file, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="音频文件不存在")

@app.get("/voices")
async def get_voices():
    return {"voices": tts_client.get_voices()}
```

### 3.5 第五步：调试和优化

用的 Agent：Oracle（架构咨询）+ Artistry（创意解决）

遇到问题怎么办：
- Oracle 分析问题，给出解决方案
- Artistry 尝试非常规思路

常见问题：

```markdown
问题 1：TTS 超时

原因：文本太长或网络问题

方案：
1. 减少单次请求长度
2. 加重试机制
3. 用流式 API

问题 2：内存占用过高

原因：音频数据全堆内存里

方案：
1. 边生成边写磁盘
2. 定期清理缓存
3. 流式处理

问题 3：音频拼接有爆音

原因：片段之间突变

方案：
1. 加淡入淡出
2. 加静音间隔
3. 用 crossfade
```

### 3.6 第六步：代码审查

用的 Agent：Momus（计划评审）

代码写完后，让 Momus 审查：
- 结构合理吗
- 边界情况有没有漏
- 错误处理完善吗

---

## 四、能做什么？

![odd-tts-audiobook-04](/images/oddtts/odd-tts-audiobook-04.png)

### 4.1 使用场景

场景一：技术文档有声化。把技术文档转成有声书，上下班听。

场景二：学习资料朗读。把论文、教程转成音频，散步时听。

场景三：多语言有声书。Kokoro 支持中英混合，读技术英文书很合适。

### 4.2 支持的功能

| 功能 | 说明 |
|------|------|
| 音色选择 | 8 种内置音色 |
| 语速调节 | 0.5x - 2.0x |
| 进度保存 | 中断后可继续 |
| 批量处理 | 一键生成完整有声书 |
| 多种格式 | MP3、WAV |

---

## 五、核心要点

用 oh-my-openagent 做这个项目，Workflow 是这样的：

规划 → Prometheus 制定计划

探索 → Explore 分析源码

实现 → Sisyphus 协调开发

调试 → Oracle/Artistry 解决问题

审查 → Momus 把关质量

核心心法：**让专业的 agent 做专业的事**。

不要一个 agent 又是计划又是执行又是调试。分工协作，效率完全不一样。

---

## 六、注意事项

### 6.1 文本质量

TTS 对文本敏感。乱码、特殊字符太多会影响效果。

先做文本清洗：

```python
def clean(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、：；""''（）【】《》]', '', text)
    return text.strip()
```

### 6.2 超长文本

10 万字以上，建议分批处理。每批 1-2 万字，处理完一批保存一次进度。

### 6.3 音质优化

想要更高音质，可以换 Edge TTS 或 OpenAI TTS。代价是要联网、要花钱。

---

## 七、总结

oh-my-openagent + OddTTS 做有声书，本质是把"AI 编程"和"AI 语音"两个能力结合起来。

OddTTS 把文字变成声音。

oh-my-openagent 把开发过程变得高效。

以前几天才能做完的东西，现在几个小时就搞定。

这就是工具进步带来的变化。

---

## 相关资源

- OddTTS 项目：https://github.com/oddmeta/oddtts
- oh-my-openagent：https://github.com/code-yeongyu/oh-my-openagent
- Kokoro 模型：https://github.com/remsky/Kokoro-ONNX

---

## 广而告之

<div style="text-align: center;">
<span>关注公众号：奥德元</span>
<br>
<br>
<span style="font-size: 1.2em; font-weight: bold; color: red;">一起学习AI，一起追赶时代！</span>
<br>
<br>
<span>新建了一个AI技术交流群，欢迎大家一起加入讨论。</span>
<br>
<span>扫码加入AI技术交流群（微信）</span>
<br>
<span>若需联系作者，请加微信：<b>oddmeta</b></span>
</div>