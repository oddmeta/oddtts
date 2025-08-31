import requests
import base64
import time
import os
from pathlib import Path

# 配置API基础URL - 调整路径格式
API_BASE_URL = "http://localhost:8000"

# 测试文本
TEST_TEXT = "Hello! 这是一个API测试。This is an API test. 让我们看看语音合成的效果如何。"

def test_api_voices():
    """测试获取语音列表API"""
    print("="*50)
    print("测试: 获取语音列表 API (/api/oddtts/voices)")
    
    try:
        # 明确指定完整URL
        response = requests.get(f"{API_BASE_URL}/api/oddtts/voices")
        print(f"请求URL: {API_BASE_URL}/api/oddtts/voices")
        print(f"响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        voices = response.json()
        print(f"成功获取 {len(voices)} 个语音选项")
        
        # 打印前5个语音的信息
        print("\n前5个可用语音:")
        for i, voice in enumerate(voices[:5]):
            print(f"{i+1}. 名称: {voice.get('name')}")
            print(f"   语言: {voice.get('locale')}")
            print(f"   性别: {voice.get('gender')}\n")
        
        return voices
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print("测试失败: 接口不存在，请检查服务端是否正确实现了该API")
            # 尝试获取服务器上所有可用的接口信息
            try:
                response = requests.get(f"{API_BASE_URL}/docs")
                if response.status_code == 200:
                    print("提示: 你可以访问以下地址查看可用API文档:")
                    print(f"{API_BASE_URL}/docs")
            except:
                pass
        else:
            print(f"测试失败: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return None

def test_api_voice_details(voice_name):
    """测试获取特定语音详情API"""
    print("="*50)
    print(f"测试: 获取特定语音详情 API (/api/oddtts/voices/{voice_name})")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/oddtts/voices/{voice_name}")
        response.raise_for_status()
        
        voice_details = response.json()
        print("语音详情:")
        for key, value in voice_details.items():
            print(f"   {key}: {value}")
        
        return True
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print(f"测试失败: 语音 '{voice_name}' 不存在或接口未实现")
        else:
            print(f"测试失败: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return False

def test_api_tts_file(voice_name):
    """测试生成TTS音频并返回文件路径API"""
    print("="*50)
    print("测试: 生成TTS音频(文件路径) API (/api/oddtts/file)")
    
    try:
        payload = {
            "text": TEST_TEXT,
            "voice": voice_name,
            "rate": 0,
            "volume": 0,
            "pitch": 0
        }
        
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/oddtts/file", json=payload)
        response.raise_for_status()
        end_time = time.time()
        
        result = response.json()
        print(f"生成成功，耗时: {end_time - start_time:.2f}秒")
        print(f"文件路径: {result.get('file_path')}")
        print(f"状态: {result.get('status')}")
        
        if result.get('file_path') and os.path.exists(result.get('file_path')):
            print("验证: 音频文件存在")
            
            dest_path = f"test_tts_file_{voice_name.replace('-', '_')[:10]}.mp3"
            with open(result.get('file_path'), 'rb') as src, open(dest_path, 'wb') as dest:
                dest.write(src.read())
            print(f"已将音频文件复制到: {dest_path}")
            return True
        else:
            print("验证失败: 音频文件不存在")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return False

def test_api_tts_base64(voice_name):
    """测试生成TTS音频并返回Base64编码API"""
    print("="*50)
    print("测试: 生成TTS音频(Base64) API (/api/oddtts/base64)")
    
    try:
        payload = {
            "text": TEST_TEXT,
            "voice": voice_name,
            "rate": 5,
            "volume": 0,
            "pitch": 0
        }
        
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/oddtts/base64", json=payload)
        response.raise_for_status()
        end_time = time.time()
        
        result = response.json()
        print(f"生成成功，耗时: {end_time - start_time:.2f}秒")
        print(f"状态: {result.get('status')}")
        
        if result.get('base64'):
            print("验证: 成功获取Base64编码数据")
            
            audio_data = base64.b64decode(result.get('base64'))
            dest_path = f"test_tts_base64_{voice_name.replace('-', '_')[:10]}.mp3"
            with open(dest_path, 'wb') as f:
                f.write(audio_data)
            print(f"已将Base64数据解码并保存到: {dest_path}")
            return True
        else:
            print("验证失败: 未获取到Base64编码数据")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return False

def test_api_tts_stream(voice_name):
    """测试生成TTS音频流式响应API"""
    print("="*50)
    print("测试: 生成TTS音频(流式) API (/api/oddtts/stream)")
    
    try:
        payload = {
            "text": TEST_TEXT,
            "voice": voice_name,
            "rate": -5,
            "volume": 0,
            "pitch": 5
        }
        
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/oddtts/stream", json=payload, stream=True)
        response.raise_for_status()
        
        dest_path = f"test_tts_stream_{voice_name.replace('-', '_')[:10]}.mp3"
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        end_time = time.time()
        print(f"流式接收完成，耗时: {end_time - start_time:.2f}秒")
        
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            print(f"验证: 流式音频已保存到: {dest_path}")
            return True
        else:
            print("验证失败: 流式音频文件不存在或为空")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"测试失败: {str(e)}")
        return False

def main():
    print("===== TTS API 客户端测试程序 =====")
    print(f"测试服务器地址: {API_BASE_URL}")
    print("请确保服务端已启动并正常运行...\n")
    
    # 等待用户确认
    input("按Enter键开始测试API...")
    
    # 1. 测试获取语音列表API
    voices = test_api_voices()
    if not voices:
        print("\n获取语音列表失败，无法进行后续测试")
        return
    
    # 选择测试用的语音
    english_voice = None
    chinese_voice = None
    
    for voice in voices:
        locale = voice.get('locale', '')
        if not english_voice and 'en-' in locale:
            english_voice = voice.get('name')
        if not chinese_voice and 'zh-' in locale:
            chinese_voice = voice.get('name')
        
        if english_voice and chinese_voice:
            break
    
    if not english_voice:
        english_voice = voices[0].get('name') if voices else None
    if not chinese_voice:
        chinese_voice = voices[1].get('name') if len(voices) > 1 else english_voice
    
    print(f"\n将使用以下语音进行测试:")
    print(f"英文语音: {english_voice}")
    print(f"中文语音: {chinese_voice}")
    
    # 2. 测试获取特定语音详情API
    test_api_voice_details(english_voice)
    
    # 3. 测试生成TTS音频(文件路径) API
    test_api_tts_file(chinese_voice)
    
    # 4. 测试生成TTS音频(Base64) API
    test_api_tts_base64(english_voice)
    
    # 5. 测试生成TTS音频(流式) API
    test_api_tts_stream(chinese_voice)
    
    print("\n" + "="*50)
    print("所有API测试完成!")

if __name__ == "__main__":
    main()
    