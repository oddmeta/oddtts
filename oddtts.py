# g:\oddmeta\oddtts\oddtts\oddtts.py
import asyncio
import gradio as gr
import os
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request

import oddtts.oddtts_config as config

from oddtts.base_tts_driver import OddTTSDriver
from oddtts.oddtts_params import ODDTTS_TYPE

# Global variables for voice data
single_tts_driver = OddTTSDriver()

voices = []
voice_map = {}
voice_options = []

# 获取所有可用语音 - 修复KeyError问题
async def get_voices(type: ODDTTS_TYPE):
    voice_list = await single_tts_driver.get_voices(type=type)
    return voice_list

# 生成TTS音频并返回文件路径
async def generate_tts_file(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int):
    output_file = await single_tts_driver.generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    return output_file

# 生成TTS音频并返回字节流
async def generate_tts_bytes(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int):
    audio_bytes = await single_tts_driver.generate_tts_bytes(type=type,text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
    return audio_bytes

async def generate_tts_stream(type: ODDTTS_TYPE, text: str, voice: str, rate: int, volume: int, pitch: int):
    async for chunk in single_tts_driver.generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch):
        yield chunk

# 定义Gradio接口和额外的API端点
def create_gradio_interface():
    global voices, voice_options
    
    with gr.Blocks(title="OddTTS Web服务") as demo:
        # 存储最后生成的音频文件路径，用于后续下载
        last_audio_path = gr.State(None)
        
        gr.Markdown("# OddTTS 语音合成Web服务")
        gr.Markdown("提供语音合成API，支持生成文件调用，字节流调用，流式调用")
        
        with gr.Tab("语音合成演示"):
            with gr.Row():
                with gr.Column(scale=3):
                    text_input = gr.Textbox(label="输入文本", lines=5, placeholder="请输入要转换为语音的文本...")

                    voice_locales_select = gr.Dropdown([], label="选择语种", interactive=True)
                    voice_language_select = gr.Dropdown([], label="选择语音", interactive=True)
                    
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
            # print(f"加载locale选项: type={type(unique_locales)}, content={unique_locales}")
            return gr.update(choices=unique_locales, value=unique_locales[0] if unique_locales else None)
        
        def load_voices(): 
            # print(f"加载voice选项: type={type(voice_options)}, content={voice_options}")
            return gr.update(choices=voice_options, value=voice_options[0] if voice_options else None)

        # 添加locale筛选语音的事件处理函数
        def filter_voices_by_locale(selected_locale = "zh-CN"):
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

        # 使用HTML组件注入JavaScript代码，适用于Gradio 6.2.0版本
        browser_language_js = """
        <script>
        // 使用MutationObserver监听DOM变化，确保选择框加载完成
        const observer = new MutationObserver((mutations, obs) => {
            // 获取浏览器语言
            const browserLang = navigator.language || navigator.userLanguage;
            console.log('Browser language:', browserLang);
            
            // 尝试将浏览器语言映射到可用的locale
            const langMap = {
                'zh': 'zh-CN',
                'en': 'en-US',
                'ja': 'ja-JP',
                'ko': 'ko-KR',
                'fr': 'fr-FR',
                'de': 'de-DE',
                'es': 'es-ES',
                'it': 'it-IT'
            };
            
            // 获取主要语言代码
            const mainLang = browserLang.split('-')[0];
            let targetLocale = langMap[mainLang];
            
            console.log('Target locale:', targetLocale);
            
            // 使用更通用的选择器查找选择框
            let localeSelect = null;
            
            // 遍历所有select元素，找到与"选择语种"相关的
            const selectElements = document.querySelectorAll('select');
            console.log('Found select elements:', selectElements.length);
            
            for (let i = 0; i < selectElements.length; i++) {
                const select = selectElements[i];
                // 查看父元素或兄弟元素中是否有"选择语种"的标签
                const parent = select.parentElement;
                if (parent) {
                    const label = parent.querySelector('label');
                    if (label && label.textContent.includes('选择语种')) {
                        localeSelect = select;
                        break;
                    }
                }
            }
            
            // 如果没有找到，尝试使用data-testid选择器
            if (!localeSelect) {
                localeSelect = document.querySelector('select[data-testid^="dropdown-label"]');
            }
            
            console.log('Found locale select:', localeSelect);
            
            if (localeSelect && localeSelect.options.length > 0) {
                // 查找匹配的选项
                let foundOption = false;
                for (let option of localeSelect.options) {
                    console.log('Option value:', option.value);
                    if (option.value === targetLocale || option.value.startsWith(mainLang)) {
                        localeSelect.value = option.value;
                        // 触发change事件
                        localeSelect.dispatchEvent(new Event('change'));
                        console.log('Successfully set locale to:', option.value);
                        foundOption = true;
                        break;
                    }
                }
                
                if (!foundOption) {
                    console.log('No matching locale found for:', mainLang);
                    // 如果没有找到匹配的，尝试使用第一个选项
                    if (localeSelect.options.length > 0) {
                        localeSelect.value = localeSelect.options[0].value;
                        localeSelect.dispatchEvent(new Event('change'));
                        console.log('Set to first available locale:', localeSelect.options[0].value);
                    }
                }
                
                // 停止观察
                obs.disconnect();
            }
        });
        
        // 开始观察DOM变化
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // 5秒后停止观察，防止无限等待
        setTimeout(() => {
            observer.disconnect();
            console.log('Stopped observing DOM changes');
        }, 5000);
        </script>
        """
        
        ## 添加HTML组件来注入JavaScript代码
        # gr.HTML(browser_language_js)
        
        # 加载locale和voice选项
        demo.load(load_locales, None, [voice_locales_select])
        demo.load(load_voices, None, [voice_language_select])

        print("配置完成，开始运行...")

        voice_locales_select.change(
            fn=filter_voices_by_locale,
            inputs=[voice_locales_select],
            outputs=[voice_language_select]
        )

        # 生成语音按钮点击事件
        async def generate_audio(text, voice, rate, volume, pitch):
            type = config.oddtts_cfg["tts_type"]
            audio_path = await generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
            return audio_path, audio_path
        
        generate_btn.click(
            fn=generate_audio,
            inputs=[text_input, voice_language_select, rate_slider, volume_slider, pitch_slider],
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

    type = config.oddtts_cfg["tts_type"]

    # print("Loading voices...")
    voices = await get_voices(type=type)
    # print(voices)
    # print("Voices loaded.")

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
async def api_get_voices():
    """获取所有可用的语音列表"""
    type = config.oddtts_cfg["tts_type"]
    return await get_voices(type=type)
    
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

    type = config.oddtts_cfg["tts_type"]
    try:
        audio_path = await generate_tts_file(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
        return {"status": "success", "file_path": audio_path, "format": "mp3"}
    except Exception as e:
        return {"error": str(e)}, 500
    
# 4. TTS生成API - 返回Base64编码
@app.post("/api/oddtts/base64")
async def api_tts_base64(request: Request):
    """生成TTS音频并返回Base64编码"""
    data = await request.json()

    type = config.oddtts_cfg["tts_type"]
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
        audio_bytes = await generate_tts_bytes(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch)
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

    type = config.oddtts_cfg["tts_type"]
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
        return StreamingResponse(generate_tts_stream(type=type, text=text, voice=voice, rate=rate, volume=volume, pitch=pitch), media_type="audio/mpeg")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# 挂载Gradio界面到/gradio路径
gr.mount_gradio_app(app, create_gradio_interface(), path="/")