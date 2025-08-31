import edge_tts
import asyncio
import gradio as gr
import tempfile
import os
import json
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request

import uvicorn
from fastapi import FastAPI
import gradio as gr

from base_tts_driver import TTSDriver

# Global variables for voice data
single_tts_driver = TTSDriver()

voices = []
voice_map = {}
voice_options = []

# 获取所有可用语音 - 修复KeyError问题
async def get_voices():
    voices = await edge_tts.list_voices()
    voice_list = []
    
    for v in voices:
        # 只提取确保存在的字段，避免KeyError
        voice_info = {
            "name": v.get("Name"),
            "gender": v.get("Gender"),
            "locale": v.get("Locale"),
            "short_name": v.get("ShortName")
        }
        
        # 可选字段，存在才添加
        if "LocalName" in v:
            voice_info["local_name"] = v["LocalName"]
            
        voice_list.append(voice_info)
    
    return voice_list

# 生成TTS音频并返回文件路径
async def generate_tts_file(text, voice, rate, volume, pitch):
    # 确保参数格式正确，包含正负符号
    rate_str = f"{rate:+d}%"
    volume_str = f"{volume:+d}%"
    pitch_str = f"{pitch:+d}Hz"
    
    communicate = edge_tts.Communicate(
        text, 
        voice, 
        rate=rate_str, 
        volume=volume_str, 
        pitch=pitch_str
    )
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        output_file = f.name
    
    # 生成音频
    await communicate.save(output_file)
    return output_file

# 生成TTS音频并返回字节流
async def generate_tts_bytes(text, voice, rate, volume, pitch):
    rate_str = f"{rate:+d}%"
    volume_str = f"{volume:+d}%"
    pitch_str = f"{pitch:+d}Hz"
    
    communicate = edge_tts.Communicate(
        text, 
        voice, 
        rate=rate_str, 
        volume=volume_str, 
        pitch=pitch_str
    )
    
    # 将音频数据保存到字节流
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    return audio_data

# 定义Gradio接口和额外的API端点
def create_gradio_interface():
    global voices, voice_options
    
    with gr.Blocks(title="OddTTS 服务") as demo:
        # 存储最后生成的音频文件路径，用于后续下载
        last_audio_path = gr.State(None)
        
        gr.Markdown("# OddTTS 语音合成服务")
        gr.Markdown("提供语音合成API，支持多种调用方式")
        
        with gr.Tab("语音合成演示"):
            with gr.Row():
                with gr.Column(scale=3):
                    text_input = gr.Textbox(label="输入文本", lines=5, placeholder="请输入要转换为语音的文本...")

                    voice_locales_select = gr.Dropdown([], label="选择语种", interactive=True)
                    voice_select = gr.Dropdown([], label="选择语音", interactive=True)
                    
                    with gr.Row():
                        rate_slider = gr.Slider(-50, 50, 0, step=5, label="语速 (%)")
                        volume_slider = gr.Slider(-50, 50, 0, step=5, label="音量 (%)")
                    
                    pitch_slider = gr.Slider(-50, 50, 0, step=5, label="音调 (Hz)")
                    generate_btn = gr.Button("生成语音", variant="primary")
                
                with gr.Column(scale=2):
                    audio_output = gr.Audio(label="生成的语音")
                    download_btn = gr.Button("下载音频")

        # 添加界面加载事件，动态获取语音列表
        async def load_locales():
            global voices
            # 等待voices数据加载完成
            while not voices:
                await asyncio.sleep(0.1)

            # 提取唯一的locale并排序
            unique_locales = sorted({v["locale"] for v in voices if v.get("locale") is not None})
            print(f"加载locale选项: type={type(unique_locales)}, content={unique_locales}")
            return gr.update(choices=unique_locales, value=unique_locales[0] if unique_locales else None)
        
        def load_voices(): 
            print(f"加载voice选项: type={type(voice_options)}, content={voice_options}")
            return gr.update(choices=voice_options, value=voice_options[0] if voice_options else None)

        # 添加locale筛选语音的事件处理函数
        def filter_voices_by_locale(selected_locale):
            global voice_options, voice_map
            if not selected_locale:  # 如果没有选择locale，返回所有语音
                filtered_voices = voice_options
            else:  # 根据选中的locale筛选语音
                filtered_voices = [
                    voice_name for voice_name in voice_options 
                    if voice_map.get(voice_name, {}).get("locale") == selected_locale
                ]
            print(f"根据locale {selected_locale} 筛选后: {filtered_voices}")
            return gr.update(
                choices=filtered_voices,
                value=filtered_voices[0] if filtered_voices else None
            )

        demo.load(load_locales, None, [voice_locales_select])
        demo.load(load_voices, None, [voice_select])

        voice_locales_select.change(
            fn=filter_voices_by_locale,
            inputs=[voice_locales_select],
            outputs=[voice_select]
        )

        # 生成语音按钮点击事件
        async def generate_audio(text, voice, rate, volume, pitch):
            audio_path = await generate_tts_file(text, voice, rate, volume, pitch)
            return audio_path, audio_path
        
        generate_btn.click(
            fn=generate_audio,
            inputs=[text_input, voice_select, rate_slider, volume_slider, pitch_slider],
            outputs=[last_audio_path, audio_output]
        )
        
        # 下载按钮点击事件
        def download_audio(file_path):
            if file_path and os.path.exists(file_path):
                return gr.File(file_path)
            return None
        
        download_btn.click(
            fn=download_audio,
            inputs=[last_audio_path],
            outputs=[gr.File(label="下载音频")]
        )
    
    return demo


# 创建FastAPI主应用
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - 加载语音列表
    global voices, voice_options, voice_map

    print("Loading voices...")
    voices = await get_voices()
    print(voices)
    print("Voices loaded.")

    voice_options = [v["name"] for v in voices if v["name"] is not None]
    voice_map = {v["name"]: v for v in voices if v["name"] is not None}
     
    yield
    # Shutdown - 可选的清理代码
    pass

app = FastAPI(title="OddTTS API Service", lifespan=lifespan)

# 添加CORS中间件（移至主应用配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
# 添加健康检查端点（移动到这里）
@app.get("/oddtts/health")
def health_check():
        return {"status": "healthy", "message": "API服务运行正常"}

# 1. 获取语音列表API
@app.get("/api/oddtts/voices")
def api_get_voices():
        """获取所有可用的语音列表"""
        return voices
    
# 2. 获取特定语音详情API
@app.get("/api/oddtts/voices/{voice_name}")
def api_get_voice_details(voice_name: str):
        """获取特定语音的详细信息"""
        if voice_name in voice_map:
            return voice_map[voice_name]
        return {"error": f"Voice '{voice_name}' not found"}, 404
    
# 3. TTS生成API - 返回文件路径
@app.post("/api/oddtts/file")
async def api_tts_file(request: Request):
        """生成TTS音频并返回文件路径"""
        data = await request.json()
        text = data.get("text")
        voice = data.get("voice")
        rate = data.get("rate", 0)
        volume = data.get("volume", 0)
        pitch = data.get("pitch", 0)
        
        # 如果未指定语音，使用第一个可用语音
        if not voice and voice_options:
            voice = voice_options[0]
        
        if not voice or voice not in voice_map:
            return {"error": f"Voice '{voice}' not found"}, 404
        
        try:
            audio_path = await generate_tts_file(text, voice, rate, volume, pitch)
            return {"status": "success", "file_path": audio_path, "format": "mp3"}
        except Exception as e:
            return {"error": str(e)}, 500
    
# 4. TTS生成API - 返回Base64编码
@app.post("/api/oddtts/base64")
async def api_tts_base64(request: Request):
        """生成TTS音频并返回Base64编码"""
        data = await request.json()
        text = data.get("text")
        voice = data.get("voice")
        rate = data.get("rate", 0)
        volume = data.get("volume", 0)
        pitch = data.get("pitch", 0)
        
        # 如果未指定语音，使用第一个可用语音
        if not voice and voice_options:
            voice = voice_options[0]
            
        if not voice or voice not in voice_map:
            return {"error": f"Voice '{voice}' not found"}, 404
        
        try:
            audio_bytes = await generate_tts_bytes(text, voice, rate, volume, pitch)
            import base64
            base64_str = base64.b64encode(audio_bytes).decode('utf-8')
            return {"status": "success", "base64": base64_str, "format": "mp3"}
        except Exception as e:
            return {"error": str(e)}, 500
    
# 5. TTS生成API - 流式响应
@app.post("/api/oddtts/stream")
async def api_tts_stream(request: Request):
    """生成TTS音频并以流式响应返回"""
    data = await request.json()
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", 0)
    volume = data.get("volume", 0)
    pitch = data.get("pitch", 0)
    
    # 如果未指定语音，使用第一个可用语音
    if not voice and voice_options:
        voice = voice_options[0]

    if not voice or voice not in voice_map:
        return JSONResponse({"error": f"Voice '{voice}' not found"}, status_code=404)
        
    try:
        # 创建一个生成器函数来处理流式输出
        async def audio_generator():
            rate_str = f"{rate:+d}%"
            volume_str = f"{volume:+d}%"
            pitch_str = f"{pitch:+d}Hz"
            
            communicate = edge_tts.Communicate(
                text, voice, rate=rate_str, volume=volume_str, pitch=pitch_str
            )
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
            
        return StreamingResponse(audio_generator(), media_type="audio/mpeg")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# 挂载Gradio界面到/gradio路径
app = gr.mount_gradio_app(app, create_gradio_interface(), path="/gradio")

if __name__ == "__main__":
    # 使用uvicorn直接启动FastAPI应用
    uvicorn.run(
        "oddtts:app",  # 指向当前文件的app实例
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式自动重载
    )

